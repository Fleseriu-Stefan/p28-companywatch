import hashlib
import os
import tempfile
import time
from contextlib import contextmanager, nullcontext
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urljoin, urlsplit

import httpx

from app.etl.errors import ETLError


@dataclass(frozen=True)
class Artifact:
    path: Path
    sha256: str
    size: int
    final_url: str
    etag: str | None


def check_url(url):
    parts = urlsplit(url)
    if (
        parts.scheme != "https"
        or parts.hostname != "data.gov.ro"
        or parts.username
        or parts.password
        or parts.port not in (None, 443)
        or parts.fragment
    ):
        raise ETLError("source_url_rejected")


@contextmanager
def downloaded(source, directory, *, client=None, expected_sha256=None, max_bytes=1073741824):
    """Private, temporary full artifact. Never resume or append an ignored Range response."""
    directory = Path(directory)
    if directory.is_symlink():
        raise ETLError("raw_directory_unsafe")
    directory.mkdir(mode=0o700, parents=True, exist_ok=True)
    if directory.stat().st_uid != os.getuid():
        raise ETLError("raw_directory_unsafe")
    directory.chmod(0o700)
    owned = client is None
    context = (
        httpx.Client(timeout=30, follow_redirects=False, trust_env=False)
        if owned
        else nullcontext(client)
    )
    with tempfile.TemporaryDirectory(prefix="import-", dir=directory) as temp, context as http:
        partial = Path(temp) / "source.part"
        for attempt in range(3):
            url = source.url
            digest = hashlib.sha256()
            size = 0
            try:
                with partial.open("wb") as handle:
                    partial.chmod(0o600)
                    for redirect in range(4):
                        check_url(url)
                        with http.stream(
                            "GET",
                            url,
                            headers={"Accept-Encoding": "identity"},
                            follow_redirects=False,
                        ) as response:
                            if response.is_redirect:
                                if redirect == 3 or "location" not in response.headers:
                                    raise ETLError("redirect_invalid")
                                url = urljoin(url, response.headers["location"])
                                check_url(url)
                                continue
                            if response.status_code in {429, 500, 502, 503, 504}:
                                raise ETLError("download_transient")
                            if response.status_code != 200:
                                raise ETLError("download_http_error")
                            content_type = (
                                response.headers.get("content-type", "").split(";", 1)[0].lower()
                            )
                            if content_type not in {
                                "text/csv",
                                "application/csv",
                                "application/octet-stream",
                            }:
                                raise ETLError("not_csv")
                            if response.headers.get("content-encoding", "identity") != "identity":
                                raise ETLError("unexpected_content_encoding")
                            for chunk in response.iter_bytes(chunk_size=65536):
                                size += len(chunk)
                                if size > max_bytes:
                                    raise ETLError("download_too_large")
                                digest.update(chunk)
                                handle.write(chunk)
                            handle.flush()
                            os.fsync(handle.fileno())
                            content_length = response.headers.get("content-length")
                            if content_length is not None and int(content_length) != size:
                                raise ETLError("transfer_size_mismatch")
                            etag = response.headers.get("etag")
                            break
                if source.size is not None and source.size != size:
                    raise ETLError("source_size_changed")
                if expected_sha256 is not None and digest.hexdigest() != expected_sha256:
                    raise ETLError("hash_mismatch")
                final = partial.with_suffix(".csv")
                partial.replace(final)
                artifact = Artifact(final, digest.hexdigest(), size, url, etag)
                break
            except (httpx.TransportError, ETLError) as error:
                retryable = (
                    isinstance(error, httpx.TransportError) or str(error) == "download_transient"
                )
                if not retryable or attempt == 2:
                    if isinstance(error, ETLError):
                        raise
                    raise ETLError("download_interrupted") from None
                time.sleep(attempt + 1)
        yield artifact
