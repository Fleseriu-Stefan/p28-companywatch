"""Run M1/M2 checks in an isolated Compose project; never target development data."""

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
LEGACY_PROJECT = "companywatch"
LEGACY_VOLUME = "companywatch_mysql_data"


class IsolationError(RuntimeError):
    """An unproven target must never be tested or cleaned up automatically."""


def check_git_exclusions():
    ignored = (
        ".env",
        ".env.production",
        "backend/.env.local",
        "data/raw.zip",
        "etl-private/source.part",
        "Od_Firme.Csv",
        "od_firme.csv.zip",
        "Downloads/od_firme-2026-11-04.csv",
        "backup.sql",
        "db/mysql-backup.sql.gz",
        "secrets.yaml",
        "backend/keys/private.pem",
        "backend/.pytest_cache/CACHEDIR.TAG",
        "frontend/dist/index.html",
    )
    addable = (
        ".env.example",
        ".env.production.example",
        "backend/app/etl/service.py",
        "frontend/package-lock.json",
    )
    failures = []
    for path in (*ignored, *addable):
        result = subprocess.run(
            ["git", "check-ignore", "--no-index", "--quiet", "--", path], cwd=ROOT, check=False
        )
        if result.returncode not in (0, 1) or (result.returncode == 0) != (path in ignored):
            failures.append(path)
    if failures:
        raise RuntimeError(f"Unexpected Git ignore coverage: {', '.join(failures)}")
    print("Git artifact exclusions: OK", flush=True)


def check_docker_context_exclusions():
    required = {
        "**/.env",
        "**/.env.*",
        "**/.npmrc",
        "**/credentials",
        "**/credentials.*",
        "**/secrets",
        "**/secrets.*",
        "**/[Oo][Dd]_[Ff][Ii][Rr][Mm][Ee]*",
        "**/[Oo][Nn][Rr][Cc]*.[Zz][Ii][Pp]",
        "**/*.sql",
        "**/*.sql.*",
        "**/*.dump",
        "**/__pycache__",
        "**/.pytest_cache",
        "**/.ruff_cache",
        "**/node_modules",
        "**/dist",
    }
    for context in ("backend", "frontend"):
        path = ROOT / context / ".dockerignore"
        rules = path.read_text().splitlines()
        missing = required.difference(rules)
        if missing:
            raise RuntimeError(f"{context}/.dockerignore is missing: {', '.join(sorted(missing))}")
        if "!**/.env.example" not in rules[rules.index("**/.env.*") + 1 :]:
            raise RuntimeError(f"{context}/.dockerignore must keep shareable .env.example files")
    print("Docker build-context exclusion rules: OK", flush=True)


def docker_output(*args):
    return subprocess.check_output(["docker", *args], cwd=ROOT, text=True, timeout=20).strip()


def prove_disposable_config(compose, project):
    volume = f"{project}_mysql_data"
    network = f"{project}_default"
    config = json.loads(compose("config", "--format", "json", capture=True).stdout)
    volumes, networks = config["volumes"], config["networks"]
    mount = config["services"]["db"]["volumes"]
    if not (
        project.startswith("companywatch-check-")
        and project != LEGACY_PROJECT
        and volume != LEGACY_VOLUME
        and config["name"] == project
        and volumes == {"mysql_data": {"name": volume}}
        and set(networks) == {"default"}
        and networks["default"]["name"] == network
        and not networks["default"].get("external")
        and [(m["type"], m["source"], m["target"]) for m in mount]
        == [("volume", "mysql_data", "/var/lib/mysql")]
        and all(
            set(service["networks"]) == {"default"}
            and "container_name" not in service
            and "network_mode" not in service
            and "volumes_from" not in service
            for service in config["services"].values()
        )
        and all(
            m.get("source") != "mysql_data"
            for name, service in config["services"].items()
            if name != "db"
            for m in service.get("volumes", ())
        )
    ):
        raise IsolationError(
            "Cannot prove the verification project and database volume are isolated"
        )
    if (
        docker_output("ps", "-aq", "--filter", f"label=com.docker.compose.project={project}")
        or volume in docker_output("volume", "ls", "--format", "{{.Name}}").splitlines()
        or network in docker_output("network", "ls", "--format", "{{.Name}}").splitlines()
    ):
        raise IsolationError("Verification project, volume or network already exists")
    print(f"Verified disposable project {project} and volume {volume}", flush=True)
    return volume


def verify_volume_owner(project, volume):
    template = (
        '{{index .Labels "com.docker.compose.project"}} '
        '{{index .Labels "com.docker.compose.volume"}}'
    )
    if docker_output("volume", "inspect", "--format", template, volume) != f"{project} mysql_data":
        raise IsolationError("Verification volume ownership could not be confirmed")


def verify_db_mount(compose, project, volume, *, required=True):
    container = compose("ps", "-a", "-q", "db", capture=True).stdout.strip()
    if not container and not required:
        return
    template = (
        '{{index .Config.Labels "com.docker.compose.project"}} '
        '{{range .Mounts}}{{if eq .Destination "/var/lib/mysql"}}'
        "{{.Type}} {{.Name}}{{end}}{{end}}"
    )
    if not container or docker_output("inspect", "--format", template, container) != (
        f"{project} volume {volume}"
    ):
        raise IsolationError("Verification MySQL container did not mount the approved test volume")
    verify_volume_owner(project, volume)
    print(f"Verified live MySQL mount {volume}", flush=True)


