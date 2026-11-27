"""Host-side launcher and safety checks for the eight-trial Gate 2 A1 pilot."""

import argparse
import fcntl
import io
import json
import math
import os
import queue
import re
import secrets
import selectors
import shutil
import signal
import subprocess
import sys
import tarfile
import tempfile
import threading
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import asdict, dataclass
from pathlib import Path
from statistics import median
from time import monotonic, sleep
from unittest.mock import patch

from scripts import verify

GIB = 1024**3
STORAGE_BUDGET = 4 * GIB
STORAGE_ABORT = 2 * GIB
FREE_FLOOR = 4 * GIB
START_FREE = 10 * GIB
MYSQL_RAM = 2 * GIB
RUNNER_RAM = GIB
SAMPLE_INTERVAL = 5
MAX_SAMPLE_GAP = 10
PRESSURE_SECONDS = 10
VIEW_SECONDS = 300
TRIAL_SECONDS = 600
CAMPAIGN_SECONDS = 10800
SHUTDOWN_SECONDS = 125
RUNNER_SHUTDOWN_SECONDS = 15
CLEANUP_RESERVE = 360
PREFLIGHT_SECONDS = 90
POLL_SECONDS = 0.05
ROWS = 25001
SCENARIOS = ("retry", "final", "failure_staging", "failure_prepared")
MYSQL_IMAGE = "mysql:8.4@sha256:a81d043930e51745522bd5c430961cf8286f0a23f0a9a2a6e0108f7ea71b0902"
RUNNER_IMAGE = "companywatch-backend:m2"
PROTECTED = {
    "companywatch_mysql_data": "companywatch",
    "companywatch-bench-3458f6c9bd974af5_mysql_data": "companywatch-bench-3458f6c9bd974af5",
}
ROOT = Path(__file__).resolve().parents[1]
PROJECT_PATTERN = r"companywatch-check-[0-9a-f]{16}"
ID_PATTERN = r"[0-9a-f]{64}"
TIMES = ("select_ms", "delete_ms", "commit_ms", "pointer_ms", "pointer_hold_ms", "transaction_ms")
COMMAND_GUARD = ContextVar("pilot_command_guard", default=None)


class PilotAbort(RuntimeError):
    """An invariant or approved operational limit prevents continuing."""


class WorkAbort(PilotAbort):
    """A resource or time limit cancels workload before teardown."""


def require(ok, reason):
    if not ok:
        raise PilotAbort(reason)


@dataclass(frozen=True)
class StorageSample:
    docker_free: int
    windows_free: int
    volume: int
    layers: int
    logs: int
    artifacts: int
    backing_growth: int
    mysql_memory: int
    runner_memory: int
    mysql_cpu_usec: int = 0
    runner_cpu_usec: int = 0
    mysql_io_bytes: int = 0
    runner_io_bytes: int = 0


class BudgetMonitor:
    def __init__(self):
        self.last = None
        self.storage_peak = 0
        self.pressure_since = {}
        self.samples = []

    def observe(self, reading, now):
        require(isinstance(reading, StorageSample), "storage monitor unavailable")
        require(
            all(type(value) is int and value >= 0 for value in asdict(reading).values()),
            "storage monitor returned invalid readings",
        )
        require(
            math.isfinite(now) and (self.last is None or 0 <= now - self.last <= MAX_SAMPLE_GAP),
            "storage monitor sampling gap exceeded",
        )
        self.last = now
        # Backing growth overlaps the tracked Docker files. Artifacts are accounted for separately.
        used = max(reading.volume + reading.layers + reading.logs, reading.backing_growth)
        used += reading.artifacts
        self.storage_peak = max(self.storage_peak, used)
        self.samples.append({**asdict(reading), "observed_storage": used, "monotonic": now})
        require(used < STORAGE_ABORT, "disposable storage threshold reached")
        for key in ("docker_free", "windows_free"):
            require(getattr(reading, key) >= FREE_FLOOR, f"{key} is below the 4 GiB floor")
        for key, limit in (("mysql_memory", MYSQL_RAM), ("runner_memory", RUNNER_RAM)):
            if getattr(reading, key) > limit * 0.85:
                since = self.pressure_since.setdefault(key, now)
                require(now - since < PRESSURE_SECONDS, f"sustained memory pressure: {key}")
            else:
                self.pressure_since.pop(key, None)


def check_deadlines(*, now, held_since=None, trial_since=None, campaign_since=None):
    for started, limit, name in (
        (held_since, VIEW_SECONDS, "read view"),
        (trial_since, TRIAL_SECONDS, "trial"),
        (campaign_since, CAMPAIGN_SECONDS, "campaign"),
    ):
        if started is not None:
            require(now - started < limit, f"{name} deadline reached")


def validate_snapshot(read_view, *, held):
    valid = read_view.get("opened") is held
    if held:
        valid = (
            valid
            and read_view.get("old_visible") is True
            and read_view.get("fresh_visible") is False
            and read_view.get("released") is True
        )
    require(valid, "read-view handshake or visibility proof is missing")


def valid_time(value):
    return type(value) in (int, float) and math.isfinite(value) and value >= 0


def validate_drain(rows, expected):
    require(type(expected) is int and expected >= 0 and bool(rows), "drain cannot reconcile")
    for ordinal, row in enumerate(rows, 1):
        require(
            type(row.get("ordinal")) is int
            and row["ordinal"] == ordinal
            and type(row.get("deleted")) is int
            and 0 <= row["deleted"] <= 1000
            and type(row.get("selected")) is int
            and row["selected"] == row["deleted"]
            and (row["deleted"] == 0) == (ordinal == len(rows)),
            "batch rows or ordinals did not reconcile",
        )
        require(
            all(valid_time(row.get(key)) for key in TIMES)
            and type(row.get("rows_examined")) is int
            and row["rows_examined"] >= 0,
            "invalid batch measurement",
        )
    require(sum(row["deleted"] for row in rows) == expected, "drain totals did not reconcile")


def material_batch_penalty(pairs):
    """Predeclared A2 rule. A single A1 pair cannot recommend a cursor."""
    return len(pairs) == 3 and all(
        all(
            valid_time(pair.get(key))
            for key in ("held_late", "held_early", "control_late", "control_early")
        )
        and (pair["held_late"] - pair["held_early"])
        - (pair["control_late"] - pair["control_early"])
        >= max(2.0, 0.2 * pair["control_late"])
        for pair in pairs
    )


def material_probe_penalty(pairs):
    return len(pairs) == 3 and all(
        valid_time(control) and valid_time(held) and held - control >= max(2.0, 0.2 * control)
        for control, held in pairs
    )


def validate_ownership(project, records, endpoints, runner_mounts):
    require(re.fullmatch(PROJECT_PATTERN, project), "invalid ownership project")
    seen = set()
    ids = set()
    for item in records:
        service, cid = item["service"], item["id"]
        expected = (
            [("volume", f"{project}_mysql_data", "/var/lib/mysql", True)]
            if service == "db"
            else list(runner_mounts)
        )
        require(
            service in {"db", "tests"}
            and service not in seen
            and cid not in ids
            and re.fullmatch(ID_PATTERN, cid)
            and item["project"] == project
            and item["name"] == f"/{project}-{service}-1"
            and item["oneoff"].lower() == "false"
            and set(item["mounts"]) == set(expected)
            and all(mount[1] not in PROTECTED for mount in item["mounts"])
            and set(item["networks"]) <= {f"{project}_default"},
            "unexpected container, mount or network ownership",
        )
        seen.add(service)
        ids.add(cid)
    require(endpoints <= ids, "unexpected endpoint ownership")


