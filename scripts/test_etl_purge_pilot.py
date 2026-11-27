"""Offline tests for the Gate 2 A1 pilot's run and measurement guards."""

import io
import json
import math
import re
import subprocess
import sys
import tarfile
import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

from scripts import etl_purge_pilot as pilot

PROJECT = "companywatch-check-1234567890abcdef"
CID = "a" * 64
GIB = 1024**3


def sample(**changes):
    return pilot.StorageSample(
        **{
            "docker_free": 16 * GIB,
            "windows_free": 16 * GIB,
            "volume": 200,
            "layers": 300,
            "logs": 20,
            "artifacts": 30,
            "backing_growth": 400,
            "mysql_memory": 0,
            "runner_memory": 0,
            **changes,
        }
    )


def batch(ordinal, deleted=1000, **changes):
    return {
        "ordinal": ordinal,
        "selected": deleted,
        "deleted": deleted,
        "rows_examined": deleted,
        "select_ms": 2.0,
        "delete_ms": 2.0,
        "commit_ms": 1.0,
        "pointer_ms": 0.1,
        "pointer_hold_ms": 4.9,
        "transaction_ms": 5.1,
        **changes,
    }


class MonitorTests(unittest.TestCase):
    def setUp(self):
        self.monitor = pilot.BudgetMonitor()

    def test_accepts_storage_and_records_peak_conservatively(self):
        self.monitor.observe(sample(), 1)
        self.assertEqual(self.monitor.storage_peak, 550)
        self.monitor.observe(sample(backing_growth=600), 5)
        self.assertEqual(self.monitor.storage_peak, 630)

    def test_storage_threshold_counts_all_disposable_components(self):
        self.monitor.observe(sample(), 0)
        with self.assertRaisesRegex(pilot.PilotAbort, "storage threshold"):
            self.monitor.observe(sample(volume=2 * GIB - 350), 4)

    def test_aborts_when_either_backing_filesystem_drops_below_floor(self):
        for field in ("docker_free", "windows_free"):
            with self.subTest(field=field), self.assertRaisesRegex(pilot.PilotAbort, field):
                pilot.BudgetMonitor().observe(sample(**{field: 4 * GIB - 1}), 1)

    def test_aborts_on_missing_invalid_or_stale_measurement(self):
        for invalid in (None, sample(volume=-1), sample(logs=math.nan)):
            with self.subTest(invalid=invalid), self.assertRaisesRegex(pilot.PilotAbort, "monitor"):
                pilot.BudgetMonitor().observe(invalid, 1)
        self.monitor.observe(sample(), 1)
        with self.assertRaisesRegex(pilot.PilotAbort, "monitor"):
            self.monitor.observe(sample(), 12)

    def test_sustained_memory_pressure_and_reset(self):
        high = sample(mysql_memory=2 * GIB * 9 // 10)
        for t, reading in [(0, high), (5, high), (9, sample()), (10, high), (15, high)]:
            self.monitor.observe(reading, t)
        with self.assertRaisesRegex(pilot.PilotAbort, "memory pressure"):
            self.monitor.observe(high, 20)

    def test_trial_view_and_campaign_deadlines(self):
        for kwargs, error in [
            ({"held_since": 0, "now": 300}, "read view"),
            ({"trial_since": 0, "now": 600}, "trial"),
            ({"campaign_since": 0, "now": 10800}, "campaign"),
        ]:
            with self.subTest(error=error), self.assertRaisesRegex(pilot.PilotAbort, error):
                pilot.check_deadlines(**kwargs)


class MeasurementsTests(unittest.TestCase):
    def test_missing_or_wrong_read_view_handshake_aborts(self):
        with self.assertRaisesRegex(pilot.PilotAbort, "read-view handshake"):
            pilot.validate_snapshot({"opened": False}, held=True)
        with self.assertRaisesRegex(pilot.PilotAbort, "read-view handshake"):
            pilot.validate_snapshot(
                {"opened": True, "old_visible": False, "fresh_visible": False, "released": True},
                held=True,
            )

    def test_confirmed_snapshot_is_valid_even_if_purge_catchup_is_inconclusive(self):
        pilot.validate_snapshot(
            {"opened": True, "old_visible": True, "fresh_visible": False, "released": True},
            held=True,
        )
        pilot.validate_snapshot({"opened": False}, held=False)

    def test_reconciliation_checks_totals_ordinals_and_cap(self):
        rows = [batch(1), batch(2), batch(3, 1), batch(4, 0)]
        pilot.validate_drain(rows, 2001)
        for bad, total in [
            (rows, 2000),
            ([batch(1, 1001), batch(2, 0)], 1001),
            ([batch(1), batch(3, 0)], 1000),
            ([batch(1, 1000, selected=999), batch(2, 0)], 1000),
            ([batch(1)], 1000),
        ]:
            with self.subTest(bad=bad), self.assertRaisesRegex(pilot.PilotAbort, "reconcil"):
                pilot.validate_drain(bad, total)

    def test_invalid_measurements_are_rejected(self):
        for changes in ({"select_ms": math.inf}, {"commit_ms": -1}, {"rows_examined": None}):
            with (
                self.subTest(changes=changes),
                self.assertRaisesRegex(pilot.PilotAbort, "measurement"),
            ):
                pilot.validate_drain([batch(1, **changes), batch(2, 0)], 1000)

    def test_materiality_requires_three_pairs_and_both_thresholds(self):
        pair = {"control_early": 5.0, "control_late": 20.0, "held_early": 5.0, "held_late": 24.0}
        self.assertFalse(pilot.material_batch_penalty([pair]))
        self.assertTrue(pilot.material_batch_penalty([pair] * 3))
        weak = {**pair, "held_late": 23.9}
        self.assertFalse(pilot.material_batch_penalty([pair, pair, weak]))
        self.assertFalse(pilot.material_probe_penalty([(5.0, 6.5)] * 3))
        self.assertTrue(pilot.material_probe_penalty([(5.0, 7.0)] * 3))


class OwnershipTests(unittest.TestCase):
    def record(self, **changes):
        return {
            "id": CID,
            "name": f"/{PROJECT}-db-1",
            "project": PROJECT,
            "service": "db",
            "oneoff": "False",
            "mounts": [("volume", f"{PROJECT}_mysql_data", "/var/lib/mysql", True)],
            "networks": [f"{PROJECT}_default"],
            **changes,
        }

    def test_owned_mysql_is_accepted_and_protected_volume_or_foreign_endpoint_is_rejected(self):
        pilot.validate_ownership(PROJECT, [self.record()], {CID}, ())
        for record, endpoints in [
            (self.record(project="companywatch"), {CID}),
            (
                self.record(mounts=[("volume", "companywatch_mysql_data", "/var/lib/mysql", True)]),
                {CID},
            ),
            (self.record(), {CID, "b" * 64}),
        ]:
            with self.subTest(record=record), self.assertRaisesRegex(pilot.PilotAbort, "ownership"):
                pilot.validate_ownership(PROJECT, [record], endpoints, ())

    def test_failed_teardown_persists_and_prevents_later_attempts(self):
        with tempfile.TemporaryDirectory() as directory:
            marker = Path(directory) / "cleanup-blocked"
            prove = Mock()
            stop = Mock(side_effect=pilot.PilotAbort("shutdown failed"))
            remove = Mock()
            with self.assertRaisesRegex(pilot.PilotAbort, "shutdown"):
                pilot.cleanup_owned(marker, prove, stop, remove)
            self.assertTrue(marker.is_file())
            remove.assert_not_called()
            retry = Mock()
            with self.assertRaisesRegex(pilot.PilotAbort, "blocked"):
                pilot.cleanup_owned(marker, prove, retry, remove)
            retry.assert_not_called()

    def test_failed_ownership_prevents_shutdown_and_removal(self):
        with tempfile.TemporaryDirectory() as directory:
            marker = Path(directory) / "cleanup-blocked"
            prove = Mock(side_effect=pilot.PilotAbort("ownership failed"))
            stop, remove = Mock(), Mock()
            with self.assertRaisesRegex(pilot.PilotAbort, "ownership"):
                pilot.cleanup_owned(marker, prove, stop, remove)
            stop.assert_not_called()
            remove.assert_not_called()
            self.assertTrue(marker.is_file())


class AbortFlowTests(unittest.TestCase):
    def test_runner_archive_contains_only_approved_sources(self):
        with tarfile.open(fileobj=io.BytesIO(pilot.runner_archive()), mode="r:") as archive:
            names = set(archive.getnames())
        self.assertIn("tests/benchmark_etl_purge.py", names)
        self.assertIn("app/etl/service.py", names)
        self.assertIn("migrations/versions/0002_etl.py", names)
        self.assertFalse(any(".env" in name or name.startswith("/") for name in names))

    def test_resource_abort_tears_down_once_and_does_not_start_next_trial(self):
        created = Mock(project=PROJECT)
        created.start.side_effect = pilot.PilotAbort("resource monitor unavailable")
        created.monitor.samples = []
        created.monitor.storage_peak = 0
        created.result = None
        created.shutdown_monitor_error = None
        created.mysql_exit = None
        created.shutdown_evidence = {}
        created.started = 1
        with tempfile.TemporaryDirectory() as directory:
            workspace = Path(directory)
            created.marker = workspace / "cleanup-blocked"
            with (
                unittest.mock.patch.object(
                    pilot, "DisposableTrial", return_value=created
                ) as launch,
                unittest.mock.patch.object(pilot.verify, "prove_disposable_config"),
                self.assertRaisesRegex(pilot.PilotAbort, "monitor unavailable"),
            ):
                pilot.campaign(workspace, None, {}, pilot.monotonic())
            launch.assert_called_once()
            created.stop_and_remove.assert_called_once()
            self.assertIn("monitor unavailable", (workspace / f"{PROJECT}.result.json").read_text())


def valid_report(scenario="final", held=False):
    accepted = 24251
    totals = {
        "final": {"final_staging": 25001},
        "retry": {"retry_staging": 25001, "retry_prepared": accepted, "final_staging": 25001},
    }[scenario]
    drains = {}
    for name, total in totals.items():
        full, remainder = divmod(total, 1000)
        sizes = [1000] * full + ([remainder] if remainder else []) + [0]
        drains[name] = {
            "expected": total,
            "batches": [
                batch(i, size, select_server_ms=1.0, delete_server_ms=float(bool(size)))
                for i, size in enumerate(sizes, 1)
            ],
            "windows": {},
        }
    terminal = dict.fromkeys(
        (
            "pointer_ms",
            "pointer_hold_ms",
            "transaction_ms",
            "commit_ms",
            "stage_probe_ms",
            "prepared_probe_ms",
            "stage_probe_server_ms",
            "prepared_probe_server_ms",
            "stage_rows_examined",
            "stage_rows_returned",
            "prepared_rows_examined",
        ),
        0,
    )
    terminal.update(prepared_rows_returned=1, read_view_held=held and scenario != "retry")
    history = [{"checkpoint": "before", "history": 0, "purge_trx": 0, "purge_undo": 0}]
    for name, drain in drains.items():
        if name == "final_staging" and scenario == "retry":
            history.extend(
                {**history[0], "checkpoint": phase} for phase in ("before_release", "after_release")
            )
        history.extend(
            {**history[0], "checkpoint": f"{name}:{row['ordinal']}"}
            for row in drain["batches"]
            if row["ordinal"] % 5 == 1 or not row["deleted"]
        )
    if scenario != "retry":
        history.extend(
            {**history[0], "checkpoint": phase} for phase in ("before_release", "after_release")
        )
    snapshot = {"opened": held}
    if held:
        snapshot.update(old_visible=True, fresh_visible=False, released=True)
    return {
        "project": PROJECT,
        "scenario": scenario,
        "held": held,
        "source_rows": 25001,
        "invariants": True,
        "fixture_counts": {"staging": 25001, "prepared": accepted},
        "snapshot": snapshot,
        "history": history,
        "plans": {
            name: {
                "query_block": {"table": {"table_name": table, "key": key, "access_type": "ref"}}
            }
            for name, table, key in (
                ("staging", "etl_staging_rows", "ix_etl_staging_version_key"),
                ("prepared", "company_version_rows", "PRIMARY"),
                ("terminal_staging", "etl_staging_rows", "ix_etl_staging_version_key"),
            )
        },
        "terminal": terminal,
        "elapsed_seconds": 1.0,
        "observer_overhead_ms": 20.0,
        "drains": drains,
    }


class AuditReportTests(unittest.TestCase):
    def test_valid_trial_is_accepted_and_bound_to_its_project(self):
        for scenario in ("retry", "final"):
            for held in (False, True):
                report = valid_report(scenario, held)
                pilot.check_report(report, scenario, held, project=PROJECT)
                with self.assertRaisesRegex(pilot.PilotAbort, "trial project"):
                    pilot.check_report(
                        report, scenario, held, project="companywatch-check-" + "b" * 16
                    )

    def test_malformed_trial_evidence_is_rejected(self):
        corruptions = {
            "server timing": lambda r: r["drains"]["final_staging"]["batches"][0].update(
                select_server_ms=math.nan
            ),
            "fixture count": lambda r: r["fixture_counts"].update(staging=1),
            "history checkpoint": lambda r: r["history"].pop(-2),
            "missing plan": lambda r: r["plans"].pop("prepared"),
            "wrong index": lambda r: r["plans"]["staging"]["query_block"]["table"].update(
                key="PRIMARY"
            ),
            "trial identity": lambda r: r.update(project="companywatch"),
            "terminal treatment": lambda r: r["terminal"].update(read_view_held=True),
            "terminal row count": lambda r: r["terminal"].update(prepared_rows_returned=2),
        }
        for name, mutate in corruptions.items():
            with self.subTest(name=name):
                report = valid_report()
                mutate(report)
                with self.assertRaises(pilot.PilotAbort):
                    pilot.check_report(report, "final", False)

    def test_retry_probe_is_excluded_and_other_probes_remain_comparable(self):
        for scenario in ("retry", "final"):
            with self.subTest(scenario=scenario):
                control, held = valid_report(scenario), valid_report(scenario, held=True)
                held["terminal"]["stage_probe_ms"] = 4.0
                paired = pilot.summarize_pair(control, held)
                self.assertEqual(paired["terminal_excess_ms"], None if scenario == "retry" else 4.0)
                self.assertEqual(paired["purge_evidence"], "inconclusive")
                self.assertFalse(paired["cursor_recommendation"])


class AuditLifecycleTests(unittest.TestCase):
    def make_trial(self, workspace):
        vhd = workspace / "docker.vhdx"
        vhd.touch()
        evidence = {
            "mysql_image": "mysql-id",
            "runner_image": "runner-id",
            "docker_free": 16 * GIB,
            "windows_free": 16 * GIB,
            "vhd_size": 0,
        }
        with (
            patch.object(pilot, "daemon_storage", return_value=(16 * GIB, 0, 0)),
            patch.object(pilot.shutil, "disk_usage", return_value=Mock(free=16 * GIB)),
        ):
            return pilot.DisposableTrial(workspace, vhd, evidence, pilot.monotonic())

    def test_resource_breach_aborts_while_startup_command_is_still_running(self):
        self.assert_startup_aborts("storage threshold")

    def test_stalled_sample_aborts_while_startup_command_is_still_running(self):
        self.assert_startup_aborts("sampling gap")

    def assert_startup_aborts(self, reason):
        with tempfile.TemporaryDirectory() as directory:
            workspace = Path(directory)
            trial = self.make_trial(workspace)
            completed = workspace / "startup-completed"
            started = workspace / "startup-started"
            trial.compose_base = [
                sys.executable,
                "-c",
                "import pathlib, sys, time; pathlib.Path(sys.argv[1]).touch(); "
                "time.sleep(.8); pathlib.Path(sys.argv[2]).touch()",
                str(started),
                str(completed),
            ]
            trial.scope = Mock(side_effect=pilot.PilotAbort("startup ran past watchdog"))
            trial.stop_and_remove = Mock()
            release = threading.Event()

            def storage(*_args, **_kwargs):
                if started.exists():
                    if reason == "sampling gap":
                        release.wait(2)
                    return 16 * GIB, 0, 2 * GIB
                return 16 * GIB, 0, 0

            try:
                with (
                    patch.object(pilot, "DisposableTrial", return_value=trial),
                    patch.object(pilot.verify, "prove_disposable_config"),
                    patch.object(pilot, "SAMPLE_INTERVAL", 0.05),
                    patch.object(pilot, "MAX_SAMPLE_GAP", 0.3),
                    patch.object(pilot, "daemon_storage", side_effect=storage),
                    patch.object(pilot.shutil, "disk_usage", return_value=Mock(free=16 * GIB)),
                    patch.object(pilot, "docker", return_value=""),
                ):
                    with self.assertRaisesRegex(pilot.PilotAbort, reason):
                        pilot.campaign(workspace, trial.vhd, trial.evidence, pilot.monotonic())
                self.assertTrue(started.exists())
                self.assertFalse(completed.exists())
                trial.stop_and_remove.assert_called_once()
            finally:
                release.set()

    def test_stubborn_local_wait_cli_cannot_enter_an_unbounded_context_wait(self):
        with tempfile.TemporaryDirectory() as directory:
            trial = self.make_trial(Path(directory))
            trial.scope = Mock(
                return_value=(
                    [{"id": CID, "state": {"Status": "running"}, "service": "db"}],
                    "network",
                    True,
                )
            )
            process = MagicMock()
            process.__enter__.return_value = process
            process.poll.return_value = None
            process.communicate.side_effect = subprocess.TimeoutExpired("docker wait", 1)
            process.wait.side_effect = subprocess.TimeoutExpired("docker wait", 1)
            ticks = iter(range(0, 5000, 5))
            with (
                patch.object(pilot, "docker", return_value="") as docker,
                patch.object(pilot.subprocess, "Popen", return_value=process),
                patch.object(pilot.os, "killpg"),
                patch.object(pilot, "monotonic", side_effect=lambda: next(ticks)),
                patch.object(trial, "sampling"),
                self.assertRaises((pilot.PilotAbort, subprocess.TimeoutExpired)),
            ):
                trial.stop_and_remove()
            self.assertTrue(trial.marker.is_file())
            docker.assert_called_once_with("container", "kill", "--signal=TERM", CID)
            process.__exit__.assert_not_called()

    def test_mysql_nonzero_exit_latches_without_removal(self):
        with tempfile.TemporaryDirectory() as directory:
            trial = self.make_trial(Path(directory))
            trial.scope = Mock(
                return_value=(
                    [{"id": CID, "state": {"Status": "running"}, "service": "db"}],
                    "network",
                    True,
                )
            )
            with (
                patch.object(pilot, "docker", return_value="") as docker,
                patch.object(
                    pilot, "command", return_value=subprocess.CompletedProcess([], 0, "137\n")
                ),
                self.assertRaisesRegex(pilot.PilotAbort, "did not exit 0"),
            ):
                trial.stop_and_remove()
            self.assertTrue(trial.marker.is_file())
            self.assertIsNone(trial.mysql_exit)
            docker.assert_called_once_with("container", "kill", "--signal=TERM", CID)

    def test_watchdog_remains_active_during_graceful_shutdown(self):
        with tempfile.TemporaryDirectory() as directory:
            workspace = Path(directory)
            trial = self.make_trial(workspace)
            waiting = workspace / "waiting"
            trial.scope = Mock(
                side_effect=[
                    ([{"id": CID, "state": {"Status": "running"}, "service": "db"}], None, False),
                    (
                        [
                            {
                                "id": CID,
                                "state": {"Status": "exited", "ExitCode": 0},
                                "service": "db",
                            }
                        ],
                        None,
                        False,
                    ),
                ]
            )
            real_command = pilot.command

            def command(args, **kwargs):
                self.assertEqual(args, ["docker", "container", "wait", CID])
                return real_command(
                    [
                        sys.executable,
                        "-c",
                        "import pathlib, sys, time; pathlib.Path(sys.argv[1]).touch(); "
                        "time.sleep(.3); print(0)",
                        str(waiting),
                    ],
                    **kwargs,
                )

            def storage(*_args, **_kwargs):
                return 16 * GIB, 0, 2 * GIB if waiting.is_file() else 0

            with (
                patch.object(pilot, "daemon_storage", side_effect=storage),
                patch.object(pilot.shutil, "disk_usage", return_value=Mock(free=16 * GIB)),
                patch.object(pilot, "docker", return_value="") as docker,
                patch.object(pilot, "command", side_effect=command),
                patch.object(pilot, "protected_labels"),
                patch.object(pilot, "SAMPLE_INTERVAL", 0.05),
                pilot.guarded_commands(trial),
            ):
                trial.start_watchdog()
                try:
                    trial.stop_and_remove()
                finally:
                    trial.stop_watchdog()
            self.assertEqual(trial.mysql_exit, 0)
            self.assertIn("storage threshold", trial.shutdown_monitor_error)
            self.assertFalse(trial.marker.exists())
            self.assertLess(
                docker.call_args_list.index(
                    unittest.mock.call("container", "kill", "--signal=TERM", CID)
                ),
                docker.call_args_list.index(unittest.mock.call("container", "rm", CID)),
            )

    def test_archive_installs_regular_files_beneath_verified_root(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            subprocess.run(
                [sys.executable, "-I", "-B", "-c", pilot.ARCHIVE_INSTALL, str(root)],
                input=pilot.runner_archive(),
                capture_output=True,
                timeout=5,
                check=True,
            )
            for path in ("app/etl/service.py", "tests/benchmark_etl_purge.py"):
                self.assertEqual(
                    (root / path).read_bytes(), (pilot.ROOT / "backend" / path).read_bytes()
                )

    def test_redirected_archive_destination_aborts_before_copy(self):
        for component in (".", "app", "app/config.py"):
            with self.subTest(component=component):
                self.assert_redirected_archive_destination(component)

    def assert_redirected_archive_destination(self, component):
        with tempfile.TemporaryDirectory() as directory:
            workspace = Path(directory)
            root = workspace / "destination"
            outside = workspace / "outside"
            outside.mkdir()
            if component == ".":
                root.symlink_to(outside, target_is_directory=True)
            else:
                (root / "app").mkdir(parents=True)
                if component == "app":
                    (root / "app").rmdir()
                    (root / "app").symlink_to(outside, target_is_directory=True)
                else:
                    (root / component).symlink_to(outside / "conf")
            trial = self.make_trial(workspace)
            log = {"Type": "json-file", "Config": {"max-size": "5m", "max-file": "2"}}
            records = [
                {
                    "id": cid,
                    "service": service,
                    "image": trial.evidence[image],
                    "host": {
                        "Init": service == "tests",
                        "Memory": ram,
                        "MemorySwap": ram,
                        "NanoCpus": 2_000_000_000,
                        "LogConfig": log,
                    },
                }
                for cid, service, image, ram in (
                    (CID, "tests", "runner_image", GIB),
                    ("b" * 64, "db", "mysql_image", 2 * GIB),
                )
            ]
            trial.compose = Mock()
            trial.scope = Mock(return_value=(records, "network", True))
            copied = []
            real_run = subprocess.run

            def host_run(args, **kwargs):
                copied.append(args)
                raise pilot.PilotAbort("unverified archive copy was attempted")

            def runner(args, **kwargs):
                if "input_data" not in kwargs:
                    self.fail("runner reached workload before archive proof")
                command = [sys.executable, *args[1:-1], str(root)]
                result = real_run(
                    command, input=kwargs["input_data"], capture_output=True, timeout=3
                )
                if result.returncode:
                    raise pilot.PilotAbort("unsafe archive destination")
                copied.append(args)

            def docker(*args, **_kwargs):
                if args[-1] == "/sys/fs/cgroup/cpu.max":
                    return "200000 100000"
                return f"{GIB if CID in args else 2 * GIB}\n0"

            with (
                patch.object(trial, "sampling"),
                patch.object(trial, "run_owned", side_effect=runner),
                patch.object(pilot, "docker", side_effect=docker),
                patch.object(pilot.subprocess, "run", side_effect=host_run),
                self.assertRaisesRegex(pilot.PilotAbort, "unsafe archive destination"),
            ):
                trial.start()
            self.assertFalse(copied)
            self.assertFalse(list(outside.iterdir()))


class InspectCompatibilityTests(unittest.TestCase):
    def setUp(self):
        workspace = Path(self.enterContext(tempfile.TemporaryDirectory()))
        vhd = workspace / "docker.vhdx"
        vhd.touch()
        self.trial = pilot.DisposableTrial(
            workspace,
            vhd,
            {"docker_free": 16 * GIB, "windows_free": 16 * GIB, "vhd_size": 0},
            pilot.monotonic(),
        )
        self.trial.resources_requested = True
        self.volume_path = f"/var/lib/docker/volumes/{self.trial.volume}/_data"
        self.fields = {
            ".Id": CID,
            ".Name": f"/{self.trial.project}-db-1",
            ".Config.Labels": {
                "com.docker.compose.project": self.trial.project,
                "com.docker.compose.service": "db",
                "com.docker.compose.oneoff": "False",
            },
            ".Mounts": [
                {
                    "Type": "volume",
                    "Name": self.trial.volume,
                    "Source": self.volume_path,
                    "Destination": "/var/lib/mysql",
                    "RW": True,
                }
            ],
            ".NetworkSettings.Networks": {self.trial.network: {}},
            ".State": {"Status": "created"},
            ".HostConfig": {},
            ".LogPath": "",
            ".Image": "sha256:" + "b" * 64,
        }
        self.sized_response = {".SizeRw": 512}
        self.owner = f"{self.trial.project} mysql_data"
        self.trial.compose = Mock(return_value=subprocess.CompletedProcess([], 0, CID))
        self.docker = self.enterContext(patch.object(pilot, "docker", side_effect=self.response))
        self.storage = self.enterContext(
            patch.object(pilot, "daemon_storage", return_value=(16 * GIB, 0, 0))
        )
        self.enterContext(
            patch.object(pilot.shutil, "disk_usage", return_value=Mock(free=16 * GIB))
        )

    def response(self, *args, timeout=5):
        network_id = "c" * 64
        label = f"label=com.docker.compose.project={self.trial.project}"
        if args == ("ps", "-aq", "--no-trunc", "--filter", label):
            return CID
        if args in (("volume", "ls", "-q"), ("volume", "ls", "-q", "--filter", label)):
            return self.trial.volume
        if args == ("network", "ls", "--no-trunc", "--format", "{{.ID}} {{.Name}}"):
            return f"{network_id} {self.trial.network}"
        if args == ("network", "ls", "--no-trunc", "-q", "--filter", label):
            return network_id
        if args[:2] == ("network", "inspect"):
            self.assertEqual(args[-1], network_id)
            return (
                json.dumps(
                    {
                        "com.docker.compose.project": self.trial.project,
                        "com.docker.compose.network": "default",
                    }
                )
                + "\n{}"
            )
        if args[:2] == ("volume", "inspect"):
            self.assertEqual(args[-1], self.trial.volume)
            return f"{self.volume_path} {self.owner}" if ".Mountpoint" in args[-2] else self.owner
        if args[:2] == ("inspect", "--format"):
            self.assertEqual(args[-1], CID)
            return f"{self.trial.project} volume {self.trial.volume}"
        self.assertEqual(args[:2], ("container", "inspect"))
        self.assertEqual(args[-1], CID)
        self.assertGreater(timeout, 0)
        fields = dict(self.fields)
        if "--size" in args:
            fields.update(self.sized_response)
        requested = re.findall(r"\{\{json (\.[\w.]+)\}\}", args[-2])
        try:
            return " ".join(json.dumps(fields[name]) for name in requested)
        except KeyError as missing:
            raise pilot.PilotAbort(f"Docker template map has no entry for key {missing}") from None

    def test_ownership_scope_accepts_ordinary_inspect_without_size_rw(self):
        records, network, volume = self.trial.scope()
        self.assertEqual([record["id"] for record in records], [CID])
        self.assertEqual(network, "c" * 64)
        self.assertTrue(volume)
        self.assertFalse(self.trial.marker.exists())
        inspect_args = next(
            c.args for c in self.docker.call_args_list if c.args[:2] == ("container", "inspect")
        )
        self.assertNotIn("--size", inspect_args)
        self.assertNotIn(".SizeRw", inspect_args[-2])

    def test_sampling_requests_size_and_counts_writable_layer_bytes(self):
        self.trial.sampling()
        inspect_args = next(
            c.args for c in self.docker.call_args_list if c.args[:2] == ("container", "inspect")
        )
        self.assertEqual(inspect_args[2:4], ("--size", "--format"))
        self.assertIn(".SizeRw", inspect_args[-2])
        self.assertEqual(self.trial.monitor.samples[0]["layers"], 512)

    def test_invalid_size_rw_aborts_without_recording_a_sample(self):
        for response in ({}, *({".SizeRw": n} for n in (None, -1, "512", True, 1.5))):
            with self.subTest(response=response):
                self.sized_response = response
                with self.assertRaises(pilot.PilotAbort):
                    self.trial.sampling()
                self.assertEqual(self.trial.monitor.samples, [])
        self.storage.assert_not_called()

    def test_wrong_volume_owner_latches_cleanup_without_mutations(self):
        self.owner = "foreign-project mysql_data"
        with self.assertRaisesRegex(pilot.verify.IsolationError, "volume ownership"):
            self.trial.stop_and_remove()
        self.assertTrue(self.trial.marker.is_file())
        self.docker.reset_mock()
        with self.assertRaisesRegex(pilot.PilotAbort, "cleanup blocked"):
            self.trial.stop_and_remove()
        self.docker.assert_not_called()


class RunnerLifecycleTests(unittest.TestCase):
    RUNNER = "b" * 64

    def setUp(self):
        self.workspace = Path(self.enterContext(tempfile.TemporaryDirectory()))
        vhd = self.workspace / "docker.vhdx"
        vhd.touch()
        self.trial = pilot.DisposableTrial(
            self.workspace,
            vhd,
            {
                "docker_free": 16 * GIB,
                "windows_free": 16 * GIB,
                "vhd_size": 0,
                "mysql_image": "mysql-image",
                "runner_image": "runner-image",
            },
            pilot.monotonic(),
        )
        self.docker = self.enterContext(patch.object(pilot, "docker", return_value=""))
        self.trial.verification = Mock()

    def records(self, status="running"):
        return [
            {"id": cid, "service": service, "state": {"Status": status}}
            for cid, service in ((self.RUNNER, "tests"), (CID, "db"))
        ]

    def expect_only_term_signals(self, *ids):
        self.assertEqual(
            [c.args for c in self.docker.call_args_list if c.args[:2] == ("container", "kill")],
            [("container", "kill", "--signal=TERM", cid) for cid in ids],
        )

    def assert_no_removal(self):
        self.assertFalse(any(c.args[1:2] == ("rm",) for c in self.docker.call_args_list))
        self.assertTrue(self.trial.marker.is_file())

    def test_generated_override_enables_init_only_for_runner(self):
        config = json.loads((self.workspace / f"{self.trial.project}.json").read_text())
        self.assertIs(config["services"]["tests"].get("init"), True)
        self.assertNotIn("init", config["services"]["db"])

    def test_missing_effective_runner_init_blocks_startup(self):
        records = self.records("created")
        for record in records:
            db = record["service"] == "db"
            ram = pilot.MYSQL_RAM if db else pilot.RUNNER_RAM
            record["image"] = "mysql-image" if db else "runner-image"
            record["host"] = {
                "Init": False,
                "Memory": ram,
                "MemorySwap": ram,
                "NanoCpus": 2_000_000_000 if db else 0,
                "LogConfig": {"Type": "json-file", "Config": {"max-size": "5m", "max-file": "2"}},
            }
        self.trial.scope = Mock(return_value=(records, None, False))
        self.trial.compose = Mock()
        self.docker.side_effect = pilot.PilotAbort("unverified container startup attempted")
        with self.assertRaisesRegex(pilot.PilotAbort, "runner init is not enabled"):
            self.trial.start()
        self.docker.assert_not_called()

    def test_runner_timeout_still_stops_verified_idle_mysql_without_removing_any_resource(self):
        self.trial.scope = Mock(return_value=(self.records(), None, False))
        with patch.object(
            pilot,
            "command",
            side_effect=[
                pilot.PilotAbort("runner wait deadline"),
                subprocess.CompletedProcess([], 0, "0"),
            ],
        ) as wait:
            with self.assertRaisesRegex(pilot.PilotAbort, "runner wait deadline"):
                self.trial.stop_and_remove()
        self.assertEqual([c.args[0][-1] for c in wait.call_args_list], [self.RUNNER, CID])
        self.assertEqual(self.trial.mysql_exit, 0)
        self.expect_only_term_signals(self.RUNNER, CID)
        self.assertEqual(self.trial.scope.call_count, 2)
        self.assert_no_removal()

    def test_lost_workload_acknowledgment_blocks_all_shutdown(self):
        self.trial.containers = {"tests": self.RUNNER, "db": CID}
        self.trial.scope = Mock(
            side_effect=[(self.records(), None, False), (self.records("exited"), None, False)]
        )
        with patch.object(
            pilot, "command", side_effect=pilot.PilotAbort("lost exec acknowledgment")
        ):
            with self.assertRaisesRegex(pilot.PilotAbort, "lost exec acknowledgment"):
                self.trial.run_owned(["python", "-B", "-c", "pass"], input_data=b"data")
        with patch.object(pilot, "command", return_value=subprocess.CompletedProcess([], 0, "0")):
            with self.assertRaisesRegex(
                pilot.PilotAbort, "workload termination could not be verified"
            ):
                self.trial.stop_and_remove()
        self.docker.assert_not_called()
        self.assert_no_removal()

    def test_unproved_read_view_release_blocks_all_shutdown(self):
        self.trial.handle_event({"kind": "view_open"})
        self.trial.scope = Mock(
            side_effect=[(self.records(), None, False), (self.records("exited"), None, False)]
        )
        with patch.object(pilot, "command", return_value=subprocess.CompletedProcess([], 0, "0")):
            with self.assertRaisesRegex(
                pilot.PilotAbort, "workload termination could not be verified"
            ):
                self.trial.stop_and_remove()
        self.docker.assert_not_called()
        self.assert_no_removal()

    def test_lost_ownership_after_runner_timeout_prevents_mysql_signal(self):
        self.trial.scope = Mock(
            side_effect=[(self.records(), None, False), pilot.PilotAbort("ownership changed")]
        )
        with patch.object(pilot, "command", side_effect=pilot.PilotAbort("runner wait deadline")):
            with self.assertRaisesRegex(pilot.PilotAbort, "runner wait deadline") as error:
                self.trial.stop_and_remove()
        self.assertIn("ownership changed", " ".join(getattr(error.exception, "__notes__", [])))
        self.expect_only_term_signals(self.RUNNER)
        self.assert_no_removal()

    def test_runner_accepts_clean_exit_or_sigterm_status(self):
        for code in ("0", "143"):
            with self.subTest(code=code):
                self.trial.scope = Mock(
                    side_effect=[
                        (self.records(), None, False),
                        (self.inspected_exits(runner=int(code)), None, False),
                    ]
                )
                self.docker.reset_mock()
                with patch.object(
                    pilot,
                    "command",
                    side_effect=[
                        subprocess.CompletedProcess([], 0, result) for result in (code, "0")
                    ],
                ):
                    self.trial.stop_and_remove()
                self.expect_only_term_signals(self.RUNNER, CID)
                self.assertIn(
                    ("container", "rm", self.RUNNER), [c.args for c in self.docker.call_args_list]
                )
                self.assertFalse(self.trial.marker.exists())

    def test_arbitrary_runner_status_preserves_marker_but_mysql_stops(self):
        rechecked = self.records()
        rechecked[0]["state"]["Status"] = "exited"
        self.trial.scope = Mock(
            side_effect=[(self.records(), None, False), (rechecked, None, False)]
        )
        with patch.object(
            pilot,
            "command",
            side_effect=[subprocess.CompletedProcess([], 0, result) for result in ("137", "0")],
        ):
            with self.assertRaisesRegex(pilot.PilotAbort, "unexpected runner exit status"):
                self.trial.stop_and_remove()
        self.assertEqual(self.trial.mysql_exit, 0)
        self.expect_only_term_signals(self.RUNNER, CID)
        self.assert_no_removal()

    def mock_exit_and_reinspection(self, before, after):
        self.docker.reset_mock()
        self.trial.scope = Mock(side_effect=[(before, "network", True), (after, "network", True)])
        self.trial.verification = Mock()

        def wait(args, **_kwargs):
            self.assertEqual(args[:-1], ["docker", "container", "wait"])
            code = {self.RUNNER: "143", CID: "0"}[args[-1]]
            return subprocess.CompletedProcess(args, 0, code)

        return patch.object(pilot, "command", side_effect=wait)

    def inspected_exits(self, runner=143, mysql=0):
        records = self.records("exited")
        records[0]["state"]["ExitCode"] = runner
        records[1]["state"]["ExitCode"] = mysql
        return records

    def never_started(self):
        return {
            "Status": "created",
            "Pid": 0,
            "Running": False,
            "StartedAt": "0001-01-01T00:00:00Z",
            "FinishedAt": "0001-01-01T00:00:00Z",
            "ExitCode": 0,
        }

    def test_inspect_exit_mysql_mismatch_blocks_all_removal(self):
        with (
            self.mock_exit_and_reinspection(self.records(), self.inspected_exits(mysql=1)),
            self.assertRaisesRegex(pilot.PilotAbort, "inspect exit code"),
        ):
            self.trial.stop_and_remove()
        self.assert_no_removal()

    def test_inspect_exit_runner_mismatch_blocks_all_removal(self):
        with (
            self.mock_exit_and_reinspection(self.records(), self.inspected_exits(runner=0)),
            self.assertRaisesRegex(pilot.PilotAbort, "inspect exit code"),
        ):
            self.trial.stop_and_remove()
        self.assert_no_removal()

    def test_inspect_exit_missing_or_invalid_codes_block_all_removal(self):
        for state in (
            {},
            {"ExitCode": None},
            {"ExitCode": "0"},
            {"ExitCode": False},
            {"ExitCode": -1},
        ):
            with self.subTest(state=state):
                after = self.inspected_exits()
                after[1]["state"] = {"Status": "exited", **state}
                with (
                    self.mock_exit_and_reinspection(self.records(), after),
                    self.assertRaisesRegex(pilot.PilotAbort, "inspect exit code"),
                ):
                    self.trial.stop_and_remove()
                self.assert_no_removal()
                self.trial.marker.unlink()

    def test_inspect_exit_created_after_successful_wait_blocks_all_removal(self):
        after = self.inspected_exits()
        after[1]["state"] = self.never_started()
        with (
            self.mock_exit_and_reinspection(self.records(), after),
            self.assertRaisesRegex(pilot.PilotAbort, "not exited"),
        ):
            self.trial.stop_and_remove()
        self.assert_no_removal()

    def test_inspect_exit_created_with_nonzero_start_timestamp_cannot_be_removed(self):
        created = self.records("created")[1:]
        created[0]["state"] = {**self.never_started(), "StartedAt": "2026-11-27T17:00:00Z"}
        with (
            self.mock_exit_and_reinspection(created, created) as wait,
            self.assertRaisesRegex(pilot.PilotAbort, "never to have started"),
        ):
            self.trial.stop_and_remove()
        wait.assert_not_called()
        self.assert_no_removal()

    def test_inspect_exit_missing_container_blocks_all_removal(self):
        with (
            self.mock_exit_and_reinspection(self.records(), self.inspected_exits()[1:]),
            self.assertRaisesRegex(pilot.PilotAbort, "owned shutdown resources changed"),
        ):
            self.trial.stop_and_remove()
        self.assert_no_removal()

    def test_inspect_exit_matching_states_and_codes_allow_guarded_removal(self):
        with self.mock_exit_and_reinspection(self.records(), self.inspected_exits()):
            self.trial.stop_and_remove()
        self.expect_only_term_signals(self.RUNNER, CID)
        self.assertEqual(
            [call.args for call in self.docker.call_args_list if call.args[1:2] == ("rm",)],
            [
                ("container", "rm", self.RUNNER),
                ("container", "rm", CID),
                ("network", "rm", "network"),
                ("volume", "rm", self.trial.volume),
            ],
        )
        self.assertFalse(self.trial.marker.exists())

    def test_inspect_exit_proven_never_started_container_needs_no_wait(self):
        created = self.records("created")[1:]
        created[0]["state"] = self.never_started()
        with self.mock_exit_and_reinspection(created, created) as wait:
            self.trial.stop_and_remove()
        wait.assert_not_called()
        self.expect_only_term_signals()
        self.assertIn(("container", "rm", CID), [call.args for call in self.docker.call_args_list])
        self.assertFalse(self.trial.marker.exists())


if __name__ == "__main__":
    unittest.main()
