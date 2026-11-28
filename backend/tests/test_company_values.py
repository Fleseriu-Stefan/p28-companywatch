import pytest

from app.api.onrc_models import Company


@pytest.mark.parametrize(
    ("cui", "expected"),
    [
        ("0", None),
        ("000", None),
        ("-8", None),
        ("RO42", None),
        ("٤٢", None),
        (None, None),
        ("0042", "0042"),
    ],
)
def test_cui_projection(cui, expected):
    assert company(cui, None).model_dump(mode="json")["cui"] == expected


@pytest.mark.parametrize("source", ["09/01/2021", "09/01/2021 16:05:00"])
def test_registration_date_projection(source):
    assert company(None, source).model_dump(mode="json")["registration_date"] == "2021-01-09"


def company(cui, registration_date):
    return Company(
        euid="ROONRC.FIXTURE",
        cui=cui,
        registration_date=registration_date,
        name=None,
        registration=None,
        legal_form=None,
        county=None,
        locality=None,
    )
