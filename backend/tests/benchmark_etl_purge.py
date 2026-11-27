"""Synthetic worker for the guarded 25,001-row Gate 2 A1 launcher."""

import argparse
import json
import os
import re
import signal
from contextlib import contextmanager
from importlib.metadata import version as installed_version
from pathlib import Path
from statistics import median
from tempfile import TemporaryDirectory
from time import monotonic, sleep
from types import SimpleNamespace
from unittest.mock import patch

from sqlalchemy import event, func, insert, select, text

from app.config import Settings
from app.db import create_database_engine
from app.etl import service
from app.etl.errors import ETLError
from app.etl.models import attempts, companies, publications, staging, versions
from tests.etl_fixtures import csv_file, row, source

ROWS = 25001
SCENARIOS = ("retry", "final", "failure_staging", "failure_prepared")
PID_FILE = Path("/tmp/purge-a1.pid")


class InvalidTrial(RuntimeError):
    """Abort instrumentation without converting it into a synthetic ingest failure."""


def require(condition, code):
    if not condition:
        raise InvalidTrial(code)


def emit(kind, **fields):
    print(json.dumps({"kind": kind, **fields}, allow_nan=False), flush=True)


def shutdown(_signum, _frame):
    # BaseException bypasses the production ingest failure handler on a watchdog abort.
    raise SystemExit("purge_a1_aborted")


def safe_target():
    settings = Settings.from_env()
    project = os.environ.get("ETL_TEST_PROJECT", "")
    require(
        __debug__
        and re.fullmatch(r"companywatch-check-[0-9a-f]{16}", project)
        and settings.database == "companywatch_test"
        and settings.host == "db"
        and settings.port == 3306
        and settings.user == "companywatch_test",
        "purge_a1_wrong_target",
    )
    for entry in Path("/app/requirements.lock").read_text().splitlines():
        package, expected = entry.split("==", 1)
        require(installed_version(package) == expected, "purge_a1_dependency_mismatch")
    return settings


def count(connection, table, version_id):
    return connection.scalar(
        select(func.count()).select_from(table).where(table.c.version_id == version_id)
    )


def snapshot(connection, version_id):
    return tuple(
        connection.execute(
            select(table).where(column == version_id).order_by(*table.primary_key.columns)
        ).all()
        for table, column in (
            (versions, versions.c.id),
            (staging, staging.c.version_id),
            (companies, companies.c.version_id),
        )
    )


def history(connection):
    status = connection.exec_driver_sql("SHOW ENGINE INNODB STATUS").one()[2]
    length = re.search(r"History list length (\d+)", status)
    progress = re.search(r"Purge done for trx's n:o < (\d+) undo n:o < (\d+)", status)
    require(length and progress, "purge_a1_missing_history_metrics")
    return {
        "history": int(length[1]),
        "purge_trx": int(progress[1]),
        "purge_undo": int(progress[2]),
    }


def fixture_rows():
    for number in range(1, ROWS + 1):
        if number % 100 == 0:
            yield row(number, EUID="")
        elif number % 100 == 1 and number > 1:
            yield row(number - 2)
        else:
            yield row(number)


class ReadView:
    def __init__(self, engine, observer, held):
        self.engine = engine
        self.observer = observer
        self.held = held
        self.session = None
        self.started = None
        self.keys = []
        self.record = {"opened": False}
        self.history = []
        self.overhead_ms = 0.0

    def open(self, version_id, tables):
        self.history.append({"checkpoint": "before", **history(self.observer)})
        if not self.held:
            return
        self.session = self.engine.connect().execution_options(isolation_level="REPEATABLE READ")
        self.started = monotonic()
        signal.setitimer(signal.ITIMER_REAL, 300)
        self.session.exec_driver_sql("START TRANSACTION READ ONLY, WITH CONSISTENT SNAPSHOT")
        for table, key in tables:
            picked = self.session.scalar(
                select(key).where(table.c.version_id == version_id).limit(1)
            )
            require(picked is not None, "purge_a1_reader_missing_target")
            self.keys.append((table, key, picked, version_id))
        self.record["opened"] = True
        emit("view_open")

    def sample(self, checkpoint):
        started = monotonic()
        require(self.started is None or started - self.started < 300, "purge_a1_view_deadline")
        self.history.append({"checkpoint": checkpoint, **history(self.observer)})
        self.overhead_ms += (monotonic() - started) * 1000

    def verify_and_release(self):
        self.sample("before_release")
        if self.held:
            old_visible = fresh_visible = False
            try:
                old_visible = True
                for table, key, picked, version_id in self.keys:
                    query = select(key).where(table.c.version_id == version_id, key == picked)
                    old_visible &= self.session.scalar(query) == picked
                    fresh_visible |= self.observer.scalar(query) is not None
                self.record.update(old_visible=old_visible, fresh_visible=fresh_visible)
            finally:
                self.release()
            require(old_visible and not fresh_visible, "purge_a1_snapshot_not_demonstrated")
        initial = self.history[0]["history"]
        end = monotonic() + 15
        while True:
            stats = history(self.observer)
            self.history.append({"checkpoint": "after_release", **stats})
            if stats["history"] <= initial or monotonic() >= end:
                break
            sleep(0.5)

    def release(self, *, graceful=True):
        if self.session is not None:
            try:
                if graceful:
                    self.session.rollback()
                else:
                    self.session.invalidate()
            finally:
                signal.setitimer(signal.ITIMER_REAL, 0)
                self.session.close()
                self.session = None
                self.started = None
                if self.record["opened"]:
                    self.record["released"] = True
                    emit("view_release")


