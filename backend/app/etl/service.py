import hashlib
import hmac
import json
import secrets
from collections import Counter
from contextlib import contextmanager
from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import delete, func, insert, select, text, update
from sqlalchemy.dialects.mysql import insert as mysql_insert
from sqlalchemy.exc import SQLAlchemyError

from app.etl.errors import ETLError
from app.etl.models import attempts, companies, publications, staging, versions
from app.etl.parser import classify, project, records
from app.etl.source import HEADER, LEGAL_FORMS, PROFILE_VERSION, RETAINED, SOURCES

DATASET = "onrc-firme-pj"
FIELDS = tuple(RETAINED.values())


def digest_json(value):
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode()
    ).hexdigest()


SCHEMA_HASH = digest_json(
    {
        "header": HEADER,
        "encoding": "utf-8-sig",
        "separator": "^",
        "quotes": "literal",
        "legal_forms": sorted(LEGAL_FORMS),
        "retained": RETAINED,
        "profile": PROFILE_VERSION,
    }
)


def file_hash(path):
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


@contextmanager
def ingest_transaction(connection, lock_name):
    if connection.invalidated:
        raise ETLError("ingest_lock_lost")
    try:
        with connection.begin():
            owns_lock = connection.scalar(
                text("SELECT IS_USED_LOCK(:name) = CONNECTION_ID()"), {"name": lock_name}
            )
            if owns_lock != 1:
                raise ETLError("ingest_lock_lost")
            yield
    except SQLAlchemyError:
        if connection.invalidated:
            raise ETLError("ingest_lock_lost") from None
        raise


