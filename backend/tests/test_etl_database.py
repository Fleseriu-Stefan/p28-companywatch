import os
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from datetime import UTC, datetime
from threading import Event
from time import monotonic, sleep
from tracemalloc import get_traced_memory, start, stop

import pytest
from sqlalchemy import event, func, insert, select, text, update
from sqlalchemy.exc import OperationalError

from app.db import create_database_engine
from app.etl.errors import ETLError
from app.etl.models import attempts, companies, publications, staging, versions
from app.etl.service import PROFILE_VERSION, Pipeline, digest_json, file_hash
from app.etl.source import HEADER, RETAINED
from tests.conftest import isolated_test_settings
from tests.etl_fixtures import csv_file, row, source

pytestmark = pytest.mark.integration


@pytest.fixture
def pipeline(engine):
    return Pipeline(engine, minimum_rows=1, allow_synthetic=True)


@pytest.fixture
def ingest_engine():
    configured = create_database_engine(isolated_test_settings(), read_timeout=120)
    yield configured
    configured.dispose()


def publish(pipeline, version):
    report = pipeline.report(version)
    approval = pipeline.approve(version, report["report_hash"])
    pipeline.publish(version, approval)
    return approval


def test_filter_duplicates_minimal_persistence_and_idempotency(pipeline, tmp_path):
    items = [
        row(1),
        row(2),
        row(2),
        row(3, EUID=""),
        row(4, FORMA_JURIDICA="PFA", COD_INMATRICULARE="F01/4/2020"),
        row(5, FORMA_JURIDICA="UNKNOWN"),
        row(6, ADR_DEN_STRADA="DO NOT PERSIST"),
    ]
    path = csv_file(tmp_path / "synthetic.csv", items)
    version = pipeline.ingest(path, source())
    report = pipeline.report(version)
    assert report["state"] == "review"
    assert report["report"]["source_records"] == 7
    assert report["report"]["accepted_records"] == 2
    assert report["report"]["excluded_records"] == 1
    assert report["report"]["quarantined_records"] == 4
    assert report["report"]["duplicate_key_groups"] == 1
    assert report["report"]["full_file_validated"] is True
    assert pipeline.ingest(path, source()) == version
    with pipeline.engine.connect() as connection:
        data = connection.execute(select(companies).where(companies.c.version_id == version)).all()
        assert len(data) == 2
        assert "DO NOT PERSIST" not in str(data)
        assert (
            connection.scalar(
                select(func.count()).select_from(staging).where(staging.c.version_id == version)
            )
            == 0
        )
    publish(pipeline, version)
    assert pipeline.report(version)["state"] == "published"


def test_no_automatic_publication_and_approval_seal(pipeline, tmp_path):
    version = pipeline.ingest(csv_file(tmp_path / "one.csv", [row(20)]), source())
    with pytest.raises(ETLError, match="approval_required"):
        pipeline.publish(version, "not-an-approval")
    with pytest.raises(ETLError, match="report_hash_mismatch"):
        pipeline.approve(version, "0" * 64)
    approval = pipeline.approve(version, pipeline.report(version)["report_hash"])
    with pipeline.engine.begin() as connection:
        connection.execute(
            update(companies)
            .where(companies.c.version_id == version)
            .values(name="TAMPERED SYNTHETIC NAME")
        )
    with pytest.raises(ETLError, match="prepared_data_changed"):
        pipeline.publish(version, approval)
    assert pipeline.report(version)["state"] == "approved"


def test_empty_and_synthetic_versions_cannot_pass_real_publication_gate(pipeline, tmp_path):
    version = pipeline.ingest(csv_file(tmp_path / "empty.csv", []), source())
    with pytest.raises(ETLError, match="insufficient_records"):
        pipeline.approve(version, pipeline.report(version)["report_hash"])
    version = pipeline.ingest(csv_file(tmp_path / "one.csv", [row(30)]), source())
    guarded = Pipeline(pipeline.engine)
    with pytest.raises(ETLError, match="synthetic_not_allowed"):
        guarded.approve(version, pipeline.report(version)["report_hash"])


def test_failed_file_never_replaces_current_snapshot(pipeline, tmp_path):
    good = pipeline.ingest(csv_file(tmp_path / "good.csv", [row(40)]), source())
    publish(pipeline, good)
    bad = csv_file(tmp_path / "bad.csv", [row(41)])
    with bad.open("a") as handle:
        handle.write("synthetic^broken\n")
    with pytest.raises(ETLError, match="record_width_invalid"):
        pipeline.ingest(bad, source("2026-11-04"))
    with pipeline.engine.connect() as connection:
        assert connection.scalar(select(publications.c.current_version_id)) == good
        assert (
            connection.scalar(
                select(func.count()).select_from(versions).where(versions.c.state == "failed")
            )
            >= 1
        )


def test_sql_failure_after_staging_keeps_current_publication(pipeline, tmp_path, caplog):
    current_path = csv_file(tmp_path / "current.csv", [row(8501)])
    current = pipeline.ingest(current_path, source())
    current_approval = publish(pipeline, current)
    path = csv_file(tmp_path / "failed.csv", [row(8502, DENUMIRE="SYNTHETIC_PRIVATE_VALUE")])

    def fail_aggregation(*args):
        statement = args[2]
        if "GROUP BY etl_staging_rows.legal_form" in statement:
            raise OperationalError(
                "SYNTHETIC_PRIVATE_SQL",
                {"data": "SYNTHETIC_PRIVATE_PARAMETER"},
                RuntimeError(1205, "SYNTHETIC_PRIVATE_DRIVER_MESSAGE"),
            )

    event.listen(pipeline.engine, "before_cursor_execute", fail_aggregation)
    try:
        with pytest.raises(ETLError, match="^database_error$"):
            pipeline.ingest(path, source())
    finally:
        event.remove(pipeline.engine, "before_cursor_execute", fail_aggregation)

    assert "operation=count_accepted_forms outcome=sql_operation_failed" in caplog.text
    assert "driver_code=1205" in caplog.text
    assert "SYNTHETIC_PRIVATE" not in caplog.text
    with pipeline.engine.connect() as connection:
        failed = connection.execute(
            select(versions.c.id).where(versions.c.sha256 == file_hash(path))
        ).scalar_one()
        assert not connection.scalar(
            select(func.count()).select_from(staging).where(staging.c.version_id == failed)
        )
        assert not connection.scalar(
            select(func.count()).select_from(companies).where(companies.c.version_id == failed)
        )
        assert connection.scalar(select(publications.c.current_version_id)) == current
        assert (
            connection.scalar(select(versions.c.approval).where(versions.c.id == current))
            == current_approval
        )
    failed_report = pipeline.report(failed)
    assert failed_report["state"] == "failed"
    assert failed_report["report"]["full_file_validated"] is False
    assert failed_report["report"]["failure_code"] == "database_error"
    with pytest.raises(ETLError, match="^version_not_reviewable$"):
        pipeline.approve(failed, failed_report["report_hash"])
    with pytest.raises(ETLError, match="^approval_required$"):
        pipeline.publish(failed, current_approval)
    with pipeline.engine.connect() as connection:
        assert connection.scalar(select(publications.c.current_version_id)) == current