HISTORY_SQL = text("""
SELECT EVENT_ID, SQL_TEXT, TIMER_WAIT, ROWS_EXAMINED, ROWS_AFFECTED
FROM performance_schema.events_statements_history WHERE THREAD_ID=:thread
ORDER BY EVENT_ID
""")


def statement_role(statement):
    if statement.startswith("SELECT"):
        if "IS_USED_LOCK" in statement:
            return "lock"
        if "FROM dataset_publications" in statement:
            return "pointer"
    table = next(
        (
            name
            for name, physical in (
                ("staging", "etl_staging_rows"),
                ("prepared", "company_version_rows"),
            )
            if f"FROM {physical}" in statement
        ),
        None,
    )
    if table and statement.startswith("DELETE"):
        return f"delete_{table}"
    if table and statement.startswith("SELECT") and "LIMIT" in statement:
        return f"select_{table}"
    return None


class Trace:
    def __init__(self, engine, observer, reader):
        self.engine = engine
        self.observer = observer
        self.reader = reader
        self.actual_commit = engine.dialect.do_commit
        self.connection = self.phase = self.begin = self.thread = self.current = None
        self.floor = 0
        self.timers = {}
        self.drains = {}
        self.terminal = {}
        self.terminal_view_held = None
        self.overhead_ms = 0.0

    def history(self):
        return self.observer.execute(HISTORY_SQL, {"thread": self.thread}).all()

    @contextmanager
    def capture(self, connection, phase):
        started = monotonic()
        self.connection, self.phase = connection, phase
        self.thread = self.observer.scalar(
            text("SELECT THREAD_ID FROM performance_schema.threads WHERE PROCESSLIST_ID=:id"),
            {"id": connection.connection.driver_connection.thread_id()},
        )
        require(self.thread is not None, "purge_a1_writer_thread_missing")
        events = self.history()
        self.floor = events[-1].EVENT_ID if events else 0
        self.overhead_ms += (monotonic() - started) * 1000
        try:
            yield
        finally:
            self.connection = self.phase = self.begin = self.current = None
            self.timers = {}

    def before(self, connection, _cursor, statement, _params, _context, _many):
        if connection is not self.connection:
            return
        role = statement_role(statement)
        if role is None:
            return
        now = monotonic()
        if role == "lock":
            self.begin = now
            require(
                self.reader.started is None or now - self.reader.started < 300,
                "purge_a1_view_deadline",
            )
        if self.phase == "terminal" and role == "select_staging":
            self.terminal_view_held = self.reader.session is not None
        self.current = (role, now)

    def after(self, connection, cursor, _statement, _params, _context, _many):
        if connection is not self.connection or self.current is None:
            return
        role, started = self.current
        finished = monotonic()
        self.timers[role] = ((finished - started) * 1000, cursor.rowcount, finished)
        self.current = None

    def commit(self, dbapi):
        started = monotonic()
        self.actual_commit(dbapi)
        ack = monotonic()
        if self.connection is None or dbapi is not self.connection.connection:
            return
        now = monotonic()
        events = [e for e in self.history() if e.EVENT_ID > self.floor]
        if events:
            self.floor = events[-1].EVENT_ID
        observed = {statement_role(e.SQL_TEXT or ""): e for e in events}
        require("pointer" in self.timers and self.begin is not None, "purge_a1_missing_timing")
        row_stats = {
            "pointer_ms": self.timers["pointer"][0],
            "pointer_hold_ms": (ack - self.timers["pointer"][2]) * 1000,
            "commit_ms": (ack - started) * 1000,
            "transaction_ms": (ack - self.begin) * 1000,
        }
        selections = [
            (role, values) for role, values in self.timers.items() if role.startswith("select_")
        ]
        if self.phase == "terminal":
            require(
                {role for role, _ in selections} == {"select_staging", "select_prepared"},
                "purge_a1_terminal_probes_missing",
            )
            for role, values in selections:
                require(role in observed, "purge_a1_terminal_metrics_missing")
                event_row = observed[role]
                label = "stage" if role == "select_staging" else "prepared"
                row_stats[f"{label}_probe_ms"] = values[0]
                row_stats[f"{label}_probe_server_ms"] = event_row.TIMER_WAIT / 1e9
                row_stats[f"{label}_rows_examined"] = event_row.ROWS_EXAMINED
                row_stats[f"{label}_rows_returned"] = values[1]
            row_stats["read_view_held"] = self.terminal_view_held
            self.terminal = row_stats
        else:
            require(len(selections) == 1, "purge_a1_batch_select_unobserved")
            role, (elapsed, selected, _) = selections[0]
            table = role.removeprefix("select_")
            delete_role = f"delete_{table}"
            delete_ms, deleted, _ = self.timers.get(delete_role, (0, 0, 0))
            require(
                role in observed
                and (
                    not deleted
                    or (delete_role in observed and observed[delete_role].ROWS_AFFECTED == deleted)
                ),
                "purge_a1_statement_metrics_missing",
            )
            event_row = observed[role]
            batches = self.drains.setdefault(f"{self.phase}_{table}", [])
            records = {
                "ordinal": len(batches) + 1,
                "select_ms": elapsed,
                "delete_ms": delete_ms,
                "selected": selected,
                "deleted": deleted,
                "rows_examined": event_row.ROWS_EXAMINED,
                "select_server_ms": event_row.TIMER_WAIT / 1e9,
                "delete_server_ms": observed[delete_role].TIMER_WAIT / 1e9 if deleted else 0,
            }
            if len(batches) % 5 == 0 or not deleted:
                records["handler"] = dict(
                    self.observer.execute(
                        text("""
                    SELECT VARIABLE_NAME, VARIABLE_VALUE
                    FROM performance_schema.status_by_thread
                    WHERE THREAD_ID=:thread AND VARIABLE_NAME LIKE 'Handler_read%'
                    """),
                        {"thread": self.thread},
                    ).all()
                )
                self.reader.sample(f"{self.phase}_{table}:{len(batches) + 1}")
            batches.append({**row_stats, **records})
        self.overhead_ms += (monotonic() - now) * 1000
        self.timers = {}


