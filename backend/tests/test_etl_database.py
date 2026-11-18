from concurrent.futures import ThreadPoolExecutor
from threading import Event
from time import monotonic, sleep

import pytest
from sqlalchemy import func, select, text, update

from app.etl.errors import ETLError
from app.etl.models import attempts, companies, publications, staging, versions
from app.etl.service import PROFILE_VERSION, Pipeline, digest_json, file_hash
from tests.etl_fixtures import csv_file, row, source

pytestmark = pytest.mark.integration


@pytest.fixture
def pipeline(engine):
    return Pipeline(engine, minimum_rows=1, allow_synthetic=True)


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


def test_large_synthetic_version_meets_full_publication_threshold(engine, tmp_path):
    pipeline = Pipeline(engine, allow_synthetic=True)
    path = csv_file(tmp_path / "synthetic-volume.csv", (row(i) for i in range(1, 100002)))
    version = pipeline.ingest(path, source())
    report = pipeline.report(version)
    assert report["report"]["source_records"] == 100001
    assert report["report"]["accepted_records"] == 100001
    assert report["report"]["minimum_records"] == 100000
    approval = publish(pipeline, version)
    pipeline.publish(version, approval)
    with engine.connect() as connection:
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
