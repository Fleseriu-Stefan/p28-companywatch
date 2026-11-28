import json
from contextlib import contextmanager
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from app.etl import cli, subset
from app.etl.cli import main
from app.etl.errors import ETLError
from app.etl.service import quality_deltas
from tests.etl_fixtures import csv_file, row


def test_real_download_needs_explicit_consent_before_database_or_network(capsys):
    with patch("app.etl.cli.downloaded", side_effect=AssertionError("No network allowed")):
        assert main(["ingest", "--edition", "2026-10-19"]) == 2
    assert "real_download_requires_explicit_consent" in capsys.readouterr().err


def test_sources_lists_only_the_approved_resources(capsys):
    assert main(["sources"]) == 0
    output = capsys.readouterr().out
    assert "361e52e3-4590-40af-ae0f-8a15089fc927" in output
    assert "869eac01-8480-4ac6-a18d-d0f044b0db80" in output


def test_real_import_refuses_persistent_raw_storage(capsys):
    with patch("app.etl.cli.require_raw_tmpfs", side_effect=ETLError("raw_tmpfs_required")):
        with patch("app.etl.cli.downloaded", side_effect=AssertionError("No network allowed")):
            assert main(["ingest", "--edition", "2026-10-19", "--allow-real-download"]) == 2
    assert "raw_tmpfs_required" in capsys.readouterr().err


def test_calibration_streams_one_artifact_at_a_time_without_database(monkeypatch, tmp_path, capsys):
    monkeypatch.setattr(cli, "CALIBRATION_TARGET", 2)
    monkeypatch.setattr(subset, "CALIBRATION_TARGET", 2)
    monkeypatch.setattr(cli, "require_raw_tmpfs", lambda: None)
    visited, open_artifacts = [], []

    @contextmanager
    def download(source, directory):
        assert not open_artifacts
        assert directory.name == "etl-private"
        visited.append(source.edition)
        open_artifacts.append(source.edition)
        path = csv_file(tmp_path / source.edition, [row(1), row(2), row(3)])
        try:
            yield SimpleNamespace(path=path, sha256="a" * 64)
        finally:
            open_artifacts.pop()

    monkeypatch.setattr(cli, "downloaded", download)
    with patch("app.etl.cli.create_database_engine") as engine:
        assert main(["calibrate"]) == 2
        assert not visited
        assert main(["calibrate", "--allow-real-download"]) == 0
        engine.assert_not_called()
    result = json.loads(capsys.readouterr().out)
    assert visited == list(subset.SOURCES)
    assert not open_artifacts
    assert all("rank_hash" not in edition for edition in result["editions"].values())
    assert subset.validate_calibration(result) == int(result["threshold"], 16)


@pytest.mark.parametrize(
    ("previous", "current", "duplicates", "expected"),
    [
        (100, 61, 0, []),
        (100, 60, 0, ["accepted_records_decreased_at_least_40_percent"]),
        (100, 59, 0, ["accepted_records_decreased_at_least_40_percent"]),
        (100, 0, 0, ["accepted_records_dropped_to_zero"]),
        (0, 0, 0, []),
        (0, 1, 0, []),
        (
            100,
            60,
            2,
            ["duplicate_records_appeared", "accepted_records_decreased_at_least_40_percent"],
        ),
    ],
)
def test_quality_advisories_and_rate_denominators(previous, current, duplicates, expected):
    def report(accepted, duplicate_rows):
        total = accepted + duplicate_rows
        return {
            "source_records": total,
            "accepted_records": accepted,
            "excluded_records": 0,
            "quarantined_records": duplicate_rows,
            "duplicate_key_records": duplicate_rows,
            "source_legal_forms": {"SRL": total},
            "accepted_legal_forms": {"SRL": accepted},
        }

    result = quality_deltas(report(previous, 0), report(current, duplicates))
    assert result["advisories"] == expected
    assert result["counts"]["accepted_records"]["delta"] == current - previous
    rate = result["rates"]["accepted_records"]
    assert rate["old_denominator"] == previous
    assert rate["new_denominator"] == current + duplicates
    if not previous or current + duplicates == 0:
        assert rate["delta_pp"] is None
    else:
        assert rate["delta_pp"] == pytest.approx(100 * (current / (current + duplicates) - 1))


def test_quality_cli_uses_explicit_ids(capsys):
    result = {"old_version": "old", "new_version": "new", "advisories": []}
    with (
        patch("app.etl.cli.Settings.from_env"),
        patch("app.etl.cli.create_database_engine") as engine,
        patch("app.etl.cli.Pipeline") as pipeline,
    ):
        pipeline.return_value.quality_compare.return_value = result
        assert main(["quality-compare", "old", "new"]) == 0
        pipeline.return_value.quality_compare.assert_called_once_with("old", "new")
        engine.return_value.dispose.assert_called_once_with()
    assert json.loads(capsys.readouterr().out) == result