def cleanup_owned(marker, prove, stop, remove):
    require(not marker.exists() and not marker.is_symlink(), "automatic cleanup blocked")
    try:
        prove()
        stop()
        prove()
        remove()
    except BaseException:
        latch_cleanup(marker)
        raise


def latch_cleanup(marker):
    try:
        marker.touch(mode=0o600, exist_ok=False)
    except FileExistsError:
        pass


def reap_local_client(process):
    """Bound reaping the host CLI, with no signal sent to a container."""
    try:
        os.killpg(process.pid, signal.SIGTERM)
    except ProcessLookupError:
        pass
    try:
        process.wait(timeout=0.5)
    except subprocess.TimeoutExpired:
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        try:
            process.wait(timeout=0.5)
        except subprocess.TimeoutExpired:
            raise PilotAbort("local subprocess could not be reaped") from None


def command(args, *, env=None, timeout=5, capture=False, input_data=None):
    deadline = monotonic() + timeout
    guard = COMMAND_GUARD.get()

    def remaining():
        limit = deadline - monotonic()
        if guard is not None:
            limit = min(limit, guard())
        require(limit > 0, f"{args[0]} operation deadline reached")
        return limit

    remaining()
    process = subprocess.Popen(
        args,
        cwd=ROOT,
        env=env,
        stdin=subprocess.PIPE if input_data is not None else subprocess.DEVNULL,
        stdout=subprocess.PIPE if capture else subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True,
    )
    try:
        payload = input_data
        while True:
            try:
                raw, _ = process.communicate(input=payload, timeout=min(POLL_SECONDS, remaining()))
            except subprocess.TimeoutExpired:
                payload = None
                continue
            remaining()
            return subprocess.CompletedProcess(
                args, process.returncode, raw.decode() if capture else None
            )
    except BaseException as error:
        try:
            reap_local_client(process)
        except PilotAbort as reap_error:
            error.add_note(str(reap_error))
        raise
    finally:
        for pipe in (process.stdin, process.stdout):
            if pipe is not None:
                pipe.close()


def output(args, *, env=None, timeout=5):
    result = command(args, env=env, timeout=timeout, capture=True)
    require(result.returncode == 0, f"{args[0]} command failed (exit {result.returncode})")
    return result.stdout.strip()


def docker(*args, timeout=5):
    return output(["docker", *args], timeout=timeout)


def daemon_storage(paths=(), logs=(), *, timeout=4):
    # These paths come from the inspected disposable project. Argument passing is literal.
    outer = r"""
pid=$(pidof dockerd)
case "$pid" in ''|*[!0-9]*) exit 1 ;; esac
exec nsenter -t "$pid" -m -- sh -ec '
    stat -f -c "%a %S" /var/lib/docker
    for path do
        case "$path" in
            volume:*) du -sk "${path#volume:}" ;;
            log:*)
                log=${path#log:}
                dir=${log%/*}
                name=${log##*/}
                for file in "$dir/$name" "$dir/$name".*; do
                    if [ -f "$file" ]; then du -sk "$file"; fi
                done ;;
            *) exit 1 ;;
        esac
    done
' monitor "$@"
"""
    data = output(
        [
            "wsl.exe",
            "--cd",
            "/",
            "--distribution",
            "docker-desktop",
            "--exec",
            "sh",
            "-ec",
            outer,
            "monitor",
            *(f"volume:{path}" for path in paths),
            *(f"log:{log}" for log in logs),
        ],
        timeout=timeout,
    ).splitlines()
    free, block = map(int, data[0].split())
    volumes = set(paths)
    volume = log_bytes = 0
    seen = set()
    for line in data[1:]:
        blocks, path = line.split(None, 1)
        require(path not in seen, "storage monitor returned duplicate paths")
        seen.add(path)
        amount = int(blocks) * 1024
        if path in volumes:
            volume += amount
        else:
            require(
                any(path == log or path.startswith(f"{log}.") for log in logs),
                "storage monitor returned an unexpected log path",
            )
            log_bytes += amount
    require(volumes <= seen and set(logs) <= seen, "storage monitor lost a volume or log")
    return free * block, volume, log_bytes


def windows_vhd():
    candidates = list(Path("/mnt/c/Users").glob("*/AppData/Local/Docker/wsl/disk/docker_data.vhdx"))
    require(len(candidates) == 1, "cannot prove the Windows backing filesystem")
    path = candidates[0]
    windows_user = path.parents[5]
    settings = Path(windows_user, "AppData/Roaming/Docker/settings-store.json")
    require(settings.is_file(), "cannot verify Docker Desktop backing path")
    config = json.loads(settings.read_text())
    # Refuse custom storage paths that this environment-specific monitor has not verified.
    configured = config.get("dataFolder") or config.get("diskImageLocation")
    if configured:
        native = output(["wslpath", "-u", configured])
        require(path.is_relative_to(Path(native)), "unexpected Docker Desktop backing path")
    return path


def protected_labels():
    for volume, owner in PROTECTED.items():
        verify.verify_volume_owner(owner, volume)


def preflight():
    require(
        not os.getenv("DOCKER_HOST") and not os.getenv("DOCKER_CONTEXT"), "custom Docker endpoint"
    )
    require(docker("context", "show") == "default", "unexpected Docker context")
    info = json.loads(docker("info", "--format", "{{json .}}"))
    require(
        info["OSType"] == "linux"
        and info["CgroupVersion"] == "2"
        and info["MemoryLimit"]
        and info["CpuCfsQuota"]
        and info["SwapLimit"]
        and info["NCPU"] >= 2
        and info["MemTotal"] >= 4 * GIB
        and "Docker Desktop" in info["OperatingSystem"],
        "Docker resource limits are unavailable",
    )
    vhd = windows_vhd()
    windows_free = shutil.disk_usage(vhd.parent).free
    docker_free, _, _ = daemon_storage()
    require(min(docker_free, windows_free) >= START_FREE, "10 GiB backing storage preflight failed")
    with patch.object(verify, "docker_output", docker):
        protected_labels()
    images = [
        docker("image", "inspect", "--format", "{{.Id}}", name)
        for name in (MYSQL_IMAGE, RUNNER_IMAGE)
    ]
    require(
        all(re.fullmatch(r"sha256:[0-9a-f]{64}", image) for image in images), "unverified images"
    )
    branches = output(["git", "--no-optional-locks", "status", "--short", "--branch"])
    require(branches.splitlines()[0] == "## test/m2-3c-purge-lag", "unexpected pilot branch")
    require(
        output(["git", "rev-parse", "HEAD"]) == "4af5a6fcbcd093a4ad74492c66fd3ec8030e56e0",
        "unexpected pilot baseline",
    )
    require(
        not output(
            [
                "git",
                "diff",
                "--name-only",
                "HEAD",
                "--",
                "backend/app",
                "backend/migrations",
                "compose.yaml",
                "scripts/verify.py",
                "backend/requirements.lock",
                "backend/tests/benchmark_etl_diff.py",
            ]
        ),
        "production or verification input changed",
    )
    evidence = {
        "cgroups": info["CgroupVersion"],
        "daemon_cpus": info["NCPU"],
        "daemon_ram": info["MemTotal"],
        "docker_free": docker_free,
        "windows_free": windows_free,
        "vhd_size": vhd.stat().st_size,
        "mysql_image": images[0],
        "runner_image": images[1],
        "storage_budget": STORAGE_BUDGET,
        "storage_abort": STORAGE_ABORT,
        "sample_seconds": SAMPLE_INTERVAL,
        "maximum_sample_gap_seconds": MAX_SAMPLE_GAP,
    }
    return vhd, evidence