def main() -> None:
    subprocess.run([sys.executable, "docs/agents/tools/ledger-lint.py"], cwd=ROOT, check=True)
    check_git_exclusions()
    check_docker_context_exclusions()
    project = f"companywatch-check-{secrets.token_hex(8)}"
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

    def compose(
        *args: str,
        capture: bool = False,
        check: bool = True,
        extra_file=None,
        opt_in="1",
    ):
        command = base + ["-f", "compose.yaml"]
        if extra_file:
            command += ["-f", str(extra_file)]
        return subprocess.run(
            command + list(args),
            cwd=ROOT,
            env={**env, "COMPANYWATCH_M2_MIGRATE": opt_in},
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

    def assert_api_stopped() -> None:
        running_api = compose("ps", "--status", "running", "-q", "api", capture=True)
        assert not running_api.stdout.strip(), "API started without a successful migration"

    volume = prove_disposable_config(compose, project)
    images = {f"{project}-backend:m2", f"{project}-frontend:m1"}
    image_format = "{{.Repository}}:{{.Tag}}"
    if images.intersection(docker_output("image", "ls", "--format", image_format).splitlines()):
        raise IsolationError("Verification image tags already exist")
    allow_cleanup = True
    try:
        compose("config", "--quiet")
        compose("build", "api", "frontend")
        compose("run", "--rm", "--no-deps", "tests", "ruff", "check", ".")
        compose("run", "--rm", "--no-deps", "tests", "ruff", "format", "--check", ".")
        compose("run", "--rm", "--no-deps", "tests", "ruff", "check", "/checks")
        compose("run", "--rm", "--no-deps", "tests", "ruff", "format", "--check", "/checks")
        compose("run", "--rm", "--no-deps", "tests", "pytest", "-q", "-m", "not integration")
        compose("run", "--rm", "--no-deps", "frontend")
        offline = compose(
            "run",
            "--rm",
            "--no-deps",
            "tests",
            "alembic",
            "upgrade",
            "head",
            "--sql",
            capture=True,
        ).stdout
        assert "CREATE TABLE etl_versions" in offline and "0002_etl" in offline
        for subcommand in ("sources", "--help"):
            compose("run", "--rm", "etl", subcommand)
            assert not compose("ps", "-a", "-q", "db", "migrate", capture=True).stdout.strip()
        legacy_refusal = compose(
            "run",
            "--rm",
            "--no-deps",
            "-e",
            f"M2_MIGRATION_PROJECT={LEGACY_PROJECT}",
            "migrate",
            check=False,
            capture=True,
        )
        assert legacy_refusal.returncode == 2
        assert "M2 migration requires a separate Compose project" in legacy_refusal.stdout
        print(
            "Offline SQL, dependency-free ETL metadata, and legacy migration veto: OK",
            flush=True,
        )
        compose(
            "run",
            "--rm",
            "--no-deps",
            "--entrypoint",
            "python",
            "etl",
            "-c",
            "import os, stat; from pathlib import Path; p=Path('/etl-private'); "
            "assert p.stat().st_uid==os.getuid(); "
            "assert stat.S_IMODE(p.stat().st_mode)==0o700; "
            "assert any(' /etl-private ' in line and ' tmpfs ' in line "
            "for line in Path('/proc/mounts').read_text().splitlines()); "
            "print('Protected ephemeral raw tmpfs: OK')",
        )
        compose("up", "-d", "--wait", "--wait-timeout", "180", "db")
        verify_db_mount(compose, project, volume)
        compose("run", "--rm", "--no-deps", "tests", "alembic", "upgrade", "0001_baseline")
        refused = compose("up", "-d", "api", check=False, opt_in="0")
        assert refused.returncode != 0, "M2 startup did not require migration opt-in"
        refusal = compose("logs", "--no-color", "migrate", capture=True, opt_in="0").stdout
        assert "Set COMPANYWATCH_M2_MIGRATE=1" in refusal
        assert_api_stopped()
        print("M2 startup without explicit migration opt-in blocked: OK", flush=True)
        compose(
            "run",
            "--rm",
            "--no-deps",
            "tests",
            "pytest",
            "-q",
            "tests/test_database.py::test_baseline_and_repeated_migration",
        )
        compose("up", "-d", "--wait", "--wait-timeout", "180", "api")
        verify_db_mount(compose, project, volume)
        compose(
            "run",
            "--rm",
            "--no-deps",
            "tests",
            "pytest",
            "-q",
            "-m",
            "integration",
            "--deselect=tests/test_database.py::test_baseline_and_repeated_migration",
        )
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
        verify_db_mount(compose, project, volume)
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
            assert_api_stopped()
        verify_db_mount(compose, project, volume)
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
            "== ('0002_etl',); connection.close(); engine.dispose()",
        )
        compose("up", "-d", "--wait", "--wait-timeout", "180", "api")
        await_ready(api_url())
        print("M1/M2 verification passed", flush=True)
    except IsolationError:
        allow_cleanup = False
        raise
    finally:
        if allow_cleanup:
            verify_db_mount(compose, project, volume, required=False)
            if volume in docker_output("volume", "ls", "--format", "{{.Name}}").splitlines():
                verify_volume_owner(project, volume)
            compose("down", "--volumes", "--timeout", "5")
            present = images.intersection(
                docker_output("image", "ls", "--format", image_format).splitlines()
            )
            if present:
                docker_output("image", "rm", *sorted(present))


if __name__ == "__main__":
    main()