class Pipeline:
    def __init__(self, engine, *, minimum_rows=100000, allow_synthetic=False):
        self.engine = engine
        self.minimum_rows = minimum_rows
        self.allow_synthetic = allow_synthetic

    def ingest(self, path, source, *, transfer=None):
        sha256 = file_hash(path)
        lock_name = digest_json(
            [self.engine.url.database, source.kind, source.resource_id, PROFILE_VERSION, sha256]
        )
        # A server-side session lock is released even if the worker process dies.
        # Holding it proves any old loading attempt for this input is abandoned.
        with self.engine.connect() as connection:
            try:
                acquired = connection.scalar(text("SELECT GET_LOCK(:name, 0)"), {"name": lock_name})
                connection.commit()
            except SQLAlchemyError:
                connection.invalidate()
                raise
            if acquired != 1:
                raise ETLError("version_busy")
            try:
                return self._ingest(connection, lock_name, path, source, sha256, transfer=transfer)
            finally:
                if not connection.invalidated:
                    try:
                        released = connection.scalar(
                            text("SELECT RELEASE_LOCK(:name)"), {"name": lock_name}
                        )
                    except SQLAlchemyError:
                        released = None
                    if released != 1:
                        connection.invalidate()

    def _ingest(self, connection, lock_name, path, source, sha256, *, transfer=None):
        if source.kind not in {"real", "synthetic"}:
            raise ETLError("source_kind_invalid")
        if source.kind == "real" and SOURCES.get(source.edition) != source:
            raise ETLError("source_not_approved")
        if source.kind == "synthetic" and not self.allow_synthetic:
            raise ETLError("synthetic_not_allowed")
        if source.size is not None and path.stat().st_size != source.size:
            raise ETLError("source_size_changed")
        candidate, attempt_id = str(uuid4()), str(uuid4())
        identity = (
            versions.c.source_kind == source.kind,
            versions.c.resource_id == source.resource_id,
            versions.c.sha256 == sha256,
            versions.c.profile == PROFILE_VERSION,
        )
        with ingest_transaction(connection, lock_name):
            statement = mysql_insert(versions).values(
                id=candidate,
                edition=source.edition,
                resource_id=source.resource_id,
                source_url=source.url,
                license="CC-BY-4.0",
                source_kind=source.kind,
                sha256=sha256,
                profile=PROFILE_VERSION,
                schema_hash=SCHEMA_HASH,
                state="loading",
                created_at=datetime.now(UTC).replace(tzinfo=None),
                manifest={
                    "package_id": source.package_id,
                    "resource_id": source.resource_id,
                    "edition": source.edition,
                    "url": source.url,
                    "declared_bytes": source.size,
                    "observed_bytes": path.stat().st_size,
                    "transfer": transfer or {},
                },
            )
            connection.execute(statement.on_duplicate_key_update(id=versions.c.id))
            version = (
                connection.execute(select(versions).where(*identity).with_for_update())
                .mappings()
                .one()
            )
            version_id = version["id"]
            reused = candidate != version_id and version["state"] in {
                "review",
                "approved",
                "published",
            }
            abandoned = candidate != version_id and version["state"] == "loading"
            if abandoned:
                connection.execute(
                    update(attempts)
                    .where(attempts.c.version_id == version_id, attempts.c.state == "loading")
                    .values(state="abandoned", failure_code="worker_interrupted")
                )
            connection.execute(
                insert(attempts).values(
                    id=attempt_id,
                    version_id=version_id,
                    state="reused" if reused else "loading",
                    created_at=datetime.now(UTC).replace(tzinfo=None),
                )
            )
            if not reused:
                connection.execute(delete(staging).where(staging.c.version_id == version_id))
                connection.execute(delete(companies).where(companies.c.version_id == version_id))
                connection.execute(
                    update(versions)
                    .where(versions.c.id == version_id)
                    .values(
                        state="loading",
                        report=None,
                        report_hash=None,
                        prepared_hash=None,
                        approval=None,
                    )
                )
        if reused:
            return version_id

        counters, reasons, nulls = Counter(), Counter(), Counter()
        # Detect duplicate identities across the entire source without persisting
        # identifiers or personal values from excluded records. This key lives only
        # in this worker; keyed digests and staging rows are deleted on completion.
        identity_secret = secrets.token_bytes(32)
        examples, batch = [], []
        try:
            for ordinal, row in records(path):
                counters["source_records"] += 1
                classification = classify(row)
                if classification == "natural_person_excluded":
                    counters["excluded_records"] += 1
                if classification == "legal_entity":
                    projected, errors = project(row)
                    counters["legal_entity_candidates"] += 1
                    counters["cui_zero"] += projected["cui"] == "0"
                    nulls.update(key for key, value in projected.items() if value is None)
                else:
                    projected = dict.fromkeys(FIELDS)
                    errors = [classification]
                reasons.update(errors)
                if errors and len(examples) < 20:
                    examples.append({"source_line": ordinal, "codes": errors})
                batch.append(
                    dict(
                        version_id=version_id,
                        source_line=ordinal,
                        valid=not errors,
                        excluded=classification == "natural_person_excluded",
                        key_digest=hmac.new(
                            identity_secret, row["EUID"].encode(), hashlib.sha256
                        ).hexdigest()
                        if row["EUID"].strip()
                        else None,
                        errors=errors,
                        **projected,
                    )
                )
                if len(batch) >= 1000:
                    self._stage(connection, lock_name, batch)
                    batch = []
            if batch:
                self._stage(connection, lock_name, batch)
            if file_hash(path) != sha256:
                raise ETLError("source_changed_during_parse")
            with ingest_transaction(connection, lock_name):
                duplicate_keys = (
                    select(staging.c.key_digest)
                    .where(staging.c.version_id == version_id, staging.c.key_digest.is_not(None))
                    .group_by(staging.c.key_digest)
                    .having(func.count() > 1)
                    .subquery()
                )
                duplicate = staging.c.key_digest.in_(select(duplicate_keys.c.key_digest))
                scope = staging.c.version_id == version_id
                duplicate_groups = connection.scalar(
                    select(func.count()).select_from(duplicate_keys)
                )
                duplicate_rows = connection.scalar(
                    select(func.count()).select_from(staging).where(scope, duplicate)
                )
                for ordinal in connection.scalars(
                    select(staging.c.source_line).where(scope, duplicate).limit(20)
                ):
                    if len(examples) < 20:
                        examples.append({"source_line": ordinal, "codes": ["euid_duplicate"]})
                connection.execute(update(staging).where(scope, duplicate).values(valid=False))
                accepted = connection.scalar(
                    select(func.count())
                    .select_from(staging)
                    .where(scope, staging.c.valid.is_(True))
                )
                quarantined = connection.scalar(
                    select(func.count())
                    .select_from(staging)
                    .where(scope, staging.c.valid.is_(False), staging.c.excluded.is_(False))
                )
                connection.execute(
                    insert(companies).from_select(
                        ["version_id", *FIELDS],
                        select(staging.c.version_id, *(staging.c[key] for key in FIELDS)).where(
                            scope, staging.c.valid.is_(True)
                        ),
                    )
                )
                reasons["euid_duplicate"] = duplicate_rows
                report = {
                    "source_records": counters["source_records"],
                    "excluded_records": counters["excluded_records"],
                    "accepted_records": accepted,
                    "quarantined_records": quarantined,
                    "legal_entity_candidates": counters["legal_entity_candidates"],
                    "duplicate_key_groups": duplicate_groups,
                    "duplicate_key_records": duplicate_rows,
                    "cui_zero": counters["cui_zero"],
                    "null_fields": dict(nulls),
                    "reasons": dict(reasons),
                    "examples": examples,
                    "full_file_validated": True,
                    "source_kind": source.kind,
                    "minimum_records": max(100000, self.minimum_rows)
                    if source.kind == "real"
                    else self.minimum_rows,
                    "filter_policy": (
                        "J+SRL/SA/SNC; no branches; unknown classification quarantined"
                    ),
                    "schema_hash": SCHEMA_HASH,
                    "profile": PROFILE_VERSION,
                }
                if report["source_records"] != accepted + quarantined + report["excluded_records"]:
                    raise ETLError("quality_totals_mismatch")
                connection.execute(delete(staging).where(scope))
            with ingest_transaction(connection, lock_name):
                prepared_hash = self._prepared_hash(connection, version_id)
                connection.execute(
                    update(versions)
                    .where(versions.c.id == version_id)
                    .values(
                        state="review",
                        report=report,
                        report_hash=digest_json(report),
                        prepared_hash=prepared_hash,
                    )
                )
                connection.execute(
                    update(attempts).where(attempts.c.id == attempt_id).values(state="ready")
                )
            return version_id
        except (ETLError, SQLAlchemyError, OSError) as error:
            code = (
                str(error)
                if isinstance(error, ETLError)
                else "database_error"
                if isinstance(error, SQLAlchemyError)
                else "artifact_error"
            )
            if connection.invalidated or code == "ingest_lock_lost":
                raise ETLError("ingest_lock_lost") from None
            with ingest_transaction(connection, lock_name):
                connection.execute(delete(staging).where(staging.c.version_id == version_id))
                connection.execute(delete(companies).where(companies.c.version_id == version_id))
                report = {
                    "full_file_validated": False,
                    "failure_code": code,
                    "source_records": counters["source_records"],
                    "source_kind": source.kind,
                }
                connection.execute(
                    update(versions)
                    .where(versions.c.id == version_id)
                    .values(state="failed", report=report, report_hash=digest_json(report))
                )
                connection.execute(
                    update(attempts)
                    .where(attempts.c.id == attempt_id)
                    .values(state="failed", failure_code=code)
                )
            raise ETLError(code) from None

    def _stage(self, connection, lock_name, batch):
        with ingest_transaction(connection, lock_name):
            connection.execute(insert(staging), batch)

    def _prepared_hash(self, connection, version_id):
        digest = hashlib.sha256()
        with connection.execute(
            select(*(companies.c[key] for key in FIELDS))
            .where(companies.c.version_id == version_id)
            .order_by(companies.c.euid)
            .execution_options(stream_results=True)
        ) as result:
            for row in result:
                digest.update(
                    json.dumps(list(row), ensure_ascii=False, separators=(",", ":")).encode()
                )
                digest.update(b"\n")
        return digest.hexdigest()

    def report(self, version_id):
        with self.engine.connect() as connection:
            value = (
                connection.execute(select(versions).where(versions.c.id == version_id))
                .mappings()
                .first()
            )
        if value is None:
            raise ETLError("version_not_found")
        return {
            key: value[key]
            for key in (
                "id",
                "edition",
                "source_kind",
                "state",
                "sha256",
                "profile",
                "schema_hash",
                "report",
                "report_hash",
                "manifest",
            )
        }

    def _validate_seal(self, version, *, verify_data=True):
        report = version["report"]
        if version["source_kind"] == "synthetic" and not self.allow_synthetic:
            raise ETLError("synthetic_not_allowed")
        if not report or digest_json(report) != version["report_hash"]:
            raise ETLError("report_changed")
        minimum = (
            max(100000, report["minimum_records"])
            if version["source_kind"] == "real"
            else report["minimum_records"]
        )
        if not report["full_file_validated"] or report["accepted_records"] < minimum:
            raise ETLError("insufficient_records")
        if verify_data:
            with self.engine.connect() as connection:
                if self._prepared_hash(connection, version["id"]) != version["prepared_hash"]:
                    raise ETLError("prepared_data_changed")
        return digest_json(
            {
                key: version[key]
                for key in (
                    "id",
                    "resource_id",
                    "source_kind",
                    "sha256",
                    "profile",
                    "schema_hash",
                    "report_hash",
                    "prepared_hash",
                    "manifest",
                )
            }
        )

    def approve(self, version_id, report_hash):
        with self.engine.begin() as connection:
            version = (
                connection.execute(
                    select(versions).where(versions.c.id == version_id).with_for_update()
                )
                .mappings()
                .first()
            )
            if version is None or version["state"] not in {"review", "approved"}:
                raise ETLError("version_not_reviewable")
            if report_hash != version["report_hash"]:
                raise ETLError("report_hash_mismatch")
            seal = self._validate_seal(version)
            connection.execute(
                update(versions)
                .where(versions.c.id == version_id)
                .values(state="approved", approval=seal)
            )
        return seal

    def publish(self, version_id, approval):
        # Perform the expensive integrity scan before taking the publication lock.
        # Prepared rows have no mutation path once review begins (C-002).
        with self.engine.connect() as connection:
            preview = (
                connection.execute(select(versions).where(versions.c.id == version_id))
                .mappings()
                .first()
            )
        if preview is None or preview["state"] not in {"approved", "published"}:
            raise ETLError("approval_required")
        if self._validate_seal(preview) != approval:
            raise ETLError("approval_invalidated")
        with self.engine.begin() as connection:
            connection.execute(
                select(publications).where(publications.c.dataset == DATASET).with_for_update()
            ).one()
            version = (
                connection.execute(
                    select(versions).where(versions.c.id == version_id).with_for_update()
                )
                .mappings()
                .first()
            )
            if (
                version is None
                or version["state"] not in {"approved", "published"}
                or version["approval"] != approval
            ):
                raise ETLError("approval_required")
            if self._validate_seal(version, verify_data=False) != approval:
                raise ETLError("approval_invalidated")
            if version["state"] == "published":
                return
            self._activate(connection, version_id)

    def _activate(self, connection, version_id):
        connection.execute(
            update(publications)
            .where(publications.c.dataset == DATASET)
            .values(current_version_id=version_id)
        )
        connection.execute(
            update(versions).where(versions.c.id == version_id).values(state="published")
        )

    def diff(self, old_id, new_id):
        from app.etl.diff import compare

        return compare(self.engine, old_id, new_id, allow_synthetic=self.allow_synthetic)