def bounded_preflight():
    deadline = monotonic() + PREFLIGHT_SECONDS
    result = queue.SimpleQueue()

    def probe():
        token = COMMAND_GUARD.set(lambda: deadline - monotonic())
        try:
            result.put(preflight())
        except Exception as error:
            result.put(error)
        finally:
            COMMAND_GUARD.reset(token)

    threading.Thread(target=probe, daemon=True).start()
    try:
        answer = result.get(timeout=max(0, deadline - monotonic()))
    except queue.Empty:
        raise PilotAbort("read-only preflight deadline reached") from None
    if isinstance(answer, Exception):
        raise answer
    return answer


MYSQL_SETUP = """
UPDATE performance_schema.setup_consumers
SET ENABLED='YES' WHERE NAME IN ('global_instrumentation','thread_instrumentation',
  'events_statements_current','events_statements_history');
GRANT SELECT ON performance_schema.threads TO 'companywatch_test'@'%';
GRANT SELECT ON performance_schema.events_statements_history TO 'companywatch_test'@'%';
GRANT SELECT ON performance_schema.status_by_thread TO 'companywatch_test'@'%';
GRANT PROCESS ON *.* TO 'companywatch_test'@'%';
"""


def runner_archive():
    tracked = output(["git", "ls-files", "-z", "--", "backend/app", "backend/migrations"])
    paths = [name for name in tracked.split("\0") if name]
    paths.extend(
        (
            "backend/alembic.ini",
            "backend/requirements.lock",
            "backend/tests/__init__.py",
            "backend/tests/etl_fixtures.py",
            "backend/tests/benchmark_etl_purge.py",
        )
    )
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode="w:") as archive:
        for name in sorted(paths):
            path = ROOT / name
            require(
                path.is_file() and path.resolve() == path and not path.name.startswith(".env"),
                "unapproved runner archive path",
            )
            require(
                buffer.tell() + path.stat().st_size <= 1024 * 1024,
                "runner archive exceeds setup budget",
            )
            archive.add(path, arcname=str(path.relative_to(ROOT / "backend")), recursive=False)
    require(buffer.tell() <= 1024 * 1024, "runner archive exceeds setup budget")
    return buffer.getvalue()


# Runs as the runner's unprivileged user. Validate every destination before the
# first write, and anchor each write to a no-follow directory descriptor.
ARCHIVE_INSTALL = r"""
import io
import os
import secrets
import shutil
import stat
import sys
import tarfile
from contextlib import contextmanager
from pathlib import PurePosixPath

flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
limit = 1024 * 1024

@contextmanager
def directory(root, components, *, create=False):
    fd = os.dup(root)
    try:
        for name in components:
            try:
                child = os.open(name, flags, dir_fd=fd)
            except FileNotFoundError:
                if not create:
                    raise
                os.mkdir(name, 0o755, dir_fd=fd)
                child = os.open(name, flags, dir_fd=fd)
            os.close(fd)
            fd = child
        yield fd
    finally:
        os.close(fd)

def check_file(parent, name):
    try:
        mode = os.stat(name, dir_fd=parent, follow_symlinks=False).st_mode
    except FileNotFoundError:
        return
    if not stat.S_ISREG(mode):
        raise ValueError("unsafe archive destination")

destination = PurePosixPath(sys.argv[1])
if not destination.is_absolute() or ".." in destination.parts:
    raise ValueError("unsafe archive destination")
payload = sys.stdin.buffer.read(limit + 1)
if not payload or len(payload) > limit:
    raise ValueError("unsafe archive size")
system_root = os.open("/", flags)
try:
    with (
        directory(system_root, destination.parts[1:]) as root,
        tarfile.open(fileobj=io.BytesIO(payload), mode="r:") as archive,
    ):
        entries = {}
        for entry in archive:
            path = PurePosixPath(entry.name)
            if (not entry.isfile() or path.is_absolute() or not path.parts
                or ".." in path.parts or path.parts in entries):
                raise ValueError("unsafe archive entry")
            entries[path.parts] = entry
            try:
                with directory(root, path.parts[:-1]) as parent:
                    check_file(parent, path.name)
            except FileNotFoundError:
                pass
        if not entries:
            raise ValueError("empty archive")
        if any(parts[:i] in entries for parts in entries for i in range(1, len(parts))):
            raise ValueError("archive file conflicts with a destination directory")
        for parts, entry in entries.items():
            with directory(root, parts[:-1], create=True) as parent:
                check_file(parent, parts[-1])
                temp = ".purge-a1-" + secrets.token_hex(8)
                fd = os.open(temp, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
                             0o644, dir_fd=parent)
                try:
                    with os.fdopen(fd, "wb") as target, archive.extractfile(entry) as source:
                        shutil.copyfileobj(source, target)
                    os.replace(temp, parts[-1], src_dir_fd=parent, dst_dir_fd=parent)
                finally:
                    try:
                        os.unlink(temp, dir_fd=parent)
                    except FileNotFoundError:
                        pass
finally:
    os.close(system_root)
"""


INSPECT_FIELDS = (
    ".Id",
    ".Name",
    ".Config.Labels",
    ".Mounts",
    ".NetworkSettings.Networks",
    ".State",
    ".HostConfig",
    ".LogPath",
    ".Image",
)
INSPECT_FORMAT = " ".join("{{json " + name + "}}" for name in INSPECT_FIELDS)


def inspect_container(cid, *, size=False, timeout=5):
    result = docker(
        "container",
        "inspect",
        *(["--size"] if size else []),
        "--format",
        INSPECT_FORMAT + " {{json .SizeRw}}" if size else INSPECT_FORMAT,
        cid,
        timeout=timeout,
    )
    decoder = json.JSONDecoder()
    fields = []
    for _ in INSPECT_FIELDS:
        item, end = decoder.raw_decode(result)
        fields.append(item)
        result = result[end:].lstrip()
    inspected_id, name, labels, mounts, networks, state, host, log, image = fields
    require(inspected_id == cid, "unexpected Docker inspect container identity")
    record = {
        "id": inspected_id,
        "name": name,
        "project": labels.get("com.docker.compose.project"),
        "service": labels.get("com.docker.compose.service"),
        "oneoff": labels.get("com.docker.compose.oneoff", ""),
        "mounts": [
            (m["Type"], m.get("Name", m["Source"]), m["Destination"], m["RW"]) for m in mounts
        ],
        "networks": list(networks or {}),
        "state": state,
        "host": host,
        "log": log,
        "image": image,
    }
    if size:
        record["writable"] = json.loads(result)
    return record


def counters(cid, *, timeout=3):
    lines = docker(
        "exec",
        cid,
        "sh",
        "-ec",
        "cat /sys/fs/cgroup/memory.current /sys/fs/cgroup/cpu.stat /sys/fs/cgroup/io.stat",
        timeout=timeout,
    ).splitlines()
    cpu = next(int(line.split()[1]) for line in lines if line.startswith("usage_usec "))
    io = sum(
        int(amount) for line in lines[1:] for amount in re.findall(r"\b[wr]bytes=(\d+)\b", line)
    )
    return int(lines[0]), cpu, io


