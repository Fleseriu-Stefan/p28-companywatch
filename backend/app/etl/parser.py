import csv
import re
from datetime import datetime

from app.etl.errors import ETLError
from app.etl.source import HEADER, LEGAL_FORMS, RETAINED


def records(path):
    """Read the complete approved dialect without retaining raw or excluded fields."""
    try:
        with path.open("rb") as binary:
            if binary.read(3) != b"\xef\xbb\xbf":
                raise ETLError("encoding_bom_missing")
        with path.open(encoding="utf-8-sig", errors="strict", newline="") as handle:
            reader = csv.reader(handle, delimiter="^", quoting=csv.QUOTE_NONE, strict=True)
            if tuple(next(reader, ())) != HEADER:
                raise ETLError("schema_changed")
            for ordinal, values in enumerate(reader, start=2):
                if len(values) != len(HEADER):
                    raise ETLError("record_width_invalid")
                yield ordinal, dict(zip(HEADER, values, strict=True))
    except UnicodeDecodeError:
        raise ETLError("encoding_invalid") from None
    except csv.Error:
        raise ETLError("csv_invalid") from None


def classify(row):
    registration = row["COD_INMATRICULARE"]
    form = row["FORMA_JURIDICA"]
    if registration.startswith("F") and form in {"PFA", "II", "IF", "PF", "AF"}:
        return "natural_person_excluded"
    if row["TARA_FIRMA_MAMA"].strip() or "SUCURSAL" in row["DENUMIRE"].upper():
        return "branch_quarantined"
    if registration.startswith("J") and form in LEGAL_FORMS:
        return "legal_entity"
    return "classification_unknown"


def parse_registration_date(value):
    for pattern in ("%d/%m/%Y", "%d/%m/%Y %H:%M:%S"):
        try:
            return datetime.strptime(value, pattern).date()
        except ValueError:
            continue
    return None


def project(row):
    result = {target: row[source] or None for source, target in RETAINED.items()}
    errors = []
    registration = result["registration"] or ""
    euid = result["euid"]
    if not euid or not euid.strip():
        errors.append("euid_missing")
        result["euid"] = None
    elif len(euid) > 255 or not euid.isascii() or euid != euid.strip():
        errors.append("euid_invalid")
        result["euid"] = None
    elif euid != "ROONRC." + registration:
        errors.append("euid_registration_mismatch")
    if not re.fullmatch(r"J[0-9]+(?:/[0-9]+/[0-9]{4})?", registration):
        errors.append("registration_invalid")
    for key, maximum in (("registration", 255), ("cui", 64), ("registration_date", 64)):
        if result[key] and len(result[key]) > maximum:
            errors.append(f"{key}_too_long")
            result[key] = None
    if not result["name"] or not result["name"].strip():
        errors.append("name_missing")
    date = result["registration_date"]
    if date and parse_registration_date(date) is None:
        errors.append("registration_date_invalid")
    return result, errors