def summarize(batches):
    full = [batch for batch in batches if batch["deleted"] == 1000]
    if not full:
        return {}
    width = max(1, len(full) // 10)
    center = (len(full) - width) // 2
    windows = {
        "early": full[:width],
        "middle": full[center : center + width],
        "late": full[-width:],
    }
    results = {}
    for label, rows in windows.items():
        times = {}
        for field in ("select_ms", "delete_ms", "commit_ms", "pointer_hold_ms", "transaction_ms"):
            values = sorted(row[field] for row in rows)
            # Nearest-rank p95. Small pilot windows are descriptive.
            times[field] = {
                "median": median(values),
                "p95": values[(95 * len(values) + 99) // 100 - 1],
                "max": values[-1],
            }
        results[label] = times
    return results


def query_plans(observer, version_id):
    tests = {
        "staging": """SELECT id FROM etl_staging_rows FORCE INDEX (ix_etl_staging_version_key)
                      WHERE version_id=:version LIMIT 1000""",
        "prepared": "SELECT euid FROM company_version_rows WHERE version_id=:version LIMIT 1000",
        "terminal_staging": """SELECT version_id FROM etl_staging_rows
                               WHERE version_id=:version LIMIT 1 LOCK IN SHARE MODE""",
    }
    return {
        key: json.loads(
            observer.scalar(text(f"EXPLAIN FORMAT=JSON {sql}"), {"version": version_id})
        )
        for key, sql in tests.items()
    }


def run(engine, directory, scenario, held):
    pipeline = service.Pipeline(engine, minimum_rows=1, allow_synthetic=True)
    artifact = csv_file(directory / "target.csv", fixture_rows())
    target_source = source()
    other_source = source("2026-11-04")
    sentinel = pipeline.ingest(csv_file(directory / "published.csv", [row(70001)]), other_source)
    approval = pipeline.approve(sentinel, pipeline.report(sentinel)["report_hash"])
    pipeline.publish(sentinel, approval)
    actual_cleanup = service.clear_retry_rows
    actual_outcome = service.record_ingest_outcome

    def abandoned(*_args, **_kwargs):
        raise ETLError("purge_a1_seed_interrupted")

    with patch.object(service, "clear_retry_rows", abandoned):
        try:
            pipeline.ingest(csv_file(directory / "unrelated.csv", [row(70002)]), other_source)
        except ETLError as error:
            require(str(error) == "purge_a1_seed_interrupted", "purge_a1_bad_unrelated_seed")
        else:
            require(False, "purge_a1_missing_seed_interrupt")

    def loading_version(connection, filename):
        return connection.execute(
            select(versions.c.id).where(
                versions.c.sha256 == service.file_hash(directory / filename)
            )
        ).scalar_one()

    with engine.connect().execution_options(isolation_level="AUTOCOMMIT") as observer:
        unrelated = loading_version(observer, "unrelated.csv")
        actual_stage = pipeline._stage
        counter = 0

        def stage_interleaved(connection, lock_name, batch):
            nonlocal counter
            actual_stage(connection, lock_name, batch)
            counter += 1
            with engine.begin() as fixture:
                fixture.execute(
                    insert(staging).values(
                        version_id=unrelated,
                        source_line=counter + 10,
                        valid=False,
                        excluded=False,
                        key_digest=None,
                        errors=[],
                    )
                )

        if scenario == "retry":
            with (
                patch.object(service, "clear_retry_rows", abandoned),
                patch.object(pipeline, "_stage", stage_interleaved),
            ):
                try:
                    pipeline.ingest(artifact, target_source)
                except ETLError as error:
                    require(str(error) == "purge_a1_seed_interrupted", "purge_a1_bad_retry_seed")
                else:
                    require(False, "purge_a1_missing_seed_interrupt")

        baseline = {key: snapshot(observer, key) for key in (sentinel, unrelated)}
        before_pointer = observer.scalar(select(publications.c.current_version_id))
        reader = ReadView(engine, observer, held)
        trace = Trace(engine, observer, reader)
        expected = {}
        plans = {}
        target_id = None
        fixture_counts = {}
        failure_code = f"purge_a1_{scenario}"
        begin = monotonic()

        def cleanup(connection, lock_name, version_id, *, attempt_id=None, phase="retry"):
            nonlocal target_id
            target_id = version_id
            population = [(staging, staging.c.id)]
            if phase != "final":
                population.append((companies, companies.c.euid))
            scoped = {
                "staging": count(observer, staging, version_id),
                "prepared": count(observer, companies, version_id),
            }
            if not fixture_counts:
                fixture_counts.update(scoped)
            for table, _ in population:
                label = "staging" if table is staging else "prepared"
                expected[f"{phase}_{label}"] = scoped[label]
            if not plans:
                plans.update(query_plans(observer, version_id))
            if not reader.history and (scenario != "retry" or phase == "retry"):
                if scenario == "failure_prepared":
                    targets = [(staging, staging.c.id), (companies, companies.c.euid)]
                else:
                    targets = population
                if phase == "failure" and scenario == "failure_staging":
                    targets = [(staging, staging.c.id)]
                reader.open(version_id, targets)
            with trace.capture(connection, phase):
                actual_cleanup(
                    connection, lock_name, version_id, attempt_id=attempt_id, phase=phase
                )
            if scenario == "retry" and phase == "retry":
                reader.verify_and_release()

        def outcome(connection, *args, **kwargs):
            with trace.capture(connection, "terminal"):
                actual_outcome(connection, *args, **kwargs)

        def fail_hash(*_args, **_kwargs):
            raise ETLError(failure_code)

        def fail_aggregate(_conn, _cursor, sql, *_):
            if scenario == "failure_staging" and "GROUP BY etl_staging_rows.legal_form" in sql:
                raise ETLError(failure_code)

        event.listen(engine, "before_cursor_execute", trace.before)
        event.listen(engine, "after_cursor_execute", trace.after)
        event.listen(engine, "before_cursor_execute", fail_aggregate)
        failed = scenario.startswith("failure_")
        try:
            with (
                patch.object(service, "clear_retry_rows", cleanup),
                patch.object(service, "record_ingest_outcome", outcome),
                patch.object(engine.dialect, "do_commit", trace.commit),
                patch.object(
                    pipeline,
                    "_prepared_hash",
                    fail_hash if scenario == "failure_prepared" else pipeline._prepared_hash,
                ),
            ):
                try:
                    target = pipeline.ingest(artifact, target_source)
                    require(not failed and target == target_id, "purge_a1_missing_expected_failure")
                except ETLError as error:
                    require(
                        failed and str(error) == failure_code,
                        f"purge_a1_unexpected_ingest_outcome:{error}",
                    )
            if scenario != "retry":
                reader.verify_and_release()
        finally:
            reader.release(graceful=False)
            event.remove(engine, "before_cursor_execute", fail_aggregate)
            event.remove(engine, "after_cursor_execute", trace.after)
            event.remove(engine, "before_cursor_execute", trace.before)

        elapsed = monotonic() - begin
        require(target_id is not None, "purge_a1_missing_target")
        state = observer.execute(select(versions).where(versions.c.id == target_id)).one()
        seen_attempts = sorted(
            observer.scalars(select(attempts.c.state).where(attempts.c.version_id == target_id))
        )
        report = state.report
        accepted = ROWS - 3 * (ROWS // 100)
        expected_company_count = 0 if failed else accepted
        require(
            fixture_counts
            == {
                "staging": ROWS,
                "prepared": 0 if scenario == "failure_staging" else accepted,
            },
            "purge_a1_fixture_count_mismatch",
        )
        require(
            state.state == ("failed" if failed else "review")
            and report["source_records"] == ROWS
            and service.digest_json(report) == state.report_hash
            and state.approval is None
            and seen_attempts
            == (
                ["failed"]
                if failed
                else (["abandoned", "ready"] if scenario == "retry" else ["ready"])
            )
            and count(observer, staging, target_id) == 0
            and count(observer, companies, target_id) == expected_company_count,
            "purge_a1_terminal_invariants",
        )
        if failed:
            require(
                report
                == {
                    "full_file_validated": False,
                    "failure_code": failure_code,
                    "source_records": ROWS,
                    "source_kind": "synthetic",
                }
                and state.prepared_hash is None,
                "purge_a1_failed_report_invariants",
            )
        else:
            require(
                report["full_file_validated"]
                and report["accepted_records"] == expected_company_count
                and report["quarantined_records"] == ROWS - expected_company_count
                and pipeline._prepared_hash(observer, target_id) == state.prepared_hash,
                "purge_a1_success_report_invariants",
            )
        require(
            before_pointer == sentinel == observer.scalar(select(publications.c.current_version_id))
            and all(snapshot(observer, key) == value for key, value in baseline.items()),
            "purge_a1_unrelated_data_changed",
        )
        require(set(trace.drains) == set(expected), "purge_a1_cleanup_phases_mismatch")
        return {
            "project": os.environ["ETL_TEST_PROJECT"],
            "scenario": scenario,
            "held": held,
            "source_rows": ROWS,
            "invariants": True,
            "fixture_counts": fixture_counts,
            "snapshot": reader.record,
            "history": reader.history,
            "plans": plans,
            "terminal": trace.terminal,
            "elapsed_seconds": elapsed,
            "observer_overhead_ms": trace.overhead_ms + reader.overhead_ms,
            "drains": {
                key: {"batches": batches, "expected": expected[key], "windows": summarize(batches)}
                for key, batches in trace.drains.items()
            },
        }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("scenario", choices=SCENARIOS)
    parser.add_argument("condition", choices=("control", "held"))
    args = parser.parse_args()
    settings = safe_target()
    signal.signal(signal.SIGTERM, shutdown)
    signal.signal(signal.SIGALRM, shutdown)
    with PID_FILE.open("x", encoding="ascii") as handle:
        handle.write(f"{os.getpid()}\n")
    engine = create_database_engine(settings, read_timeout=120)
    try:
        with TemporaryDirectory(prefix="purge-a1-") as directory:
            with patch.object(service, "secrets", SimpleNamespace(token_bytes=lambda n: b"S" * n)):
                result = run(engine, Path(directory), args.scenario, args.condition == "held")
        emit("report", result=result)
    finally:
        engine.dispose()
        PID_FILE.unlink()


if __name__ == "__main__":
    try:
        main()
    except (ETLError, InvalidTrial) as error:
        emit("failure", code=str(error))
        raise SystemExit(1) from None