@pytest.mark.parametrize("late_failure", [False, True])
def test_schema_drift_leaves_no_publishable_snapshot(pipeline, tmp_path, late_failure):
    baseline_path = csv_file(tmp_path / "baseline.csv", [row(8100 + late_failure)])
    baseline = pipeline.ingest(baseline_path, source())
    publish(pipeline, baseline)
    sentinel = "SYNTHETIC_PRIVATE_DRIFT_VALUE"
    path = tmp_path / "drift.csv"
    if late_failure:
        csv_file(path, (row(number) for number in range(1, 1001)))
        with path.open("a") as handle:
            handle.write(f"{sentinel}^incomplete\n")
        error = "record_width_invalid"
    else:
        csv_file(path, [row()], (sentinel, *HEADER[1:]))
        error = "schema_changed"
    artifact_hash = file_hash(path)
    with pytest.raises(ETLError, match=f"^{error}$"):
        pipeline.ingest(path, source("2026-11-04"))
    with pipeline.engine.connect() as connection:
        version = connection.execute(
            select(versions.c.id).where(
                versions.c.sha256 == artifact_hash, versions.c.source_kind == "synthetic"
            )
        ).scalar_one()
        assert not connection.scalar(
            select(func.count()).select_from(staging).where(staging.c.version_id == version)
        )
        assert not connection.scalar(
            select(func.count()).select_from(companies).where(companies.c.version_id == version)
        )
        assert connection.scalar(select(publications.c.current_version_id)) == baseline
    manifest = pipeline.report(version)
    assert manifest["state"] == "failed"
    assert manifest["report"]["full_file_validated"] is False
    assert manifest["report"]["failure_code"] == error
    assert manifest["report"]["source_records"] == (1000 if late_failure else 0)
    assert sentinel not in str(manifest)
    with pytest.raises(ETLError, match="^version_not_reviewable$"):
        pipeline.approve(version, manifest["report_hash"])
    with pytest.raises(ETLError, match="^approval_required$"):
        pipeline.publish(version, manifest["report_hash"])


def test_quality_distributions_and_comparison_preserve_seals(pipeline, tmp_path):
    sentinel = "SYNTHETIC_PRIVATE_FORM"
    old_rows = [row(number) for number in range(8201, 8206)]
    new_rows = [
        row(8201),
        row(8202, FORMA_JURIDICA="SA"),
        row(8203, FORMA_JURIDICA="SNC"),
        row(8204),
        row(8204),
        row(8205, FORMA_JURIDICA=""),
        row(8206, FORMA_JURIDICA=sentinel),
        row(8207, COD_INMATRICULARE="F01/8207/2020", FORMA_JURIDICA="PFA"),
    ]
    old = pipeline.ingest(csv_file(tmp_path / "old.csv", old_rows), source())
    publish(pipeline, old)
    new_path = csv_file(tmp_path / "new.csv", new_rows)
    new_source = source("2026-11-04")
    new = pipeline.ingest(new_path, new_source)
    old_before = pipeline.report(old)
    new_before = pipeline.report(new)
    report = new_before["report"]
    assert report["source_legal_forms"] == {"SRL": 3, "SA": 1, "SNC": 1, "missing": 1, "other": 2}
    assert report["accepted_legal_forms"] == {"SRL": 1, "SA": 1, "SNC": 1}
    assert sum(report["source_legal_forms"].values()) == report["source_records"]
    assert sum(report["accepted_legal_forms"].values()) == report["accepted_records"]
    assert new_before["report_hash"] == digest_json(report)
    assert sentinel not in str(new_before)
    result = pipeline.quality_compare(old, new)
    assert result["comparison_status"] == "comparable"
    assert result["counts"]["accepted_records"] == {"old": 5, "new": 3, "delta": -2}
    assert result["rates"]["accepted_records"]["delta_pp"] == pytest.approx(-62.5)
    assert result["distributions"]["accepted_legal_forms"]["SA"]["count"]["delta"] == 1
    assert result["advisories"] == [
        "duplicate_records_appeared",
        "accepted_records_decreased_at_least_40_percent",
    ]
    assert sentinel not in str(result)
    with pytest.raises(ETLError, match="^synthetic_not_allowed$"):
        Pipeline(pipeline.engine).quality_compare(old, new)
    assert pipeline.ingest(new_path, new_source) == new
    assert pipeline.report(old) == old_before
    assert pipeline.report(new) == new_before
    with pipeline.engine.connect() as connection:
        assert connection.scalar(select(publications.c.current_version_id)) == old
        assert connection.scalar(select(versions.c.approval).where(versions.c.id == new)) is None
    assert pipeline.approve(new, new_before["report_hash"])
    with pipeline.engine.connect() as connection:
        assert connection.scalar(select(publications.c.current_version_id)) == old


@pytest.mark.parametrize(("field", "value"), [("schema_hash", "a" * 64), ("profile", "other")])
def test_quality_comparison_rejects_incompatible_reports(pipeline, tmp_path, field, value):
    offset = 0 if field == "schema_hash" else 10
    old = pipeline.ingest(csv_file(tmp_path / "old.csv", [row(8300 + offset)]), source())
    new = pipeline.ingest(csv_file(tmp_path / "new.csv", [row(8301 + offset)]), source())
    with pipeline.engine.begin() as connection:
        connection.execute(update(versions).where(versions.c.id == new).values({field: value}))
    with pytest.raises(ETLError, match="^quality_reports_incompatible$"):
        pipeline.quality_compare(old, new)


