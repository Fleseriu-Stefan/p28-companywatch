import json
import sys
from types import SimpleNamespace
from unittest.mock import MagicMock, Mock

import pytest

from tests import benchmark_etl_diff as benchmark

OLD_VERSION = "aaaaaaaa-0000-4000-8000-000000000001"
NEW_VERSION = "bbbbbbbb-0000-4000-8000-000000000002"


@pytest.fixture
def benchmark_engine(monkeypatch):
    monkeypatch.setenv("ETL_TEST_PROJECT", "companywatch-bench-0000000000000001")
    settings = SimpleNamespace(database="companywatch_test", host="db", port=3306, url=None)
    monkeypatch.setattr(benchmark.Settings, "from_env", Mock(return_value=settings))
    engine = MagicMock()
    monkeypatch.setattr(benchmark, "create_engine", Mock(return_value=engine))
    return engine


@pytest.mark.parametrize("uppercase", [False, True], ids=["lowercase", "uppercase"])
def test_benchmark_accepts_version_uuids(benchmark_engine, monkeypatch, capsys, uppercase):
    versions = (OLD_VERSION, NEW_VERSION)
    arguments = tuple(version.upper() for version in versions) if uppercase else versions
    monkeypatch.setattr(sys, "argv", ["benchmark_etl_diff", *arguments])
    observer = benchmark_engine.connect.return_value.__enter__.return_value
    observer.execute.return_value.all.return_value = [
        SimpleNamespace(
            id=version,
            edition=edition,
            report={"accepted_records": 100000, "source_records": 100001},
        )
        for version, edition in zip(versions, ("2026-10-19", "2026-11-04"), strict=True)
    ]
    observer.scalar.return_value = "8.4.13"
    observer.exec_driver_sql.return_value.scalar_one.return_value = "query plan"

    totals = {"added": 0, "removed": 0, "modified": 0, "unchanged": 100000, "by_field": {}}
    pipeline = Mock()
    pipeline.diff.return_value = totals
    monkeypatch.setattr(benchmark, "Pipeline", Mock(return_value=pipeline))
    sample = {
        "sql_seconds": 1.25,
        "python_seconds": 1.5,
        "rows": 100000,
        "thread_id": 1,
        "event_id": 2,
    }
    query = ("SELECT 1", ())
    measure = Mock(side_effect=lambda *args: (sample.copy(), query))
    monkeypatch.setattr(benchmark, "measure", measure)

    assert benchmark.main() == 0

    pipeline.diff.assert_called_once_with(*versions)
    assert measure.call_count == 4
    expected_args = (pipeline, observer, *versions, totals)
    assert all(call.args == expected_args for call in measure.call_args_list)
    observer.exec_driver_sql.assert_called_once_with("EXPLAIN ANALYZE SELECT 1", ())
    output = capsys.readouterr()
    assert output.err == ""
    metadata, *runs, summary = map(json.loads, output.out.splitlines())
    assert [edition["version_id"] for edition in metadata["editions"]] == list(versions)
    assert metadata["totals"] == totals
    assert runs == [
        {**sample, "run": index, "warm_up": index == 0, "sql_under_target": True}
        for index in range(4)
    ]
    assert summary == {"sql_target_met": True, "explain_analyze": "query plan"}
    benchmark_engine.dispose.assert_called_once_with()


@pytest.mark.parametrize(
    ("argument", "versions"),
    [
        ("old_version", ("invalid", NEW_VERSION)),
        ("new_version", (OLD_VERSION, "invalid")),
    ],
)
def test_benchmark_rejects_invalid_uuid_before_engine_creation(
    benchmark_engine, monkeypatch, capsys, argument, versions
):
    monkeypatch.setattr(sys, "argv", ["benchmark_etl_diff", *versions])
    monkeypatch.setattr(benchmark, "run", Mock())

    with pytest.raises(SystemExit) as error:
        benchmark.main()

    assert error.value.code == 2
    output = capsys.readouterr()
    assert f"argument {argument}: expected a UUID" in output.err
    assert "Traceback" not in output.err
    benchmark.create_engine.assert_not_called()
    benchmark_engine.connect.assert_not_called()
