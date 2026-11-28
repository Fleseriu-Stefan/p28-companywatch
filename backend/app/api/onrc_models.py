import re
from datetime import date
from typing import Literal

from pydantic import BaseModel, Field, field_validator

from app.etl.parser import parse_registration_date

ChangeType = Literal["added", "removed", "modified", "unchanged"]


class EditionSource(BaseModel):
    resource_id: str
    url: str
    license: str


class QualityCounts(BaseModel):
    source_records: int | None = None
    accepted_records: int | None = None
    quarantined_records: int | None = None
    excluded_records: int | None = None
    out_of_subset_records: int | None = None


class PublishedVersion(BaseModel):
    version_id: str
    edition: date
    source: EditionSource
    counts: QualityCounts
    current: bool


class VersionsResponse(BaseModel):
    items: list[PublishedVersion]


class Company(BaseModel):
    euid: str
    cui: str | None
    registration: str | None
    name: str | None
    legal_form: str | None
    county: str | None
    locality: str | None
    registration_date: date | None = Field(description="Registration date in ISO calendar format.")

    @field_validator("cui")
    @classmethod
    def positive_cui(cls, value):
        return value if value and re.fullmatch(r"[0-9]*[1-9][0-9]*", value) else None

    @field_validator("registration_date", mode="before")
    @classmethod
    def iso_registration_date(cls, value):
        return parse_registration_date(value) if isinstance(value, str) else value


class CompanyPage(BaseModel):
    version_id: str
    items: list[Company]
    next_cursor: str | None


class ObservedCompany(BaseModel):
    status: Literal["present", "absent", "unavailable"]
    version_id: str | None = None
    source: EditionSource | None = None
    valid_from: date | None = None
    valid_to: date | None = None
    company: Company | None = None


class DiffRow(BaseModel):
    euid: str
    change_type: ChangeType
    previous: Company | None
    current: Company | None
    changed_fields: list[str]


class DiffPage(BaseModel):
    previous_version_id: str
    current_version_id: str
    items: list[DiffRow]
    next_cursor: str | None


class LegalFormCount(BaseModel):
    version_id: str
    edition: date
    legal_form: str | None
    count: int


class CountyCount(LegalFormCount):
    county: str | None


class EditionQuality(QualityCounts):
    version_id: str
    edition: date


class AggregatesResponse(BaseModel):
    by_legal_form: list[LegalFormCount]
    by_county: list[CountyCount]
    quality_by_edition: list[EditionQuality]
    average_quarantine_rate: float | None
