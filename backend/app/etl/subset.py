"""Calibrate one shared ONRC cutoff using only transient identity hashes."""

import hashlib
from collections import Counter
from heapq import nsmallest

from app.etl.errors import ETLError
from app.etl.parser import classify, project, records
from app.etl.source import SOURCES

SUBSET_PROFILE = "onrc-pj-subset-v1"
CALIBRATION_TARGET = 120_000
SUBSET_MINIMUM = 110_000
HASH_RULE = "SHA-256(exact UTF-8 EUID), unsigned big-endian, strictly below threshold"
STATS = (
    "source_records",
    "legal_entity_candidates",
    "valid_legal_entity_records",
    "eligible_singletons",
    "duplicate_key_groups",
    "duplicate_key_records",
)


def euid_hash(euid):
    return hashlib.sha256(euid.encode("utf-8")).digest()


def selected(euid, threshold):
    return bool(euid.strip()) and int.from_bytes(euid_hash(euid), "big") < threshold


def scan_edition(path, *, target):
    counts = Counter()
    identities = {}
    for _, row in records(path):
        counts["source_records"] += 1
        valid = False
        if classify(row) == "legal_entity":
            counts["legal_entity_candidates"] += 1
            _, errors = project(row)
            valid = not errors
            counts["valid_legal_entity_records"] += valid
        euid = row["EUID"]
        if euid.strip():
            key = euid_hash(euid)
            previous = identities.get(key, 0)
            # A singleton is 1 if eligible, -1 otherwise. Duplicates track group size.
            identities[key] = abs(previous) + 1 if previous else 1 if valid else -1

    def singleton_hashes():
        for key, count in identities.items():
            if count == 1:
                counts["eligible_singletons"] += 1
                yield key
            elif count > 1:
                counts["duplicate_key_groups"] += 1
                counts["duplicate_key_records"] += count

    lowest = nsmallest(target, singleton_hashes())
    if len(lowest) < target:
        raise ETLError("calibration_insufficient_euids")
    return {**{key: counts[key] for key in STATS}, "rank_hash": lowest[-1].hex()}


def build_calibration(scans):
    threshold = max(int(scan["rank_hash"], 16) for scan in scans.values()) + 1
    return {
        "rule": HASH_RULE,
        "target": CALIBRATION_TARGET,
        "threshold": f"{threshold:064x}",
        "editions": {
            edition: {key: scan[key] for key in (*STATS, "resource_id", "sha256")}
            for edition, scan in scans.items()
        },
    }


def validate_calibration(calibration):
    try:
        if (
            set(calibration) != {"rule", "target", "threshold", "editions"}
            or calibration["rule"] != HASH_RULE
            or calibration["target"] != CALIBRATION_TARGET
            or set(calibration["editions"]) != set(SOURCES)
        ):
            raise ValueError
        threshold = int(calibration["threshold"], 16)
        if not 0 < threshold <= 1 << 256 or calibration["threshold"] != f"{threshold:064x}":
            raise ValueError
        for edition, source in SOURCES.items():
            evidence = calibration["editions"][edition]
            if (
                set(evidence) != {*STATS, "resource_id", "sha256"}
                or evidence["resource_id"] != source.resource_id
                or evidence["sha256"] != bytes.fromhex(evidence["sha256"]).hex()
                or len(evidence["sha256"]) != 64
                or any(type(evidence[key]) is not int or evidence[key] < 0 for key in STATS)
                or not (
                    CALIBRATION_TARGET
                    <= evidence["eligible_singletons"]
                    <= evidence["valid_legal_entity_records"]
                    <= evidence["legal_entity_candidates"]
                    <= evidence["source_records"]
                )
                or not (
                    2 * evidence["duplicate_key_groups"]
                    <= evidence["duplicate_key_records"]
                    <= evidence["source_records"] - evidence["eligible_singletons"]
                )
            ):
                raise ValueError
    except (KeyError, TypeError, ValueError):
        raise ETLError("calibration_invalid") from None
    return threshold