def test_quality_legacy_and_failed_reports(pipeline, tmp_path):
    old = pipeline.ingest(csv_file(tmp_path / "old.csv", [row(8400)]), source())
    new = pipeline.ingest(csv_file(tmp_path / "new.csv", [row(8401)]), source())
    legacy = pipeline.report(old)["report"]
    for field in ("quality_format", "source_legal_forms", "accepted_legal_forms"):
        del legacy[field]
    with pipeline.engine.begin() as connection:
        connection.execute(
            update(versions)
            .where(versions.c.id == old)
            .values(report=legacy, report_hash=digest_json(legacy))
        )
    legacy_before = pipeline.report(old)
    assert pipeline.quality_compare(old, new) == {
        "old_version": old,
        "new_version": new,
        "comparison_status": "unavailable",
        "reason": "legacy_report",
        "advisories": [],
    }
    assert pipeline.report(old) == legacy_before
    assert pipeline.approve(old, legacy_before["report_hash"])
    path = csv_file(tmp_path / "failure.csv", [row(8402)], HEADER[:-1])
    with pytest.raises(ETLError, match="^schema_changed$"):
        pipeline.ingest(path, source())
    with pipeline.engine.connect() as connection:
        failed = connection.execute(
            select(versions.c.id).where(versions.c.sha256 == file_hash(path))
        ).scalar_one()
    with pytest.raises(ETLError, match="^quality_reports_not_validated$"):
        pipeline.quality_compare(new, failed)


def test_sql_diff_is_null_safe_and_case_sensitive(pipeline, tmp_path):
    old = pipeline.ingest(
        csv_file(
            tmp_path / "old.csv",
            [
                row(50, ADR_LOCALITATE=""),
                row(51),
                row(52),
                row(53),
            ],
        ),
        source(),
    )
    new = pipeline.ingest(
        csv_file(
            tmp_path / "new.csv",
            [
                row(50, ADR_LOCALITATE="LOC SINTETIC"),
                row(51, DENUMIRE="exemplu sintetic 51 srl"),
                row(53),
                row(54),
            ],
        ),
        source("2026-11-04"),
    )
    with pytest.raises(ETLError, match="published_versions_required"):
        pipeline.diff(old, new)
    publish(pipeline, old)
    publish(pipeline, new)
    result = pipeline.diff(old, new)
    assert result["added"] == 1
    assert result["removed"] == 1
    assert result["modified"] == 2
    assert result["unchanged"] == 1
    assert result["by_field"]["locality"] == 1
    assert result["by_field"]["name"] == 1


@pytest.fixture
def diff_editions(pipeline, tmp_path, request):
    old_rows = [
        row(850, ADR_LOCALITATE="", ADR_JUDET=""),
        row(851, CUI="", ADR_LOCALITATE=""),
        row(852),
        row(853, ADR_LOCALITATE=""),
        row(855),
    ]
    new_rows = [
        row(850, ADR_LOCALITATE="LOC NOU", ADR_JUDET=""),
        row(851, CUI="", ADR_LOCALITATE="", DENUMIRE="exemplu sintetic 851 srl"),
        row(854, CUI=old_rows[2]["CUI"]),
        row(853, ADR_LOCALITATE=""),
        row(855, ADR_LOCALITATE="", ADR_JUDET="JUDET NOU"),
    ]
    old_source = replace(source(), resource_id=f"{request.node.name}-old")
    new_source = replace(source("2026-11-04"), resource_id=f"{request.node.name}-new")
    old = pipeline.ingest(csv_file(tmp_path / "old.csv", old_rows), old_source)
    new = pipeline.ingest(csv_file(tmp_path / "new.csv", new_rows), new_source)
    return old, new, old_rows, new_rows


def expected_side(record):
    return {name: record[column] or None for column, name in RETAINED.items()}


def check_diff_totals(pipeline, old, new, categories, fields, old_count, new_count):
    totals = pipeline.diff(old, new)
    assert {category: totals[category] for category in categories} == categories
    assert totals["by_field"] == {
        name: fields[name] for name in RETAINED.values() if name != "euid"
    }
    matched = totals["modified"] + totals["unchanged"]
    assert totals["removed"] + matched == old_count
    assert totals["added"] + matched == new_count
    assert sum(categories.values()) == old_count + new_count - matched


def test_diff_details_values_and_totals(pipeline, diff_editions):
    old, new, old_rows, new_rows = diff_editions
    publish(pipeline, old)
    publish(pipeline, new)
    expected = {
        old_rows[0]["EUID"]: ("modified", old_rows[0], new_rows[0], ("locality",)),
        old_rows[1]["EUID"]: ("modified", old_rows[1], new_rows[1], ("name",)),
        old_rows[2]["EUID"]: ("removed", old_rows[2], None, ()),
        new_rows[2]["EUID"]: ("added", None, new_rows[2], ()),
        old_rows[3]["EUID"]: ("unchanged", old_rows[3], new_rows[3], ()),
        old_rows[4]["EUID"]: ("modified", old_rows[4], new_rows[4], ("county", "locality")),
    }
    with pipeline.diff_details(old, new) as details:
        rows = list(details)
    assert len(rows) == len(expected)
    assert {entry["euid"]: entry for entry in rows} == {
        euid: {
            "euid": euid,
            "change_type": category,
            "previous": expected_side(previous) if previous is not None else None,
            "current": expected_side(current) if current is not None else None,
            "changed_fields": fields,
        }
        for euid, (category, previous, current, fields) in expected.items()
    }
    check_diff_totals(
        pipeline,
        old,
        new,
        Counter(entry["change_type"] for entry in rows),
        Counter(field for entry in rows for field in entry["changed_fields"]),
        len(old_rows),
        len(new_rows),
    )


