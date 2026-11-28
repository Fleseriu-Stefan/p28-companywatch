from contextlib import contextmanager
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from app.etl import cli


@contextmanager
def synthetic_download(*args, **kwargs):
    yield SimpleNamespace(
        path="synthetic.csv",
        final_url="https://data.gov.ro/synthetic.csv",
        etag=None,
        sha256="synthetic-hash",
        size=1,
    )


def test_ingest_cli_selects_long_read_timeout_only_after_download_opt_in(monkeypatch, capsys):
    settings = object()
    engine = MagicMock()
    pipeline = MagicMock()
    pipeline.ingest.return_value = "synthetic-version"
    pipeline.report.return_value = {"state": "review"}
    create_engine = MagicMock(return_value=engine)
    monkeypatch.setattr(cli.Settings, "from_env", lambda: settings)
    monkeypatch.setattr(cli, "create_database_engine", create_engine)
    monkeypatch.setattr(cli, "Pipeline", lambda _: pipeline)
    monkeypatch.setattr(cli, "require_raw_tmpfs", lambda: None)
    monkeypatch.setattr(cli, "downloaded", synthetic_download)
    monkeypatch.setattr(
        cli,
        "read_calibration",
        lambda _: {"editions": {"2026-10-19": {"sha256": "synthetic-hash"}}},
    )

    assert cli.main(["ingest", "--edition", "2026-10-19"]) == 2
    create_engine.assert_not_called()
    assert cli.main(["ingest", "--edition", "2026-10-19", "--allow-real-download"]) == 0
    create_engine.assert_called_once_with(settings, read_timeout=120)
    engine.dispose.assert_called_once()
    assert "review" in capsys.readouterr().out


@pytest.mark.parametrize(
    "arguments",
    [
        ["report", "synthetic-version"],
        ["approve", "synthetic-version", "--report-hash", "synthetic-hash"],
        ["publish", "synthetic-version", "--approval", "synthetic-seal"],
        ["diff", "synthetic-old", "synthetic-new"],
        ["quality-compare", "synthetic-old", "synthetic-new"],
    ],
)
def test_other_etl_commands_keep_default_read_timeout(monkeypatch, arguments):
    settings = object()
    engine = MagicMock()
    create_engine = MagicMock(return_value=engine)
    pipeline = MagicMock()
    pipeline.report.return_value = {}
    pipeline.approve.return_value = "synthetic-seal"
    pipeline.diff.return_value = {}
    pipeline.quality_compare.return_value = {}
    monkeypatch.setattr(cli.Settings, "from_env", lambda: settings)
    monkeypatch.setattr(cli, "create_database_engine", create_engine)
    monkeypatch.setattr(cli, "Pipeline", lambda _: pipeline)

    assert cli.main(arguments) == 0
    create_engine.assert_called_once_with(settings)
    engine.dispose.assert_called_once()
