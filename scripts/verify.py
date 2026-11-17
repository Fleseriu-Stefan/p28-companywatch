"""Run M1 checks in an isolated Compose project; credentials exist only in memory."""

import json
import os
import secrets
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def main() -> None:
    subprocess.run([sys.executable, "docs/agents/tools/ledger-lint.py"], cwd=ROOT, check=True)
    project = f"companywatch-check-{secrets.token_hex(5)}"
    env = os.environ.copy()
    env.update(
        COMPOSE_PROJECT_NAME=project,
        MYSQL_DATABASE="companywatch_test",
        MYSQL_USER="companywatch_test",
        MYSQL_PASSWORD=secrets.token_urlsafe(32),
        MYSQL_ROOT_PASSWORD=secrets.token_urlsafe(32),
        API_PORT="0",
    )
    base = ["docker", "compose", "--env-file", ".env.example", "-p", project]

    def compose(*args: str, capture: bool = False, check: bool = True, extra_file=None):
        command = base + ["-f", "compose.yaml"]
        if extra_file:
            command += ["-f", str(extra_file)]
        return subprocess.run(
            command + list(args),
            cwd=ROOT,
            env=env,
            check=check,
            text=True,
            stdout=subprocess.PIPE if capture else None,
            timeout=600,
        )

    def check_http(url: str, path: str, code: int, body: dict) -> None:
        try:
            with urllib.request.urlopen(url + path, timeout=20) as response:
                actual_code, data = response.status, response.read()
        except urllib.error.HTTPError as error:
            actual_code, data = error.code, error.read()
        assert actual_code == code, (path, actual_code, code)
        assert json.loads(data) == body, path

    def api_url() -> str:
        address = compose("port", "api", "8000", capture=True).stdout.strip()
        return f"http://{address}"

    def await_ready(url: str) -> None:
        deadline = time.monotonic() + 60
        while True:
            try:
                check_http(url, "/health/ready", 200, {"status": "ready"})
                return
            except (OSError, AssertionError):
                if time.monotonic() >= deadline:
                    raise
                time.sleep(1)

    print(f"Isolated verification project: {project}", flush=True)
    try:
        compose("config", "--quiet")
        compose("build", "api", "frontend")
        compose("run", "--rm", "--no-deps", "tests", "ruff", "check", ".")
        compose("run", "--rm", "--no-deps", "tests", "ruff", "format", "--check", ".")
        compose("run", "--rm", "--no-deps", "tests", "ruff", "check", "/checks")
        compose("run", "--rm", "--no-deps", "tests", "ruff", "format", "--check", "/checks")
        compose("run", "--rm", "--no-deps", "tests", "pytest", "-q", "-m", "not integration")
        compose("run", "--rm", "--no-deps", "frontend")
        compose("up", "-d", "--wait", "--wait-timeout", "180", "api")
        compose("run", "--rm", "--no-deps", "tests", "pytest", "-q", "-m", "integration")
        url = api_url()
        check_http(url, "/health/live", 200, {"status": "ok"})
        check_http(url, "/health/ready", 200, {"status": "ready"})
        for path in ("/openapi.json", "/docs"):
            with urllib.request.urlopen(url + path, timeout=20) as response:
                assert response.status == 200, path

        print("Checking database outage and recovery", flush=True)
        compose("stop", "-t", "5", "db")
        check_http(url, "/health/ready", 503, {"status": "not_ready"})
        check_http(url, "/health/live", 200, {"status": "ok"})
        compose("up", "-d", "--wait", "--wait-timeout", "180", "db")
        await_ready(url)

        print("Checking failed-migration startup gate and volume persistence", flush=True)
        compose("down", "--timeout", "5")  # Preserve this project's volume.
        with tempfile.TemporaryDirectory(prefix="companywatch-check-") as temp:
            override = Path(temp) / "failed-migration.yaml"
            override.write_text(
                'services:\n  migrate:\n    command: ["python", "-c", "raise SystemExit(17)"]\n'
            )
            failed = compose("up", "-d", "api", check=False, extra_file=override)
            assert failed.returncode != 0, "A failed migration must block API startup"
            running_api = compose("ps", "--status", "running", "-q", "api", capture=True)
            assert not running_api.stdout.strip(), "API started despite migration failure"
        compose(
            "run",
            "--rm",
            "--no-deps",
            "tests",
            "python",
            "-c",
            "from app.config import Settings; from app.db import create_database_engine; "
            "from alembic.migration import MigrationContext; "
            "engine = create_database_engine(Settings.from_env()); "
            "connection = engine.connect(); "
            "assert MigrationContext.configure(connection).get_current_heads() "
            "== ('0001_baseline',); connection.close(); engine.dispose()",
        )
        compose("up", "-d", "--wait", "--wait-timeout", "180", "api")
        await_ready(api_url())
        print("M1 verification passed", flush=True)
    finally:
        # Only delete resources in the randomly named verification project.
        compose("down", "--volumes", "--remove-orphans", "--timeout", "5")


if __name__ == "__main__":
    main()