def test_diff_details_binary_euid_and_all_field_flags(pipeline):
    # The production CSV profile rejects case-only EUID variants and ties registration to EUID.
    # Seed synthetic published rows directly to exercise the storage comparison independently.
    old, new = "binary-diff-old", "binary-diff-new"
    fields = tuple(name for name in RETAINED.values() if name != "euid")
    with pipeline.engine.begin() as connection:
        for version, edition, key, value in (
            (old, "2026-10-19", "Binary-Key", "A"),
            (new, "2026-11-04", "binary-key", "a"),
        ):
            connection.execute(
                versions.insert().values(
                    id=version,
                    edition=edition,
                    resource_id=version,
                    source_url="synthetic",
                    license="synthetic",
                    source_kind="synthetic",
                    sha256="0" * 64,
                    profile=PROFILE_VERSION,
                    schema_hash="0" * 64,
                    state="published",
                    created_at=datetime.now(UTC).replace(tzinfo=None),
                    manifest={},
                )
            )
            connection.execute(
                companies.insert(),
                [
                    {"version_id": version, "euid": key, **dict.fromkeys(fields, None)},
                    {"version_id": version, "euid": "same-key", **dict.fromkeys(fields, value)},
                ],
            )
    with pipeline.diff_details(old, new) as details:
        rows = {entry["euid"]: entry for entry in details}
    assert rows.keys() == {"Binary-Key", "binary-key", "same-key"}
    assert rows["Binary-Key"]["change_type"] == "removed"
    assert rows["binary-key"]["change_type"] == "added"
    assert rows["same-key"]["change_type"] == "modified"
    assert rows["same-key"]["changed_fields"] == fields
    assert rows["same-key"]["previous"] == {"euid": "same-key", **dict.fromkeys(fields, "A")}
    assert rows["same-key"]["current"] == {"euid": "same-key", **dict.fromkeys(fields, "a")}


def test_diff_details_version_guards_and_orientation(pipeline, diff_editions):
    old, new, old_rows, _ = diff_editions
    publish(pipeline, old)
    with pytest.raises(ETLError, match="^published_versions_required$"):
        with pipeline.diff_details(old, new):
            pytest.fail("review version was exposed")
    approval = pipeline.approve(new, pipeline.report(new)["report_hash"])
    with pytest.raises(ETLError, match="^published_versions_required$"):
        with pipeline.diff_details(old, new):
            pytest.fail("unpublished approved version was exposed")
    pipeline.publish(new, approval)
    with pytest.raises(ETLError, match="^published_versions_required$"):
        with pipeline.diff_details("missing", new):
            pytest.fail("missing version was accepted")
    guarded = Pipeline(pipeline.engine)
    with pytest.raises(ETLError, match="^synthetic_not_allowed$"):
        with guarded.diff_details(old, new):
            pytest.fail("synthetic versions were exposed without opt-in")
    with pipeline.diff_details(old, old) as details:
        same = list(details)
    assert len(same) == len(old_rows)
    assert {entry["euid"] for entry in same} == {record["EUID"] for record in old_rows}
    assert all(
        entry["change_type"] == "unchanged"
        and entry["previous"] == entry["current"]
        and entry["changed_fields"] == ()
        for entry in same
    )
    with pipeline.diff_details(old, new) as details:
        forward = {entry["euid"]: entry for entry in details}
    with pipeline.diff_details(new, old) as details:
        reverse = {entry["euid"]: entry for entry in details}
    assert forward.keys() == reverse.keys()
    opposite = {
        "added": "removed",
        "removed": "added",
        "modified": "modified",
        "unchanged": "unchanged",
    }
    for euid, entry in forward.items():
        assert reverse[euid] == {
            "euid": euid,
            "change_type": opposite[entry["change_type"]],
            "previous": entry["current"],
            "current": entry["previous"],
            "changed_fields": entry["changed_fields"],
        }


def test_diff_details_releases_cursor_and_connection(pipeline, diff_editions):
    old, new, _, _ = diff_editions
    publish(pipeline, old)
    publish(pipeline, new)
    pool = pipeline.engine.pool
    with pipeline.diff_details(old, new) as details:
        assert pool.checkedout() == 1
        assert len(list(details)) == 6
    assert pool.checkedout() == 0
    with pipeline.diff_details(old, new) as details:
        next(details)
    assert pool.checkedout() == 0
    with pytest.raises(RuntimeError, match="^synthetic_consumer_error$"):
        with pipeline.diff_details(old, new) as details:
            next(details)
            raise RuntimeError("synthetic_consumer_error")
    assert pool.checkedout() == 0
    with pipeline.engine.connect() as connection:
        assert connection.scalar(text("SELECT 1")) == 1


@pytest.mark.skipif(
    os.getenv("COMPANYWATCH_DIFF_VOLUME") != "1", reason="run the opt-in two-edition volume check"
)
def test_diff_details_two_large_published_editions(engine, tmp_path):
    pipeline = Pipeline(engine, allow_synthetic=True)
    old_path = csv_file(tmp_path / "volume-old.csv", (row(i) for i in range(1, 100002)))
    new_path = csv_file(
        tmp_path / "volume-new.csv",
        (row(i, DENUMIRE="SYNTHETIC CHANGED NAME") if i == 2 else row(i) for i in range(2, 100003)),
    )
    old_source, new_source = source(), source("2026-11-04")
    old = pipeline.ingest(old_path, old_source)
    new = pipeline.ingest(new_path, new_source)
    for version in (old, new):
        assert pipeline.report(version)["report"]["accepted_records"] == 100001
        publish(pipeline, version)
    assert pipeline.ingest(old_path, old_source) == old
    assert pipeline.ingest(new_path, new_source) == new

    categories, fields = Counter(), Counter()
    detail_sql = []

    def capture_sql(connection, cursor, statement, parameters, context, executemany):
        if "UNION ALL" in statement:
            detail_sql.append((statement, parameters))

    event.listen(engine, "before_cursor_execute", capture_sql)
    try:
        started = monotonic()
        with pipeline.diff_details(old, new) as details:
            for entry in details:
                categories[entry["change_type"]] += 1
                fields.update(entry["changed_fields"])
        elapsed = monotonic() - started
    finally:
        event.remove(engine, "before_cursor_execute", capture_sql)

    assert categories == {"added": 1, "removed": 1, "modified": 1, "unchanged": 99999}
    assert sum(categories.values()) == 100002
    assert fields == {"name": 1}
    check_diff_totals(pipeline, old, new, categories, fields, 100001, 100001)

    start()
    try:
        with pipeline.diff_details(old, new) as details:
            assert sum(1 for _ in details) == 100002
        _, peak = get_traced_memory()
    finally:
        stop()
    print(f"Accepted per edition: 100001. Categories: {dict(categories)}. Fields: {dict(fields)}.")
    print(f"Complete detail stream: {elapsed:.3f}s with default timeouts.")
    print(f"Python peak: {peak} bytes.")

    [(statement, parameters)] = detail_sql
    with engine.connect() as connection:
        print(connection.exec_driver_sql(f"EXPLAIN ANALYZE {statement}", parameters).scalar_one())