class DisposableTrial:
    def __init__(self, workspace, vhd, evidence, campaign_since):
        self.project = f"companywatch-check-{secrets.token_hex(8)}"
        self.volume = f"{self.project}_mysql_data"
        self.network = f"{self.project}_default"
        self.marker = workspace / f"{self.project}.cleanup-blocked"
        self.env = {k: v for k, v in os.environ.items() if not k.startswith(("COMPOSE_", "MYSQL_"))}
        self.env.update(
            COMPOSE_PROJECT_NAME=self.project,
            MYSQL_DATABASE="companywatch_test",
            MYSQL_USER="companywatch_test",
            MYSQL_PASSWORD=secrets.token_urlsafe(32),
            MYSQL_ROOT_PASSWORD=secrets.token_urlsafe(32),
        )
        self.vhd = vhd
        self.evidence = evidence
        self.workspace = workspace
        self.campaign_since = campaign_since
        self.started = monotonic()
        self.held_since = None
        self.view_opened = False
        self.view_closed = False
        self.monitor = BudgetMonitor()
        self.fs_start = evidence["docker_free"]
        self.windows_start = evidence["windows_free"]
        self.vhd_start = evidence["vhd_size"]
        self.containers = {}
        self.result = None
        self.in_cleanup = False
        self.resources_requested = False
        self.pending_starts = set()
        self.started_containers = set()
        self.retiring_containers = set()
        self.retiring_volume = False
        self.watch_started = None
        self.watch_last = None
        self.watch_error = None
        self.watch_lock = threading.Lock()
        self.shutdown_monitor_error = None
        self.watch_stop = threading.Event()
        self.watch_thread = None
        self.mysql_exit = None
        self.runner_exit = None
        self.shutdown_evidence = {}
        self.workload_unverified = False
        self.cleanup_blocked = False
        self.mounts = (("bind", str(ROOT / "scripts"), "/checks", False),)
        logging = {"driver": "json-file", "options": {"max-size": "5m", "max-file": "2"}}
        settings = {
            "services": {
                "db": {
                    "cpus": 2,
                    "mem_limit": MYSQL_RAM,
                    "memswap_limit": MYSQL_RAM,
                    "logging": logging,
                    "pull_policy": "never",
                },
                "tests": {
                    "image": RUNNER_IMAGE,
                    "command": ["sleep", "infinity"],
                    "init": True,
                    "mem_limit": RUNNER_RAM,
                    "memswap_limit": RUNNER_RAM,
                    "logging": logging,
                    "pull_policy": "never",
                },
            },
        }
        override = workspace / f"{self.project}.json"
        override.write_text(json.dumps(settings))
        self.compose_base = [
            "docker",
            "compose",
            "--env-file",
            ".env.example",
            "--profile",
            "tools",
            "-p",
            self.project,
            "-f",
            "compose.yaml",
            "-f",
            str(override),
        ]

    def compose(self, *args, capture=False):
        result = command(
            self.compose_base + list(args),
            env=self.env,
            timeout=7,
            capture=capture,
        )
        require(result.returncode == 0, f"Compose command failed (exit {result.returncode})")
        return result

    def verification(self, check, *args):
        # Keep the stock isolation checks and put their Docker calls under the same deadline.
        with patch.object(verify, "docker_output", docker):
            return check(*args)

    def start_watchdog(self):
        self.watch_started = monotonic()
        self.watch_thread = threading.Thread(target=self.watch_resources, daemon=True)
        self.watch_thread.start()
        while self.watch_last is None:
            self.guard()
            self.watch_stop.wait(POLL_SECONDS)
        self.guard()

    def watch_resources(self):
        while not self.watch_stop.is_set():
            tick = monotonic()
            try:
                self.sampling()
            except Exception as error:
                self.latch_monitor_failure(str(error) or type(error).__name__)
            else:
                self.watch_last = self.monitor.last
            self.watch_stop.wait(max(0, tick + SAMPLE_INTERVAL - monotonic()))

    def stop_watchdog(self):
        self.watch_stop.set()
        if self.watch_thread is not None:
            self.watch_thread.join(timeout=POLL_SECONDS)
            if self.watch_thread.is_alive() and self.watch_error is None:
                # A sample already in flight gets the remainder of its time budget.
                deadline = min(self.monitor_deadline(), self.campaign_since + CAMPAIGN_SECONDS)
                remaining = max(0, deadline - monotonic())
                self.watch_thread.join(timeout=remaining)
            if self.watch_thread.is_alive():
                self.latch_monitor_failure("resource monitor did not finish before its deadline")
        self.shutdown_monitor_error = self.watch_error

    def latch_monitor_failure(self, reason):
        with self.watch_lock:
            if self.watch_error is None:
                self.watch_error = reason

    def monitor_deadline(self):
        last = self.watch_last
        return (self.watch_started if last is None else last) + MAX_SAMPLE_GAP

    def guard(self):
        now = monotonic()
        if self.watch_started is not None:
            if now >= self.monitor_deadline():
                self.latch_monitor_failure("resource monitor sampling gap exceeded")
            if not self.in_cleanup and self.watch_error is not None:
                raise WorkAbort(self.watch_error)
        campaign_left = self.campaign_since + CAMPAIGN_SECONDS - now
        require(campaign_left > 0, "campaign deadline reached")
        if self.in_cleanup:
            # A resource alarm cancels work, while verified graceful shutdown still runs.
            return campaign_left
        try:
            check_deadlines(now=now, held_since=self.held_since, trial_since=self.started)
        except PilotAbort as error:
            raise WorkAbort(str(error)) from None
        if campaign_left <= CLEANUP_RESERVE:
            raise WorkAbort("campaign has reached its cleanup reserve")
        return min(
            campaign_left - CLEANUP_RESERVE,
            self.started + TRIAL_SECONDS - now,
            self.held_since + VIEW_SECONDS - now if self.held_since is not None else math.inf,
        )

    def scope(self, *, discover=False):
        try:
            return self.check_scope(discover=discover)
        except WorkAbort:
            # A canceled check makes no ownership claim. Teardown must prove it.
            raise
        except BaseException:
            self.block_cleanup()
            raise

    def block_cleanup(self):
        self.cleanup_blocked = True
        latch_cleanup(self.marker)

    def check_scope(self, *, discover=False):
        label = f"label=com.docker.compose.project={self.project}"
        ids = docker("ps", "-aq", "--no-trunc", "--filter", label).splitlines()
        compose_ids = self.compose("ps", "-a", "-q", "--no-trunc", capture=True).stdout.splitlines()
        require(set(ids) == set(compose_ids), "container ownership mismatch")
        if self.containers and not discover:
            require(set(ids) == set(self.containers.values()), "owned container identities changed")
        records = [inspect_container(cid) for cid in ids]
        volumes = set(docker("volume", "ls", "-q", "--filter", label).splitlines())
        has_volume = self.volume in docker("volume", "ls", "-q").splitlines()
        require(volumes == ({self.volume} if has_volume else set()), "unexpected volume ownership")
        if has_volume:
            self.verification(verify.verify_volume_owner, self.project, self.volume)
        rows = docker("network", "ls", "--no-trunc", "--format", "{{.ID}} {{.Name}}").splitlines()
        matching = [line.split()[0] for line in rows if line.split()[1] == self.network]
        require(len(matching) <= 1, "ambiguous network ownership")
        network = matching[0] if matching else None
        # Compare network names by full ID. Quiet output is deliberately made untruncated.
        owned_networks = set(
            docker("network", "ls", "--no-trunc", "-q", "--filter", label).splitlines()
        )
        require(owned_networks == ({network} if network else set()), "unexpected network ownership")
        require(not records or (network and has_volume), "resources missing during ownership check")
        endpoints = {}
        if network:
            raw = docker(
                "network", "inspect", "--format", "{{json .Labels}}\n{{json .Containers}}", network
            )
            labels, attached = map(json.loads, raw.splitlines())
            require(
                labels.get("com.docker.compose.project") == self.project
                and labels.get("com.docker.compose.network") == "default",
                "network ownership mismatch",
            )
            endpoints = attached or {}
        validate_ownership(self.project, records, set(endpoints), self.mounts)
        expected_endpoints = {
            item["id"]: item["name"][1:] for item in records if item["state"]["Status"] == "running"
        }
        require(
            {cid: endpoint["Name"] for cid, endpoint in endpoints.items()} == expected_endpoints,
            "unexpected attached endpoint ownership",
        )
        if records and "db" in {item["service"] for item in records}:
            self.verification(verify.verify_db_mount, self.compose, self.project, self.volume)
        return records, network, has_volume

    def sampling(self):
        now = monotonic()
        last = self.monitor.last
        deadline = (now if last is None else last) + MAX_SAMPLE_GAP

        def remaining(maximum):
            seconds = deadline - monotonic()
            require(seconds > 0, "storage monitor sampling gap exceeded")
            return min(seconds, maximum)

        try:
            expected_ids = set(self.containers.values())
            label = f"label=com.docker.compose.project={self.project}"

            def listed_containers():
                return set(
                    docker(
                        "ps", "-aq", "--no-trunc", "--filter", label, timeout=remaining(5)
                    ).splitlines()
                )

            def listed_volumes():
                return docker(
                    "volume", "ls", "-q", "--filter", label, timeout=remaining(5)
                ).splitlines()

            ids = listed_containers() if self.resources_requested else set()
            require(
                expected_ids - self.retiring_containers <= ids,
                "resource monitor lost an expected container",
            )
            require(
                not expected_ids or ids <= expected_ids,
                "resource monitor found a foreign container",
            )
            records = []
            for cid in sorted(ids):
                require(
                    re.fullmatch(ID_PATTERN, cid), "resource monitor found an invalid container ID"
                )
                try:
                    records.append(inspect_container(cid, size=True, timeout=remaining(5)))
                except PilotAbort:
                    if cid not in self.retiring_containers or cid in listed_containers():
                        raise
            validate_ownership(self.project, records, set(), self.mounts)
            require(
                all(
                    type(record["writable"]) is int and record["writable"] >= 0
                    for record in records
                ),
                "storage monitor cannot inspect writable layers",
            )
            layers = sum(record["writable"] for record in records)
            logs = []
            memory = {"db": 0, "tests": 0}
            cpu = {"db": 0, "tests": 0}
            io = {"db": 0, "tests": 0}
            for record in records:
                base = f"/var/lib/docker/containers/{record['id']}/"
                path = record["log"]
                state = record["state"]["Status"]
                if state in {"running", "exited"}:
                    require(
                        path == f"{base}{record['id']}-json.log", "unexpected container log path"
                    )
                    logs.append(path)
                if state == "running":
                    key = record["service"]
                    try:
                        memory[key], cpu[key], io[key] = counters(
                            record["id"], timeout=remaining(3)
                        )
                    except PilotAbort:
                        require(
                            self.in_cleanup
                            and inspect_container(record["id"], timeout=remaining(5))["state"][
                                "Status"
                            ]
                            == "exited",
                            "resource monitor lost running cgroup readings",
                        )
            paths = ()
            volumes = listed_volumes() if self.resources_requested else []
            require(volumes in ([], [self.volume]), "resource monitor found a foreign volume")
            require(
                not expected_ids or self.retiring_volume or volumes,
                "resource monitor lost its volume",
            )
            if volumes:
                try:
                    info = docker(
                        "volume",
                        "inspect",
                        "--format",
                        '{{.Mountpoint}} {{index .Labels "com.docker.compose.project"}} '
                        '{{index .Labels "com.docker.compose.volume"}}',
                        self.volume,
                        timeout=remaining(5),
                    )
                except PilotAbort:
                    if not self.retiring_volume or self.volume in listed_volumes():
                        raise
                else:
                    volume_path = f"/var/lib/docker/volumes/{self.volume}/_data"
                    require(
                        info == f"{volume_path} {self.project} mysql_data",
                        "unexpected disposable volume monitor path",
                    )
                    paths = (volume_path,)
            try:
                docker_free, volume, log_bytes = daemon_storage(paths, logs, timeout=remaining(4))
            except PilotAbort:
                # A removal can race du. Retry only after observing disappearance
                # of a resource this teardown explicitly scheduled for removal.
                still_present = listed_containers() if self.retiring_containers else ids
                kept_logs = [
                    log
                    for log in logs
                    if Path(log).parent.name not in self.retiring_containers - still_present
                ]
                kept_paths = (
                    () if paths and self.retiring_volume and not listed_volumes() else paths
                )
                if kept_paths == paths and kept_logs == logs:
                    raise
                docker_free, volume, log_bytes = daemon_storage(
                    kept_paths, kept_logs, timeout=remaining(4)
                )
            windows_free = shutil.disk_usage(self.vhd.parent).free
            growth = max(
                0,
                self.fs_start - docker_free,
                self.windows_start - windows_free,
                self.vhd.stat().st_size - self.vhd_start,
            )
            artifacts = sum(
                p.stat().st_blocks * 512 for p in self.workspace.iterdir() if p.is_file()
            )
            remaining(10)
            self.monitor.observe(
                StorageSample(
                    docker_free,
                    windows_free,
                    volume,
                    layers,
                    log_bytes,
                    artifacts,
                    growth,
                    memory["db"],
                    memory["tests"],
                    cpu["db"],
                    cpu["tests"],
                    io["db"],
                    io["tests"],
                ),
                monotonic(),
            )
        except (
            OSError,
            ValueError,
            TypeError,
            IndexError,
            KeyError,
            StopIteration,
            subprocess.SubprocessError,
        ) as error:
            raise PilotAbort("resource monitor unavailable or invalid") from error

    def handle_event(self, event):
        kind = event.get("kind")
        if kind == "view_open":
            require(not self.view_opened, "read-view handshake repeated")
            self.view_opened, self.held_since = True, monotonic()
        elif kind == "view_release":
            require(
                self.held_since is not None and not self.view_closed,
                "read-view handshake out of order",
            )
            self.view_closed, self.held_since = True, None
        elif kind == "report":
            require(self.result is None, "multiple trial reports")
            self.result = event["result"]
        elif kind == "failure":
            code = event.get("code", "")
            require(
                re.fullmatch(r"purge_a1_[a-z_]+(?::[a-z_]+)?", code), "unrecognized worker failure"
            )
            raise PilotAbort(code)
        else:
            raise PilotAbort("invalid pilot worker event")

    def run_owned(self, args, *, events=False, input_data=None):
        invocation = ["docker", "exec", self.containers["tests"], *args]
        # A lost Docker CLI does not prove the remote process or its sessions ended.
        self.guard()
        self.workload_unverified = True
        if input_data is not None:
            invocation.insert(2, "-i")
            result = command(invocation, input_data=input_data)
            require(result.returncode == 0, "unsafe archive destination or archive install failed")
            self.workload_unverified = False
            return
        process = subprocess.Popen(
            invocation,
            cwd=ROOT,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE if events else subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )
        buffered = b""
        try:
            with selectors.DefaultSelector() as selector:
                if process.stdout:
                    selector.register(process.stdout, selectors.EVENT_READ)
                while True:
                    pause = min(POLL_SECONDS, self.guard())
                    require(pause > 0, "deadline reached while running the worker")
                    if events:
                        for key, _ in selector.select(timeout=pause):
                            data = os.read(key.fd, 65536)
                            if not data:
                                selector.unregister(key.fileobj)
                            buffered += data
                            require(len(buffered) <= 2 * 1024 * 1024, "oversized worker output")
                            while b"\n" in buffered:
                                line, buffered = buffered.split(b"\n", 1)
                                self.guard()
                                self.handle_event(json.loads(line))
                    else:
                        sleep(pause)
                    if process.poll() is not None and not selector.get_map():
                        require(process.returncode == 0 and not buffered, "pilot worker failed")
                        self.workload_unverified = False
                        return
        except BaseException as error:
            if process.poll() is None and events:
                # Allow bounded cooperative worker termination after a work deadline.
                self.in_cleanup = True
                try:
                    cid = self.containers["tests"]
                    record = inspect_container(cid)
                    validate_ownership(self.project, [record], set(), self.mounts)
                    if record["id"] == cid and record["state"]["Status"] == "running":
                        docker(
                            "exec",
                            self.containers["tests"],
                            "sh",
                            "-ec",
                            'read -r pid < /tmp/purge-a1.pid; case "$pid" in '
                            "''|*[!0-9]*) exit 1 ;; esac; "
                            'test "$pid" -gt 1; kill -TERM "$pid"',
                            timeout=3,
                        )
                except (
                    PilotAbort,
                    verify.IsolationError,
                    OSError,
                    subprocess.SubprocessError,
                ) as stop_error:
                    error.add_note(f"Worker termination: {stop_error}")
            try:
                reap_local_client(process)
            except PilotAbort as reap_error:
                error.add_note(str(reap_error))
            raise
        finally:
            if process.stdout:
                process.stdout.close()

    def install_monitor_queries(self):
        # Root is used only on this verified synthetic instance to give the test user
        # read access to server metrics. Credentials stay inside the container.
        self.workload_unverified = True
        result = command(
            [
                "docker",
                "exec",
                "-i",
                self.containers["db"],
                "sh",
                "-ec",
                'MYSQL_PWD="$MYSQL_ROOT_PASSWORD" exec mysql --user=root --batch',
            ],
            input_data=MYSQL_SETUP.encode(),
            timeout=5,
        )
        require(result.returncode == 0, "failed to enable test-only MySQL monitoring")
        self.workload_unverified = False

    def start(self):
        require(
            min(self.fs_start, self.windows_start) >= START_FREE,
            "10 GiB backing storage preflight failed",
        )
        require(
            all(
                self.monitor.samples[-1][name] >= START_FREE
                for name in ("docker_free", "windows_free")
            )
            if self.monitor.samples
            else self.watch_started is None,
            "10 GiB backing storage preflight failed",
        )
        self.resources_requested = True
        try:
            self.compose("create", "--no-build", "db", "tests")
        except BaseException:
            # The daemon may still be creating resources after losing the CLI.
            self.block_cleanup()
            raise
        records, _, _ = self.scope(discover=True)
        self.containers = {record["service"]: record["id"] for record in records}
        require(set(self.containers) == {"db", "tests"}, "missing isolated services")
        for record in records:
            db = record["service"] == "db"
            if not db:
                require(record["host"].get("Init") is True, "runner init is not enabled")
            ram = MYSQL_RAM if db else RUNNER_RAM
            image = self.evidence["mysql_image" if db else "runner_image"]
            require(record["image"] == image, "running image differs from preflight")
            require(
                record["host"]["Memory"] == ram
                and record["host"]["MemorySwap"] == ram
                and (not db or record["host"]["NanoCpus"] == 2_000_000_000),
                "configured effective resource limits differ from approval",
            )
            require(
                record["host"]["LogConfig"]["Type"] == "json-file"
                and record["host"]["LogConfig"]["Config"] == {"max-size": "5m", "max-file": "2"},
                "log rotation does not match the budget assumptions",
            )
        for cid in self.containers.values():
            self.pending_starts.add(cid)
            docker("start", cid)
            self.started_containers.add(cid)
            self.pending_starts.remove(cid)
        self.scope()
        for service, cid in self.containers.items():
            ram = MYSQL_RAM if service == "db" else RUNNER_RAM
            limits = docker(
                "exec", cid, "cat", "/sys/fs/cgroup/memory.max", "/sys/fs/cgroup/memory.swap.max"
            ).splitlines()
            require(limits == [str(ram), "0"], "live memory or swap limit differs from approval")
            if service == "db":
                limit, period = map(
                    int, docker("exec", cid, "cat", "/sys/fs/cgroup/cpu.max").split()
                )
                require(period > 0 and limit == 2 * period, "live CPU quota differs from approval")
        self.run_owned(
            ["python", "-I", "-B", "-c", ARCHIVE_INSTALL, "/app"], input_data=runner_archive()
        )
        startup_deadline = monotonic() + 90
        while True:
            left = startup_deadline - monotonic()
            require(left > 0, "MySQL startup deadline reached")
            db = inspect_container(self.containers["db"], timeout=min(left, 5))
            require(db["state"]["Running"], "MySQL stopped during startup")
            if db["state"]["Health"]["Status"] == "healthy":
                break
            sleep(min(0.5, max(0, startup_deadline - monotonic())))
        self.run_owned(
            [
                "python",
                "-B",
                "-c",
                "from tests.benchmark_etl_purge import safe_target; safe_target()",
            ]
        )
        self.install_monitor_queries()
        self.run_owned(["alembic", "upgrade", "head"])

    def stop_and_remove(self):
        self.in_cleanup = True
        require(not self.cleanup_blocked, "automatic cleanup blocked")
        stopped = {}

        def prove():
            records, network, has_volume = self.scope()
            identity = (frozenset((r["service"], r["id"]) for r in records), network, has_volume)
            require(
                stopped.setdefault("identity", identity) == identity,
                "owned shutdown resources changed",
            )
            stopped.update(records=records, network=network, volume=has_volume)

        def verify_never_started(record):
            state, cid = record["state"], record["id"]
            never_started_at = "0001-01-01T00:00:00Z"
            require(
                state.get("Status") == "created"
                and state.get("StartedAt") == state.get("FinishedAt") == never_started_at
                and type(state.get("Pid")) is int
                and state["Pid"] == 0
                and state.get("Running") is False
                and cid not in self.pending_starts
                and cid not in self.started_containers,
                "container could not be proven never to have started",
            )

        def stop_container(record):
            cid, service, state = record["id"], record["service"], record["state"]["Status"]
            require(state in {"running", "exited", "created"}, "unexpected shutdown state")
            evidence = {
                "container_id": cid,
                "initial_status": state,
                "wait_exit_code": None,
                "inspect_status": None,
                "inspect_exit_code": None,
            }
            self.shutdown_evidence[service] = evidence
            if state == "created":
                verify_never_started(record)
                return
            db = service == "db"
            cutoff = monotonic() + (SHUTDOWN_SECONDS if db else RUNNER_SHUTDOWN_SECONDS)
            if state == "running":
                docker("container", "kill", "--signal=TERM", cid)
            left = cutoff - monotonic()
            require(left > 0, "graceful shutdown deadline reached")
            result = command(["docker", "container", "wait", cid], timeout=left, capture=True)
            require(monotonic() <= cutoff, "graceful shutdown deadline reached")
            require(result.returncode == 0, "could not verify graceful shutdown")
            exit_code = result.stdout.strip()
            if re.fullmatch(r"[0-9]{1,3}", exit_code):
                evidence["wait_exit_code"] = int(exit_code)
            if db:
                require(exit_code == "0", "MySQL graceful shutdown did not exit 0")
                self.mysql_exit = 0
            else:
                require(
                    exit_code in {"0", str(128 + signal.SIGTERM)}, "unexpected runner exit status"
                )
                self.runner_exit = int(exit_code)

        def stop():
            require(
                not self.workload_unverified and self.held_since is None,
                "workload termination could not be verified",
            )
            failures = []
            for service in ("tests", "db"):
                record = next((r for r in stopped["records"] if r["service"] == service), None)
                if record is None:
                    continue
                try:
                    stop_container(record)
                except (PilotAbort, OSError, subprocess.SubprocessError) as error:
                    failures.append(error)
                    if service == "tests":
                        try:
                            prove()
                        except Exception as proof_error:
                            error.add_note(f"Ownership recheck failed: {proof_error}")
                            raise error from None
            if failures:
                first, *others = failures
                for error in others:
                    first.add_note(f"MySQL shutdown also failed: {error}")
                raise first

        def remove():
            # The preceding ownership pass reads fresh ordinary Docker inspect metadata.
            for record in stopped["records"]:
                evidence = self.shutdown_evidence[record["service"]]
                state = record["state"]
                evidence.update(
                    inspect_status=state.get("Status"), inspect_exit_code=state.get("ExitCode")
                )
            for record in stopped["records"]:
                service = record["service"]
                evidence = self.shutdown_evidence[service]
                if evidence["initial_status"] == "created":
                    verify_never_started(record)
                    continue
                require(
                    evidence["inspect_status"] == "exited", f"{service} is not exited on inspect"
                )
                code = evidence["inspect_exit_code"]
                require(
                    type(code) is int and code == evidence["wait_exit_code"],
                    f"{service} inspect exit code does not match Docker wait",
                )
            for record in stopped["records"]:
                self.retiring_containers.add(record["id"])
                docker("container", "rm", record["id"])
            if stopped["network"]:
                docker("network", "rm", stopped["network"])
            if stopped["volume"]:
                self.verification(verify.verify_volume_owner, self.project, self.volume)
                self.retiring_volume = True
                docker("volume", "rm", self.volume)
            require(
                not docker(
                    "ps", "-aq", "--filter", f"label=com.docker.compose.project={self.project}"
                )
                and self.volume not in docker("volume", "ls", "-q").splitlines()
                and self.network
                not in docker("network", "ls", "--format", "{{.Name}}").splitlines(),
                "disposable resources remain",
            )
            self.verification(protected_labels)

        cleanup_owned(self.marker, prove, stop, remove)


