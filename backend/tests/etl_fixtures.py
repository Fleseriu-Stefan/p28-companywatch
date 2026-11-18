import csv
from pathlib import Path

from app.etl.source import HEADER, Source


def source(edition="2026-10-19"):
    return Source(edition, "synthetic-package", f"synthetic-{edition}", None, "synthetic")


def row(number=1, **overrides):
    record = dict.fromkeys(HEADER, "")
    record.update(
        DENUMIRE=f"EXEMPLU SINTETIC {number} SRL",
        CUI=str(100000 + number),
        COD_INMATRICULARE=f"J01/{number}/2020",
        DATA_INMATRICULARE="01/02/2020",
        EUID=f"ROONRC.J01/{number}/2020",
        FORMA_JURIDICA="SRL",
        ADR_JUDET="JUDET SINTETIC",
        ADR_LOCALITATE="LOCALITATE SINTETICA",
    )
    record.update(overrides)
    return record


def csv_file(path: Path, items, header=HEADER):
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.writer(
            handle, delimiter="^", quoting=csv.QUOTE_NONE, quotechar=None, escapechar="\\"
        )
        writer.writerow(header)
        for item in items:
            writer.writerow([item.get(key, "") for key in header])
    return path