def test_publication_rolls_back_and_concurrent_versions_are_whole(pipeline, tmp_path, monkeypatch):
    first = pipeline.ingest(csv_file(tmp_path / "first.csv", [row(60)]), source())
    publish(pipeline, first)
    second = pipeline.ingest(csv_file(tmp_path / "second.csv", [row(61), row(62)]), source())
    approval = pipeline.approve(second, pipeline.report(second)["report_hash"])
    original = pipeline._activate

    def fail(connection, version_id):
        original(connection, version_id)
        raise ETLError("synthetic_crash")

    monkeypatch.setattr(pipeline, "_activate", fail)
    with pytest.raises(ETLError, match="synthetic_crash"):
        pipeline.publish(second, approval)
    with pipeline.engine.connect() as connection:
        assert connection.scalar(select(publications.c.current_version_id)) == first
    assert pipeline.report(second)["state"] == "approved"
    monkeypatch.setattr(pipeline, "_activate", original)
    third = pipeline.ingest(csv_file(tmp_path / "third.csv", [row(63)]), source())
    third_approval = pipeline.approve(third, pipeline.report(third)["report_hash"])
    with ThreadPoolExecutor(max_workers=2) as executor:
        list(
            executor.map(
                lambda pair: pipeline.publish(*pair), [(second, approval), (third, third_approval)]
            )
        )
    with pipeline.engine.connect() as connection:
        current = connection.scalar(select(publications.c.current_version_id))
        assert current in {second, third}
        count = connection.scalar(
            select(func.count()).select_from(companies).where(companies.c.version_id == current)
        )
        assert count == (2 if current == second else 1)


def test_large_synthetic_version_meets_full_publication_threshold(ingest_engine, tmp_path):
    pipeline = Pipeline(ingest_engine, allow_synthetic=True)
    path = csv_file(tmp_path / "synthetic-volume.csv", (row(i) for i in range(1, 100002)))
    version = pipeline.ingest(path, source())
    report = pipeline.report(version)
    assert report["report"]["source_records"] == 100001
    assert report["report"]["accepted_records"] == 100001
    assert report["report"]["minimum_records"] == 100000
    approval = publish(pipeline, version)
    pipeline.publish(version, approval)
    with ingest_engine.connect() as connection:
        assert (
            connection.scalar(
                select(func.count()).select_from(companies).where(companies.c.version_id == version)
            )
            == 100001
        )


def test_concurrent_ingestion_never_duplicates_a_version(pipeline, tmp_path):
    path = csv_file(tmp_path / "concurrent.csv", [row(70)])

    def ingest(_):
        try:
            return pipeline.ingest(path, source())
        except ETLError as error:
            assert str(error) == "version_busy"
            return None

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(ingest, range(2)))
    ids = {result for result in results if result is not None}
    assert len(ids) == 1
    version = ids.pop()
    assert pipeline.ingest(path, source()) == version
    with pipeline.engine.connect() as connection:
        assert (
            connection.scalar(
                select(func.count()).select_from(companies).where(companies.c.version_id == version)
            )
            == 1
        )


def test_abandoned_loading_version_is_safely_recovered(pipeline, tmp_path):
    path = csv_file(tmp_path / "orphan.csv", [row(80)])
    version = pipeline.ingest(path, source())
    with pipeline.engine.begin() as connection:
        connection.execute(update(versions).where(versions.c.id == version).values(state="loading"))
        connection.execute(
            update(attempts).where(attempts.c.version_id == version).values(state="loading")
        )
    assert pipeline.ingest(path, source()) == version
    assert pipeline.report(version)["state"] == "review"
    with pipeline.engine.connect() as connection:
        assert (
            connection.scalar(
                select(func.count())
                .select_from(attempts)
                .where(attempts.c.version_id == version, attempts.c.state == "abandoned")
            )
            == 1
        )
        assert (
            connection.scalar(
                select(func.count()).select_from(companies).where(companies.c.version_id == version)
            )
            == 1
        )


def seed_interrupted_retry(pipeline, tmp_path, *, rows=2501, other_version=None):
    artifact = csv_file(tmp_path / "retry-batches.csv", [row(9801, DENUMIRE=tmp_path.name)])
    version = pipeline.ingest(artifact, source())
    with pipeline.engine.begin() as connection:
        connection.execute(update(versions).where(versions.c.id == version).values(state="loading"))
        connection.execute(
            update(attempts).where(attempts.c.version_id == version).values(state="loading")
        )
        entries = []
        for number in range(rows):
            entries.append(
                dict(
                    version_id=version,
                    source_line=number + 2,
                    valid=True,
                    excluded=False,
                    key_digest=f"{number:064x}",
                    errors=[],
                )
            )
            if other_version is not None:
                entries.append(
                    dict(
                        version_id=other_version,
                        source_line=number + 2,
                        valid=True,
                        excluded=False,
                        key_digest=f"{number:064x}",
                        errors=[],
                    )
                )
            if len(entries) >= 1000:
                connection.execute(insert(staging), entries)
                entries.clear()
        if entries:
            connection.execute(insert(staging), entries)
    return artifact, version