def check_report(result, scenario, held, *, project=None):
    try:
        validate_report(result, scenario, held, project)
    except (TypeError, ValueError, AttributeError, KeyError, IndexError, OverflowError) as error:
        raise PilotAbort("malformed trial evidence") from error


def validate_report(result, scenario, held, project):
    require(
        result is not None and result["scenario"] == scenario and result["held"] is held,
        "missing or mismatched trial report",
    )
    require(
        re.fullmatch(PROJECT_PATTERN, result["project"])
        and (project is None or result["project"] == project),
        "wrong trial project",
    )
    validate_snapshot(result["snapshot"], held=held)
    require(
        set(result["snapshot"])
        == ({"opened", "old_visible", "fresh_visible", "released"} if held else {"opened"}),
        "unexpected read-view evidence for trial condition",
    )
    accepted = ROWS - 3 * (ROWS // 100)
    required = {
        "retry": {"retry_staging": ROWS, "retry_prepared": accepted, "final_staging": ROWS},
        "final": {"final_staging": ROWS},
        "failure_staging": {"failure_staging": ROWS, "failure_prepared": 0},
        "failure_prepared": {
            "final_staging": ROWS,
            "failure_staging": 0,
            "failure_prepared": accepted,
        },
    }[scenario]
    require(
        type(result["source_rows"]) is int
        and result["source_rows"] == ROWS
        and set(result["drains"]) == set(required),
        "wrong pilot row count or lifecycle phase",
    )
    fixture = result["fixture_counts"]
    require(
        fixture == {"staging": ROWS, "prepared": 0 if scenario == "failure_staging" else accepted}
        and all(type(value) is int for value in fixture.values()),
        "wrong trial fixture counts",
    )
    checkpoints = ["before"]
    for phase, expected in required.items():
        if scenario == "retry" and phase == "final_staging":
            checkpoints.extend(("before_release", "after_release"))
        drain = result["drains"][phase]
        rows = drain["batches"]
        require(
            type(drain["expected"]) is int and drain["expected"] == expected,
            "wrong cleanup total for trial phase",
        )
        validate_drain(rows, expected)
        remaining = expected
        for row in rows:
            require(row["deleted"] == min(1000, remaining), "cleanup batch size did not reconcile")
            remaining -= row["deleted"]
            require(
                all(
                    valid_time(row.get(field)) for field in ("select_server_ms", "delete_server_ms")
                )
                and (row["deleted"] != 0 or row["delete_server_ms"] == 0),
                "invalid server batch timing",
            )
            if row["ordinal"] % 5 == 1 or not row["deleted"]:
                checkpoints.append(f"{phase}:{row['ordinal']}")
    if scenario != "retry":
        checkpoints.extend(("before_release", "after_release"))
    check_history(result["history"], checkpoints)
    plan_identity(result["plans"])
    terminal = result["terminal"]
    require(
        all(
            valid_time(terminal.get(k))
            for k in (
                "stage_probe_ms",
                "prepared_probe_ms",
                "pointer_ms",
                "pointer_hold_ms",
                "transaction_ms",
                "commit_ms",
                "stage_probe_server_ms",
                "prepared_probe_server_ms",
            )
        )
        and all(
            type(terminal.get(k)) is int and terminal[k] >= 0
            for k in (
                "stage_rows_returned",
                "prepared_rows_returned",
                "stage_rows_examined",
                "prepared_rows_examined",
            )
        )
        and terminal["stage_rows_returned"] == 0
        and terminal["prepared_rows_returned"] == int(not scenario.startswith("failure_"))
        and terminal.get("read_view_held") is (held and scenario != "retry")
        and valid_time(result.get("observer_overhead_ms"))
        and valid_time(result.get("elapsed_seconds"))
        and result["invariants"] is True,
        "invalid terminal measurements or data-protection invariants",
    )


def check_history(history, expected):
    observed = []
    for row in history:
        checkpoint = row["checkpoint"]
        require(
            all(
                type(row.get(key)) is int and row[key] >= 0
                for key in ("history", "purge_trx", "purge_undo")
            ),
            "invalid InnoDB history measurement",
        )
        if checkpoint == "after_release" and observed and observed[-1] == checkpoint:
            continue
        observed.append(checkpoint)
    require(observed == expected, "missing or out-of-order InnoDB history checkpoints")


def plan_identity(plans):
    tables = {
        "staging": ("etl_staging_rows", "ix_etl_staging_version_key"),
        "prepared": ("company_version_rows", "PRIMARY"),
        "terminal_staging": ("etl_staging_rows", "ix_etl_staging_version_key"),
    }
    require(set(plans) == set(tables), "missing or unexpected execution-plan keys")
    identity = {}
    for name, (table, index) in tables.items():
        observed = plans[name]["query_block"]["table"]
        access, key = observed["access_type"], observed.get("key")
        require(
            observed["table_name"] == table
            and (
                (key == index and access in {"ref", "range", "index", "const"})
                or (name != "staging" and key is None and access == "ALL")
            ),
            "unexpected execution-plan table, key or access type",
        )
        identity[name] = (table, access, key)
    return identity


def selection_windows(batches):
    full = [batch["select_ms"] for batch in batches if batch["deleted"] == 1000]
    if not full:
        return {}
    width = max(1, len(full) // 10)
    center = (len(full) - width) // 2
    return {
        "early": median(full[:width]),
        "middle": median(full[center : center + width]),
        "late": median(full[-width:]),
    }


def summarize_pair(control, held):
    require(
        control["fixture_counts"] == held["fixture_counts"]
        and control["scenario"] == held["scenario"]
        and control["held"] is False
        and held["held"] is True
        and plan_identity(control["plans"]) == plan_identity(held["plans"]),
        "trial fixtures, conditions or plans differ within pair",
    )
    retry = control["scenario"] == "retry"
    before_release = [
        next(row for row in trial["history"] if row["checkpoint"] == "before_release")
        for trial in (control, held)
    ]
    control_end, held_end = before_release
    control_begin = control["history"][0]
    held_after = next(
        row for row in reversed(held["history"]) if row["checkpoint"] == "after_release"
    )
    distinguishable = (
        held_end["history"] > control_end["history"]
        and control_end["purge_trx"] > control_begin["purge_trx"]
        and held_after["history"] < held_end["history"]
        and held_after["purge_trx"] > held_end["purge_trx"]
    )
    elapsed = {}
    for phase, control_drain in control["drains"].items():
        if retry and phase == "final_staging":
            # Retry releases its reader before it restages the file.
            continue
        c = selection_windows(control_drain["batches"])
        h = selection_windows(held["drains"][phase]["batches"])
        if c and h:
            elapsed[phase] = {
                "control_late_median_ms": c["late"],
                "excess_late_minus_early_ms": h["late"] - h["early"] - (c["late"] - c["early"]),
            }
    c, h = (trial["terminal"]["stage_probe_ms"] for trial in (control, held))
    return {
        "scenario": control["scenario"],
        "fixture_counts": control["fixture_counts"],
        "purge_evidence": "distinguishable" if distinguishable else "inconclusive",
        "drains": elapsed,
        "control_terminal_ms": c,
        "held_terminal_ms": h,
        "terminal_treatment": "outside_held_view" if retry else "matched",
        "terminal_excess_ms": None if retry else h - c,
        "cursor_recommendation": False,
    }


def campaign(workspace, vhd, evidence, started):
    reports = []
    for index, scenario in enumerate(SCENARIOS):
        for held in (False, True) if index % 2 == 0 else (True, False):
            require(
                monotonic() - started < CAMPAIGN_SECONDS - TRIAL_SECONDS - CLEANUP_RESERVE,
                "insufficient campaign time for a trial and its cleanup",
            )
            trial = DisposableTrial(workspace, vhd, evidence, started)
            failure = None
            print(
                f"Starting {trial.project} {scenario} {'held' if held else 'control'}", flush=True
            )
            with guarded_commands(trial):
                try:
                    trial.start_watchdog()
                    # A failed isolation proof must latch before there is any teardown.
                    try:
                        trial.verification(
                            verify.prove_disposable_config, trial.compose, trial.project
                        )
                    except BaseException:
                        trial.block_cleanup()
                        raise
                    trial.start()
                    trial.run_owned(
                        [
                            "python",
                            "-B",
                            "-m",
                            "tests.benchmark_etl_purge",
                            scenario,
                            "held" if held else "control",
                        ],
                        events=True,
                    )
                    require(
                        trial.view_opened is held and trial.view_closed is held,
                        "read-view handshake was not observed by watchdog",
                    )
                    check_report(trial.result, scenario, held, project=trial.project)
                    trial.guard()
                except BaseException as error:
                    failure = error
                try:
                    trial.stop_and_remove()
                except BaseException as error:
                    if failure is None:
                        failure = error
                    else:
                        failure.add_note(f"Cleanup also failed for {trial.project}: {error}")
                finally:
                    trial.stop_watchdog()
            if trial.shutdown_monitor_error is not None:
                error = f"monitor failed during shutdown: {trial.shutdown_monitor_error}"
                if failure is None:
                    failure = PilotAbort(error)
                else:
                    failure.add_note(error)
            output_path = workspace / f"{trial.project}.result.json"
            output_path.write_text(
                json.dumps(
                    {
                        "project": trial.project,
                        "scenario": scenario,
                        "held": held,
                        "result": trial.result,
                        "samples": trial.monitor.samples,
                        "peak_observed_bytes": trial.monitor.storage_peak,
                        "failure": str(failure) if failure is not None else None,
                        "valid": failure is None,
                        "cleanup_blocked": trial.marker.exists(),
                        "mysql_exit": trial.mysql_exit,
                        "shutdown": trial.shutdown_evidence,
                        "elapsed_seconds": monotonic() - trial.started,
                    },
                    indent=2,
                )
                + "\n"
            )
            print(f"Evidence: {output_path}", flush=True)
            if failure is not None:
                raise failure
            reports.append(trial.result)
    require(len(reports) == 8, "incomplete A1 campaign")
    pairs = []
    for index in range(0, len(reports), 2):
        control, held = sorted(reports[index : index + 2], key=lambda item: item["held"])
        pairs.append(summarize_pair(control, held))
    check_deadlines(now=monotonic(), campaign_since=started)
    (workspace / "summary.json").write_text(json.dumps(pairs, indent=2, allow_nan=False) + "\n")


@contextmanager
def guarded_commands(trial):
    token = COMMAND_GUARD.set(trial.guard)
    try:
        yield
    finally:
        COMMAND_GUARD.reset(token)


def main():
    started = monotonic()
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--preflight", action="store_true")
    mode.add_argument("--pilot", action="store_true")
    args = parser.parse_args()
    require(__debug__, "Python assertions must be enabled")
    vhd, evidence = bounded_preflight()
    print(json.dumps(evidence, sort_keys=True), flush=True)
    # Render the exact Compose overrides and run the repository's dry ownership check.
    if args.preflight:
        with tempfile.TemporaryDirectory(prefix="companywatch-purge-preflight-") as directory:
            trial = DisposableTrial(Path(directory), vhd, evidence, monotonic())
            trial.verification(verify.prove_disposable_config, trial.compose, trial.project)
            config = json.loads(trial.compose("config", "--format", "json", capture=True).stdout)
            require(
                config["services"]["tests"].get("init") is True
                and not config["services"]["db"].get("init"),
                "invalid Compose runner init configuration",
            )
            for service, ram in (("db", MYSQL_RAM), ("tests", RUNNER_RAM)):
                item = config["services"][service]
                require(
                    int(item["mem_limit"]) == ram
                    and int(item["memswap_limit"]) == ram
                    and (service != "db" or float(item["cpus"]) == 2),
                    "invalid Compose limits",
                )
            print("Compose runner init and declared limits verified without creating resources.")
        return
    lock_path = Path(f"/tmp/companywatch-purge-a1-{os.getuid()}.lock")
    descriptor = os.open(lock_path, os.O_CREAT | os.O_NOFOLLOW | os.O_RDWR, 0o600)
    with os.fdopen(descriptor, "w") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        require(
            not list(
                Path("/tmp").glob("companywatch-purge-a1-*/companywatch-check-*.cleanup-blocked")
            ),
            "a prior pilot retained resources after failed cleanup",
        )
        active = docker("ps", "--format", '{{.Label "com.docker.compose.project"}}').splitlines()
        require(
            not any(item.startswith("companywatch-check-") for item in active),
            "another isolated verification project is already running",
        )
        workspace = Path(tempfile.mkdtemp(prefix="companywatch-purge-a1-"))
        print(f"Pilot evidence directory: {workspace}", flush=True)
        campaign(workspace, vhd, evidence, started)


if __name__ == "__main__":
    try:
        main()
    except (
        PilotAbort,
        verify.IsolationError,
        OSError,
        ValueError,
        subprocess.SubprocessError,
    ) as error:
        print(f"A1 stopped: {error}", file=sys.stderr)
        for note in getattr(error, "__notes__", []):
            print(note, file=sys.stderr)
        sys.exit(1)
