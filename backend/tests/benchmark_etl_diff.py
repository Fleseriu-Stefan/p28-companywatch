"""Opt-in timing of the complete detail stream on isolated, published real editions."""

import argparse
import json
import os
import re
import sys
from collections import Counter
from time import monotonic
from uuid import UUID

from sqlalchemy import create_engine, event, select, text
from sqlalchemy.exc import SQLAlchemyError

from app.config import Settings
from app.etl.errors import ETLError
from app.etl.models import versions
from app.etl.service import Pipeline

READ_TIMEOUT = 120
CATEGORIES = ("added", "removed", "modified", "unchanged")


def inputs(connection, old_id, new_id):
    snapshots = connection.execute(
        select(versions.c.id, versions.c.edition, versions.c.report).where(
            versions.c.id.in_((old_id, new_id)),
            versions.c.state == "published",
            versions.c.source_kind == "real",
        )
    ).all()
    if len(snapshots) != 2 or len({row.edition for row in snapshots}) != 2:
        raise ETLError("benchmark_requires_two_distinct_published_real_editions")
    by_id = {row.id: row for row in snapshots}
    editions = []
    for version_id in (old_id, new_id):
        row = by_id[version_id]
        report = row.report or {}
        accepted = report.get("accepted_records")
        source = report.get("source_records")
        if not (
            isinstance(accepted, int) and isinstance(source, int) and source >= accepted >= 100000
        ):
            raise ETLError("benchmark_requires_verified_input_counts")
        editions.append(
            {
                "version_id": version_id,
                "edition": row.edition,
                "accepted_records": accepted,
                "source_records": source,
            }
        )
    return editions


def measure(pipeline, observer, old_id, new_id, totals):
    capture = {}

    def track_statement(connection, cursor, statement, parameters, context, executemany):
        if "UNION ALL" not in statement:
            return
        if capture:
            raise ETLError("benchmark_multiple_detail_statements")
        connection_id = connection.connection.driver_connection.thread_id()
        thread_id = observer.scalar(
            text("SELECT THREAD_ID FROM performance_schema.threads WHERE PROCESSLIST_ID = :id"),
            {"id": connection_id},
        )
        if thread_id is None:
            raise ETLError("benchmark_performance_schema_thread_missing")
        event_floor = observer.scalar(
            text(
                "SELECT COALESCE(MAX(EVENT_ID), 0) "
                "FROM performance_schema.events_statements_history "
                "WHERE THREAD_ID = :thread_id"
            ),
            {"thread_id": thread_id},
        )
        capture.update(
            statement=statement,
            parameters=parameters,
            thread_id=thread_id,
            event_floor=event_floor,
            started=monotonic(),
        )

    categories, fields = Counter(), Counter()
    event.listen(pipeline.engine, "before_cursor_execute", track_statement)
    try:
        with pipeline.diff_details(old_id, new_id) as details:
            for row in details:
                categories[row["change_type"]] += 1
                fields.update(row["changed_fields"])
            finished = monotonic()
            if not capture:
                raise ETLError("benchmark_detail_statement_missing")
            sample = observer.execute(
                text(
                    "SELECT EVENT_ID, TIMER_WAIT, ROWS_SENT, ERRORS "
                    "FROM performance_schema.events_statements_history "
                    "WHERE THREAD_ID = :thread_id AND EVENT_ID > :event_floor "
                    "AND EVENT_NAME = 'statement/sql/select' AND END_EVENT_ID IS NOT NULL"
                ),
                {"thread_id": capture["thread_id"], "event_floor": capture["event_floor"]},
            ).all()
    finally:
        event.remove(pipeline.engine, "before_cursor_execute", track_statement)
    if len(sample) != 1:
        raise ETLError("benchmark_statement_event_missing_or_ambiguous")
    server = sample[0]
    if not server.TIMER_WAIT or server.ERRORS or server.ROWS_SENT != sum(categories.values()):
        raise ETLError("benchmark_statement_event_invalid")
    if (
        set(categories).difference(CATEGORIES)
        or any(categories[name] != totals[name] for name in CATEGORIES)
        or any(fields[name] != count for name, count in totals["by_field"].items())
        or set(fields).difference(totals["by_field"])
    ):
        raise ETLError("benchmark_detail_totals_mismatch")
    return {
        "sql_seconds": server.TIMER_WAIT / 10**12,
        "python_seconds": finished - capture["started"],
        "rows": server.ROWS_SENT,
        "thread_id": capture["thread_id"],
        "event_id": server.EVENT_ID,
    }, (capture["statement"], capture["parameters"])


def run(engine, old_id, new_id):
    pipeline = Pipeline(engine)
    with engine.connect() as observer:
        editions = inputs(observer, old_id, new_id)
        totals = pipeline.diff(old_id, new_id)
        common = totals["unchanged"] + totals["modified"]
        if (
            editions[0]["accepted_records"] != common + totals["removed"]
            or editions[1]["accepted_records"] != common + totals["added"]
        ):
            raise ETLError("benchmark_input_totals_mismatch")
        print(
            json.dumps(
                {
                    "mysql_version": observer.scalar(text("SELECT VERSION()")),
                    "read_timeout_seconds": READ_TIMEOUT,
                    "editions": editions,
                    "shared_euids": common,
                    "union_size": common + totals["added"] + totals["removed"],
                    "totals": totals,
                }
            ),
            flush=True,
        )

        all_under_target = True
        for run_number in range(4):
            sample, (statement, parameters) = measure(pipeline, observer, old_id, new_id, totals)
            under_target = sample["sql_seconds"] < 30
            if run_number:
                all_under_target &= under_target
            sample.update(run=run_number, warm_up=run_number == 0, sql_under_target=under_target)
            print(json.dumps(sample), flush=True)

        plan = observer.exec_driver_sql(f"EXPLAIN ANALYZE {statement}", parameters).scalar_one()
        print(json.dumps({"sql_target_met": all_under_target, "explain_analyze": plan}))


def version_uuid(value):
    try:
        return str(UUID(value))
    except ValueError:
        raise argparse.ArgumentTypeError("expected a UUID") from None


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("old_version", type=version_uuid)
    parser.add_argument("new_version", type=version_uuid)
    args = parser.parse_args()
    engine = None
    try:
        settings = Settings.from_env()
        if not (
            re.fullmatch(r"companywatch-bench-[a-f0-9]{16}", os.getenv("ETL_TEST_PROJECT", ""))
            and settings.database.endswith("_test")
            and settings.host == "db"
            and settings.port == 3306
        ):
            raise ETLError("benchmark_requires_isolated_compose_project")
        engine = create_engine(
            settings.url,
            pool_pre_ping=True,
            hide_parameters=True,
            connect_args={"connect_timeout": 2, "read_timeout": READ_TIMEOUT, "write_timeout": 2},
        )
        run(engine, args.old_version, args.new_version)
    except ETLError as error:
        print(str(error), file=sys.stderr)
        return 2
    except (SQLAlchemyError, ValueError):
        print("benchmark_database_or_configuration_error", file=sys.stderr)
        return 2
    finally:
        if engine is not None:
            engine.dispose()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