def test_retry_cleanup_batches_are_bounded_and_isolate_interleaved_versions(pipeline, tmp_path):
    other = pipeline.ingest(csv_file(tmp_path / "other.csv", [row(9802)]), source("2026-11-04"))
    artifact, version = seed_interrupted_retry(pipeline, tmp_path, other_version=other)
    deleted = []

    def record_delete(_connection, cursor, statement, *_args):
        if statement.startswith("DELETE FROM etl_staging_rows"):
            deleted.append(cursor.rowcount)

    event.listen(pipeline.engine, "after_cursor_execute", record_delete)
    try:
        assert pipeline.ingest(artifact, source()) == version
    finally:
        event.remove(pipeline.engine, "after_cursor_execute", record_delete)

    assert len(deleted) >= 3
    assert sum(deleted[:3]) == 2501
    assert all(0 < count <= 1000 for count in deleted)
    with pipeline.engine.connect() as connection:
        assert (
            connection.scalar(
                select(func.count()).select_from(staging).where(staging.c.version_id == other)
            )
            == 2501
        )
        assert (
            connection.scalar(
                select(func.count()).select_from(staging).where(staging.c.version_id == version)
            )
            == 0
        )
        assert (
            connection.scalar(
                select(func.count()).select_from(companies).where(companies.c.version_id == version)
            )
            == 1
        )


@pytest.fixture
def empty_publication_pointer(pipeline):
    with pipeline.engine.begin() as connection:
        previous = connection.scalar(select(publications.c.current_version_id))
        connection.execute(update(publications).values(current_version_id=None))
    try:
        yield
    finally:
        with pipeline.engine.begin() as connection:
            connection.execute(update(publications).values(current_version_id=previous))


@pytest.mark.usefixtures("empty_publication_pointer")
def test_retry_cleanup_interruption_between_committed_batches_is_recoverable(
    pipeline, tmp_path, monkeypatch
):
    from app.etl import service

    artifact, version = seed_interrupted_retry(pipeline, tmp_path)
    deletes = 0
    remaining_staging = (
        select(func.count()).select_from(staging).where(staging.c.version_id == version)
    )

    def reject_fresh_parse(_path):
        pytest.fail(
            f"Fresh parsing reached after {deletes} retry staging DELETE(s); "
            "expected a second retry batch after the first committed 1,000 deletions"
        )

    def interrupt_second_delete(_connection, _cursor, statement, *_args):
        nonlocal deletes
        if statement.startswith("DELETE FROM etl_staging_rows"):
            deletes += 1
            if deletes == 2:
                # A separate connection can see only committed cleanup.
                with pipeline.engine.connect() as observer:
                    assert observer.scalar(remaining_staging) == 1501
                raise ETLError("synthetic_cleanup_interrupted")

    with monkeypatch.context() as patches:
        patches.setattr(service, "records", reject_fresh_parse)
        event.listen(pipeline.engine, "before_cursor_execute", interrupt_second_delete)
        try:
            with pytest.raises(ETLError, match="synthetic_cleanup_interrupted"):
                pipeline.ingest(artifact, source())
        finally:
            event.remove(pipeline.engine, "before_cursor_execute", interrupt_second_delete)

    assert deletes == 2
    with pipeline.engine.connect() as connection:
        assert (
            connection.scalar(
                select(func.count()).select_from(staging).where(staging.c.version_id == version)
            )
            == 1501
        )
        assert (
            connection.scalar(select(versions.c.state).where(versions.c.id == version)) == "loading"
        )
        assert (
            connection.scalar(select(versions.c.report_hash).where(versions.c.id == version))
            is None
        )
        assert connection.scalar(select(publications.c.current_version_id)) is None
    assert pipeline.ingest(artifact, source()) == version
    with pipeline.engine.connect() as connection:
        assert (
            connection.scalar(
                select(func.count()).select_from(staging).where(staging.c.version_id == version)
            )
            == 0
        )
        assert (
            connection.scalar(
                select(func.count()).select_from(companies).where(companies.c.version_id == version)
            )
            == 1
        )
        assert set(
            connection.scalars(select(attempts.c.state).where(attempts.c.version_id == version))
        ) == {"abandoned", "ready"}


def test_retry_cleanup_failure_identifies_statement_without_private_sql(pipeline, tmp_path, caplog):
    artifact, _version = seed_interrupted_retry(pipeline, tmp_path, rows=1)
    private = "SYNTHETIC_PRIVATE_CLEANUP_SQL"

    def fail_delete(_connection, _cursor, statement, *_args):
        if statement.startswith("DELETE FROM etl_staging_rows"):
            raise OperationalError(private, {"value": private}, RuntimeError(1205, private))

    event.listen(pipeline.engine, "before_cursor_execute", fail_delete)
    try:
        with pytest.raises(ETLError, match="^database_error$"):
            pipeline.ingest(artifact, source())
    finally:
        event.remove(pipeline.engine, "before_cursor_execute", fail_delete)
    assert "operation=delete_retry_staging_batch outcome=sql_operation_failed" in caplog.text
    assert "elapsed_ms=" in caplog.text
    assert "driver_code=1205" in caplog.text
    assert private not in caplog.text


def test_retry_cleanup_survives_repeated_interruptions_and_excludes_same_input_worker(
    pipeline, tmp_path, monkeypatch
):
    from app.etl import service

    artifact, version = seed_interrupted_retry(pipeline, tmp_path, rows=3501)
    remaining = select(func.count()).select_from(staging).where(staging.c.version_id == version)
    attempt_states = select(attempts.c.state).where(attempts.c.version_id == version)

    def reject_parse(_path):
        pytest.fail("Retry must interrupt after a committed cleanup batch before parsing")

    for expected in (2501, 1501):
        deletes = 0

        def interrupt(_connection, _cursor, statement, *_args, expected=expected):
            nonlocal deletes
            if statement.startswith("DELETE FROM etl_staging_rows"):
                deletes += 1
                if deletes == 2:
                    with pipeline.engine.connect() as observer:
                        assert observer.scalar(remaining) == expected
                    with pytest.raises(ETLError, match="^version_busy$"):
                        pipeline.ingest(artifact, source())
                    raise ETLError("synthetic_cleanup_interrupted")

        with monkeypatch.context() as patches:
            patches.setattr(service, "records", reject_parse)
            event.listen(pipeline.engine, "before_cursor_execute", interrupt)
            try:
                with pytest.raises(ETLError, match="^synthetic_cleanup_interrupted$"):
                    pipeline.ingest(artifact, source())
            finally:
                event.remove(pipeline.engine, "before_cursor_execute", interrupt)
        with pipeline.engine.connect() as observer:
            assert observer.scalar(remaining) == expected

    assert pipeline.ingest(artifact, source()) == version
    with pipeline.engine.connect() as observer:
        assert observer.scalar(remaining) == 0
        assert Counter(observer.scalars(attempt_states)) == {"abandoned": 3, "ready": 1}


