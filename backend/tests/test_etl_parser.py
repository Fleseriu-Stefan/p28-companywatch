import pytest

from app.etl.errors import ETLError
from app.etl.parser import classify, project, records
from app.etl.source import HEADER, RETAINED
from tests.etl_fixtures import csv_file, row


def test_literal_quotes_and_minimal_projection(tmp_path):
    item = row(DENUMIRE='"EXEMPLU" SINTETIC SRL', ADR_DEN_STRADA="DO NOT PERSIST")
    parsed = list(records(csv_file(tmp_path / "synthetic.csv", [item])))
    assert parsed[0][1]["DENUMIRE"] == item["DENUMIRE"]
    assert classify(parsed[0][1]) == "legal_entity"
    result, errors = project(parsed[0][1])
    assert not errors
    assert set(result) == set(RETAINED.values())
    assert "DO NOT PERSIST" not in str(result)


@pytest.mark.parametrize(
    "changes",
    [
        {"COD_INMATRICULARE": "F01/1/2020", "FORMA_JURIDICA": "PFA"},
        {"COD_INMATRICULARE": "J01/1/2020", "FORMA_JURIDICA": "PFA"},
        {"FORMA_JURIDICA": "UNKNOWN"},
        {"FORMA_JURIDICA": "CA"},
        {"DENUMIRE": "SUCURSALA SINTETICA SRL"},
        {"TARA_FIRMA_MAMA": "SYNTHETIC COUNTRY"},
    ],
)
def test_only_verified_legal_entities_are_retained(changes):
    assert classify(row(**changes)) != "legal_entity"


@pytest.mark.parametrize("date", ["1/2/2020", "01/02/2020 12:34:56"])
def test_date_precision_is_preserved(date):
    result, errors = project(row(DATA_INMATRICULARE=date))
    assert not errors
    assert result["registration_date"] == date


def test_invalid_identity_and_date_are_reported_without_raw_values():
    result, errors = project(row(EUID="", DATA_INMATRICULARE="INVALID SYNTHETIC VALUE"))
    assert set(errors) == {"euid_missing", "registration_date_invalid"}
    assert "INVALID SYNTHETIC VALUE" not in str(errors)
    assert result["euid"] is None


def test_schema_and_encoding_fail_closed(tmp_path):
    wrong = csv_file(tmp_path / "wrong.csv", [row()], HEADER[:-1])
    with pytest.raises(ETLError, match="schema_changed"):
        list(records(wrong))
    invalid = tmp_path / "invalid.csv"
    invalid.write_bytes(b"\xef\xbb\xbf" + "^".join(HEADER).encode() + b"\n\xff")
    with pytest.raises(ETLError, match="encoding_invalid"):
        list(records(invalid))


def test_wrong_record_width_is_a_file_error(tmp_path):
    path = csv_file(tmp_path / "wrong-width.csv", [])
    with path.open("a") as handle:
        handle.write("synthetic^incomplete\n")
    with pytest.raises(ETLError, match="record_width_invalid"):
        list(records(path))
