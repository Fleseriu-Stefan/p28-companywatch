import tracemalloc

from app.etl.parser import records
from tests.etl_fixtures import csv_file, row


def test_100001_synthetic_records_are_parsed_with_bounded_memory(tmp_path):
    path = csv_file(tmp_path / "synthetic-volume.csv", (row(i) for i in range(1, 100002)))
    tracemalloc.start()
    try:
        assert sum(1 for _ in records(path)) == 100001
        _, peak = tracemalloc.get_traced_memory()
        assert peak < 16 * 1024 * 1024
    finally:
        tracemalloc.stop()