def test_retry_cleanup_disconnect_rolls_back_only_uncommitted_batch(pipeline, tmp_path, caplog):
    artifact, version = seed_interrupted_retry(pipeline, tmp_path)
    remaining = select(func.count()).select_from(staging).where(staging.c.version_id == version)
    deletes = []

    def disconnect(connection, cursor, statement, *_args):
        if statement.startswith("DELETE FROM etl_staging_rows"):
            deleted = cursor.rowcount
            session_id = connection.scalar(text("SELECT CONNECTION_ID()"))
            deletes.append((session_id, deleted))
            if len(deletes) == 2:
                with pipeline.engine.connect() as killer:
                    killer.execute(text(f"KILL CONNECTION {int(session_id)}"))

    event.listen(pipeline.engine, "after_cursor_execute", disconnect)
    try:
        with pytest.raises(ETLError, match="^ingest_lock_lost$"):
            pipeline.ingest(artifact, source())
    finally:
        event.remove(pipeline.engine, "after_cursor_execute", disconnect)

    assert len(deletes) == 2
    assert deletes[0] == deletes[1]
    assert deletes[0][1] == 1000
    assert "operation=commit_transaction outcome=connection_invalidated" in caplog.text
    with pipeline.engine.connect() as observer:
        assert observer.scalar(remaining) == 1501
    assert pipeline.ingest(artifact, source()) == version
    with pipeline.engine.connect() as observer:
        assert observer.scalar(remaining) == 0


@pytest.mark.parametrize("state", ["loading", "review", "approved", "published"])
def test_retry_cleanup_protects_version_seals_and_pointer(pipeline, tmp_path, state):
    artifact, version = seed_interrupted_retry(pipeline, tmp_path, rows=1)
    version_row = select(versions).where(versions.c.id == version)
    pointer = select(publications.c.current_version_id)
    with pipeline.engine.begin() as connection:
        connection.execute(update(versions).where(versions.c.id == version).values(state=state))
        previous = connection.scalar(pointer)
        connection.execute(update(publications).values(current_version_id=version))
        before = connection.execute(version_row).one()
    try:
        if state == "loading":
            with pytest.raises(ETLError, match="^retry_cleanup_not_allowed$"):
                pipeline.ingest(artifact, source())
        else:
            assert pipeline.ingest(artifact, source()) == version
        with pipeline.engine.connect() as observer:
            assert observer.execute(version_row).one() == before
            assert observer.scalar(pointer) == version
            for table in (staging, companies):
                assert (
                    observer.scalar(
                        select(func.count()).select_from(table).where(table.c.version_id == version)
                    )
                    == 1
                )
    finally:
        with pipeline.engine.begin() as connection:
            connection.execute(update(publications).values(current_version_id=previous))


def test_ingest_connection_can_read_after_more_than_two_seconds(ingest_engine):
    with ingest_engine.connect() as connection:
        assert connection.scalar(text("SELECT SLEEP(3)")) == 0


def test_duplicate_aggregation_disconnect_preserves_pointer_and_recovers(
    pipeline, tmp_path, caplog
):
    current = pipeline.ingest(
        csv_file(tmp_path / "current-before-disconnect.csv", [row(9701)]), source()
    )
    publish(pipeline, current)
    artifact = csv_file(tmp_path / "disconnect-during-duplicates.csv", [row(9702)])
    ingest_engine = create_database_engine(isolated_test_settings(), read_timeout=120)
    ingest_pipeline = Pipeline(ingest_engine, minimum_rows=1, allow_synthetic=True)
    killed = False

    def disconnect_before_duplicate_count(connection, _cursor, statement, *_args):
        nonlocal killed
        if not killed and "GROUP BY etl_staging_rows.key_digest" in statement:
            killed = True
            session_id = connection.scalar(text("SELECT CONNECTION_ID()"))
            with ingest_engine.connect() as killer:
                killer.execute(text(f"KILL CONNECTION {int(session_id)}"))

    event.listen(ingest_engine, "before_cursor_execute", disconnect_before_duplicate_count)
    try:
        with pytest.raises(ETLError, match="^ingest_lock_lost$"):
            ingest_pipeline.ingest(artifact, source("2026-11-04"))
    finally:
        event.remove(ingest_engine, "before_cursor_execute", disconnect_before_duplicate_count)

    assert killed
    assert "operation=count_duplicate_groups outcome=connection_invalidated" in caplog.text
    with ingest_engine.connect() as connection:
        failed = connection.scalar(
            select(versions.c.id).where(versions.c.sha256 == file_hash(artifact))
        )
        assert (
            connection.scalar(select(versions.c.state).where(versions.c.id == failed)) == "loading"
        )
        assert connection.scalar(select(publications.c.current_version_id)) == current
        assert (
            connection.scalar(
                select(func.count()).select_from(staging).where(staging.c.version_id == failed)
            )
            == 1
        )
        assert (
            connection.scalar(
                select(func.count()).select_from(companies).where(companies.c.version_id == failed)
            )
            == 0
        )
    with pytest.raises(ETLError, match="^version_not_reviewable$"):
        ingest_pipeline.approve(failed, "synthetic-report-hash")
    with pytest.raises(ETLError, match="^approval_required$"):
        ingest_pipeline.publish(failed, "synthetic-approval")

    assert ingest_pipeline.ingest(artifact, source("2026-11-04")) == failed
    assert ingest_pipeline.report(failed)["state"] == "review"
    with ingest_engine.connect() as connection:
        assert connection.scalar(select(publications.c.current_version_id)) == current
        assert (
            connection.scalar(
                select(func.count()).select_from(staging).where(staging.c.version_id == failed)
            )
            == 0
        )
        assert (
            connection.scalar(
                select(func.count()).select_from(companies).where(companies.c.version_id == failed)
            )
            == 1
        )
        assert set(
            connection.scalars(select(attempts.c.state).where(attempts.c.version_id == failed))
        ) == {"abandoned", "ready"}
    ingest_engine.dispose()


