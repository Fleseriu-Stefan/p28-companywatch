from dataclasses import dataclass

HEADER = (
    "DENUMIRE",
    "CUI",
    "COD_INMATRICULARE",
    "DATA_INMATRICULARE",
    "EUID",
    "FORMA_JURIDICA",
    "ADR_TARA",
    "ADR_JUDET",
    "ADR_LOCALITATE",
    "ADR_DEN_STRADA",
    "ADR_NR_STRADA",
    "ADR_BLOC",
    "ADR_SCARA",
    "ADR_ETAJ",
    "ADR_APARTAMENT",
    "ADR_COD_POSTAL",
    "ADR_SECTOR",
    "ADR_COMPLETARE",
    "WEB",
    "TARA_FIRMA_MAMA",
)
RETAINED = {
    "EUID": "euid",
    "CUI": "cui",
    "COD_INMATRICULARE": "registration",
    "DENUMIRE": "name",
    "FORMA_JURIDICA": "legal_form",
    "ADR_JUDET": "county",
    "ADR_LOCALITATE": "locality",
    "DATA_INMATRICULARE": "registration_date",
}
PROFILE_VERSION = "onrc-pj-v1"
LEGAL_FORMS = frozenset({"SRL", "SA", "SNC"})


@dataclass(frozen=True)
class Source:
    edition: str
    package_id: str
    resource_id: str
    size: int | None
    kind: str = "real"

    @property
    def url(self) -> str:
        return (
            f"https://data.gov.ro/dataset/{self.package_id}/resource/"
            f"{self.resource_id}/download/od_firme.csv"
        )


SOURCES = {
    "2026-10-19": Source(
        "2026-10-19",
        "1962670f-acda-41b5-b52c-c430d7a1ef5e",
        "361e52e3-4590-40af-ae0f-8a15089fc927",
        695782068,
    ),
    "2026-11-04": Source(
        "2026-11-04",
        "c2c88c9d-4824-45f1-90ec-656f1c0d8785",
        "869eac01-8480-4ac6-a18d-d0f044b0db80",
        696515538,
    ),
}
