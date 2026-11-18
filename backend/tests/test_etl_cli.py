from unittest.mock import patch

from app.etl.cli import main
from app.etl.errors import ETLError


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