def test_high_cardinality_duplicate_aggregation_reconciles(pipeline, tmp_path):
    def items():
        for number in range(1, 20002):
            yield row(number)
        for number in range(1, 5):
            yield row(number)
        yield row(5, FORMA_JURIDICA="PFA", COD_INMATRICULARE="F01/5/2020")

    artifact = csv_file(tmp_path / "many-distinct-keys.csv", items())
    with pipeline.engine.connect() as connection:
        pointer_before = connection.scalar(select(publications.c.current_version_id))
    version = pipeline.ingest(artifact, source())
    report = pipeline.report(version)["report"]
    assert report["source_records"] == 20006
    assert report["duplicate_key_groups"] == 5
    assert report["duplicate_key_records"] == 10
    assert report["accepted_records"] == 19996
    assert report["quarantined_records"] == 9
    assert report["excluded_records"] == 1
    assert report["source_records"] == (
        report["accepted_records"] + report["quarantined_records"] + report["excluded_records"]
    )
    with pipeline.engine.connect() as connection:
        assert connection.scalar(select(publications.c.current_version_id)) == pointer_before
        assert (
            connection.scalar(
                select(func.count()).select_from(staging).where(staging.c.version_id == version)
            )
            == 0
        )


@pytest.mark.parametrize("parser_fails", [False, True])
def test_lost_ingest_lock_cannot_modify_successor(pipeline, tmp_path, monkeypatch, parser_fails):
    from app.etl import service

    offset = 2000 if parser_fails else 0
    current = pipeline.ingest(csv_file(tmp_path / "current.csv", [row(9999 + offset)]), source())
    publish(pipeline, current)
    artifact = csv_file(tmp_path / "interrupted.csv", (row(i + offset) for i in range(1, 1002)))
    input_source = source("2026-11-04")
    input_hash = file_hash(artifact)
    lock_name = digest_json(
        [
            pipeline.engine.url.database,
            input_source.kind,
            input_source.resource_id,
            PROFILE_VERSION,
            input_hash,
        ]
    )
    staged, resume = Event(), Event()
    original_records = service.records
    original_stage = pipeline._stage

    def pause_after_stage(*args, **kwargs):
        original_stage(*args, **kwargs)
        if not staged.is_set():
            staged.set()
            assert resume.wait(20)

    def interrupted_records(path):
        for ordinal, item in original_records(path):
            if ordinal == 1002 and parser_fails:
                raise ETLError("synthetic_parse_error")
            yield ordinal, item

    with ThreadPoolExecutor(max_workers=1) as executor:
        monkeypatch.setattr(pipeline, "_stage", pause_after_stage)
        monkeypatch.setattr(service, "records", interrupted_records)
        worker = executor.submit(pipeline.ingest, artifact, input_source)
        try:
            assert staged.wait(20)
            monkeypatch.setattr(service, "records", original_records)
            with pipeline.engine.connect() as connection:
                session_id = connection.scalar(
                    text("SELECT IS_USED_LOCK(:name)"), {"name": lock_name}
                )
                assert session_id is not None
                connection.execute(text(f"KILL CONNECTION {int(session_id)}"))
                deadline = monotonic() + 5
                while not connection.scalar(
                    text("SELECT IS_FREE_LOCK(:name)"), {"name": lock_name}
                ):
                    assert monotonic() < deadline
                    sleep(0.05)
            successor = pipeline.ingest(artifact, input_source)
            with pipeline.engine.connect() as connection:
                seal_before = connection.scalar(
                    select(versions.c.prepared_hash).where(versions.c.id == successor)
                )
        finally:
            resume.set()
        with pytest.raises(ETLError, match="ingest_lock_lost"):
            worker.result(timeout=20)

    assert pipeline.ingest(artifact, input_source) == successor
    report = pipeline.report(successor)
    assert report["state"] == "review"
    assert report["report"]["source_records"] == report["report"]["accepted_records"] == 1001
    with pipeline.engine.connect() as connection:
        assert connection.scalar(select(publications.c.current_version_id)) == current
        assert (
            connection.scalar(select(versions.c.prepared_hash).where(versions.c.id == successor))
            == seal_before
        )
        assert (
            connection.scalar(
                select(func.count())
                .select_from(companies)
                .where(companies.c.version_id == successor)
            )
            == 1001
        )
        assert (
            connection.scalar(
                select(func.count()).select_from(staging).where(staging.c.version_id == successor)
            )
            == 0
        )
        assert set(
            connection.scalars(select(attempts.c.state).where(attempts.c.version_id == successor))
        ) == {"abandoned", "ready", "reused"}


def test_changed_report_invalidates_approval(pipeline, tmp_path):
    version = pipeline.ingest(csv_file(tmp_path / "changed-report.csv", [row(90)]), source())
    approval = pipeline.approve(version, pipeline.report(version)["report_hash"])
    with pipeline.engine.begin() as connection:
        connection.execute(
            update(versions).where(versions.c.id == version).values(report={"changed": True})
        )
    with pytest.raises(ETLError, match="report_changed"):
        pipeline.publish(version, approval)


@pytest.mark.parametrize(
    "changes",
    [
        {"FORMA_JURIDICA": "UNKNOWN"},
        {"FORMA_JURIDICA": "PFA", "COD_INMATRICULARE": "F01/91/2020"},
    ],
)
def test_duplicate_identity_in_excluded_or_unknown_row_also_quarantines_company(
    pipeline, tmp_path, changes
):
    path = csv_file(tmp_path / "cross-scope-duplicate.csv", [row(91), row(91, **changes), row(92)])
    version = pipeline.ingest(path, source())
    report = pipeline.report(version)["report"]
    assert report["accepted_records"] == 1
    assert report["duplicate_key_groups"] == 1
    with pipeline.engine.connect() as connection:
        assert connection.scalars(
            select(companies.c.euid).where(companies.c.version_id == version)
        ).all() == ["ROONRC.J01/92/2020"]
