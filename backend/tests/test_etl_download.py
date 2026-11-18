import hashlib
import stat

import httpx
import pytest

from app.etl.download import downloaded
from app.etl.errors import ETLError
from app.etl.source import Source


def fixture_source(size=None):
    return Source("2026-10-19", "synthetic", "fixture", size, "synthetic")


def test_download_hash_permissions_and_unconditional_cleanup(tmp_path):
    payload = b"\xef\xbb\xbfSYNTHETIC^CSV\r\n"
    client = httpx.Client(
        transport=httpx.MockTransport(
            lambda request: httpx.Response(
                200, content=payload, headers={"content-type": "text/csv"}
            )
        )
    )
    with downloaded(fixture_source(len(payload)), tmp_path / "private", client=client) as artifact:
        path = artifact.path
        assert artifact.sha256 == hashlib.sha256(payload).hexdigest()
        assert artifact.size == len(payload)
        assert stat.S_IMODE(path.stat().st_mode) == 0o600
        assert stat.S_IMODE(path.parent.stat().st_mode) == 0o700
    assert not path.exists()
    assert not list((tmp_path / "private").iterdir())


@pytest.mark.parametrize(
    "headers,payload,expected,cap,code",
    [
        ({"content-type": "text/html"}, b"<html>synthetic</html>", None, 100, "not_csv"),
        ({"content-type": "text/csv"}, b"synthetic", "0" * 64, 100, "hash_mismatch"),
        ({"content-type": "text/csv"}, b"synthetic", None, 2, "download_too_large"),
    ],
)
def test_download_failure_removes_raw_files(tmp_path, headers, payload, expected, cap, code):
    client = httpx.Client(
        transport=httpx.MockTransport(
            lambda request: httpx.Response(200, content=payload, headers=headers)
        )
    )
    with pytest.raises(ETLError, match=code):
        with downloaded(
            fixture_source(),
            tmp_path / "private",
            client=client,
            expected_sha256=expected,
            max_bytes=cap,
        ):
            pass
    assert not list((tmp_path / "private").iterdir())


def test_redirect_to_unapproved_host_is_not_followed(tmp_path):
    calls = []

    def handler(request):
        calls.append(str(request.url))
        return httpx.Response(302, headers={"location": "https://example.invalid/synthetic.csv"})

    client = httpx.Client(transport=httpx.MockTransport(handler))
    with pytest.raises(ETLError, match="source_url_rejected"):
        with downloaded(fixture_source(), tmp_path / "private", client=client):
            pass
    assert len(calls) == 1


def test_downstream_failure_also_removes_temporary_raw(tmp_path):
    client = httpx.Client(
        transport=httpx.MockTransport(
            lambda request: httpx.Response(
                200, content=b"synthetic", headers={"content-type": "text/csv"}
            )
        )
    )
    with pytest.raises(RuntimeError, match="synthetic_failure"):
        with downloaded(fixture_source(), tmp_path / "private", client=client):
            raise RuntimeError("synthetic_failure")
    assert not list((tmp_path / "private").iterdir())


def test_transient_error_retries_are_bounded_and_partial_transfer_is_rejected(
    tmp_path, monkeypatch
):
    monkeypatch.setattr("app.etl.download.time.sleep", lambda delay: None)
    calls = []

    def handler(request):
        calls.append(request)
        return httpx.Response(503)

    with pytest.raises(ETLError, match="download_transient"):
        with downloaded(
            fixture_source(),
            tmp_path / "private",
            client=httpx.Client(transport=httpx.MockTransport(handler)),
        ):
            pass
    assert len(calls) == 3
    assert not list((tmp_path / "private").iterdir())
    client = httpx.Client(
        transport=httpx.MockTransport(lambda request: httpx.Response(206, content=b"synthetic"))
    )
    with pytest.raises(ETLError, match="download_http_error"):
        with downloaded(fixture_source(), tmp_path / "private", client=client):
            pass
