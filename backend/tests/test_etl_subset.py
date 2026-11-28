import pytest

from app.etl import subset
from app.etl.errors import ETLError
from tests.etl_fixtures import csv_file, row


def test_hash_uses_exact_utf8_bytes_and_strict_cutoff():
    digest = bytes.fromhex("ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad")
    cutoff = int.from_bytes(digest, "big")
    assert subset.euid_hash("abc") == digest
    assert not subset.selected("abc", cutoff)
    assert subset.selected("abc", cutoff + 1)
    assert subset.euid_hash(" abc") != digest


def test_calibration_counts_only_valid_source_wide_singletons(tmp_path):
    items = [
        row(1),
        row(1, FORMA_JURIDICA="PFA", COD_INMATRICULARE="F01/1/2020"),
        row(2),
        row(2, FORMA_JURIDICA="UNKNOWN"),
        row(3),
        row(4),
        row(5, DATA_INMATRICULARE="invalid"),
        row(6, EUID=""),
    ]
    expected_cutoff = max(subset.euid_hash(row(number)["EUID"]) for number in (3, 4))
    expected = {
        "source_records": 8,
        "legal_entity_candidates": 6,
        "valid_legal_entity_records": 4,
        "eligible_singletons": 2,
        "duplicate_key_groups": 2,
        "duplicate_key_records": 4,
        "rank_hash": expected_cutoff.hex(),
    }
    for name, order in (("forward", items), ("reverse", reversed(items))):
        path = csv_file(tmp_path / name, order)
        assert subset.scan_edition(path, target=2) == expected
        with pytest.raises(ETLError, match="^calibration_insufficient_euids$"):
            subset.scan_edition(path, target=3)


def test_one_shared_threshold_and_checked_metadata(monkeypatch, tmp_path):
    monkeypatch.setattr(subset, "CALIBRATION_TARGET", 2)
    editions = {}
    for (edition, source), numbers in zip(
        subset.SOURCES.items(), ((1, 2, 3), (2, 3, 4)), strict=True
    ):
        path = csv_file(tmp_path / edition, [row(number) for number in numbers])
        editions[edition] = {
            **subset.scan_edition(path, target=2),
            "resource_id": source.resource_id,
            "sha256": "a" * 64,
        }
    calibration = subset.build_calibration(editions)
    threshold = int(calibration["threshold"], 16)
    assert threshold == max(int(edition["rank_hash"], 16) for edition in editions.values()) + 1
    for numbers in ((1, 2, 3), (2, 3, 4)):
        assert sum(subset.selected(row(number)["EUID"], threshold) for number in numbers) >= 2
    assert subset.validate_calibration(calibration) == threshold
    with pytest.raises(ETLError, match="^calibration_invalid$"):
        subset.validate_calibration({**calibration, "threshold": hex(threshold + 1)})
