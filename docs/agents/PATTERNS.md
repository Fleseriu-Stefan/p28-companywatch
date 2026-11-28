# Patterns — p28-companywatch

<!-- graffino-agentic:begin v1 -->
> How we build things here. Copy only `approved` entries. `candidate` = seen once or
> not yet confirmed; agents add these freely. Promotion needs the user's OK.
<!-- graffino-agentic:end -->

## Index
- PATTERN-001 · Isolated Compose verification · candidate
- PATTERN-002 · Review seals for immutable ETL snapshots · candidate
- PATTERN-003 · Bounded recovery under a session lock · candidate
- PATTERN-004 · Restore a published snapshot database before startup · candidate
- PATTERN-005 · Resume an atomic MySQL index migration · candidate
- PATTERN-006 · Atomic admission under a key row lock · candidate

---

No application patterns are approved for replication.

## PATTERN-001 · Isolated Compose verification
- **Status:** candidate
- **Date:** 2026-11-17
- **How:** Exercise database and service lifecycle behaviours in a randomly named Compose project, with temporary credentials generated in memory, an ephemeral loopback port and project-scoped cleanup. Share the entry command between local verification and CI. Never target the development database for schema-negative tests.
- **Example:** scripts/verify.py and .github/workflows/ci.yml establish this practice during approved M1 implementation. Candidate only; promotion requires user approval.
- **Confirmed:** 2026-11-27

## PATTERN-002 · Review seals for immutable ETL snapshots
- **Status:** candidate
- **Date:** 2026-11-18
- **How:** Bind manual approval to the full source hash, transformation/schema profile, prepared-data fingerprint and reconciled report; publish by changing a dataset pointer in a short locked transaction. Quarantined raw values never enter logs or reports. Temporary raw storage is ephemeral and abandoned unpublished attempts are recovered under a source-content lock.
- **Example:** backend/app/etl/service.py, backend/app/etl/cli.py and backend/tests/test_etl_database.py establish this practice in M2. Candidate only, not a pattern approved for replication.
- **Confirmed:** 2026-11-27

## PATTERN-003 · Bounded recovery under a session lock
- **Status:** candidate
- **Date:** 2026-11-25
- **How:** Keep the advisory lock on the same database connection across cleanup
  transactions. Before each batch, verify lock ownership and protect the target
  against publication. Delete at most one indexed batch and commit. After an
  interruption, a new lock owner resumes from the rows still present.
- **Example:** `backend/app/etl/service.py` and `backend/tests/test_etl_database.py`.
- **Confirmed:** 2026-11-27

## PATTERN-004 · Restore a published snapshot database before startup
- **Status:** candidate
- **How:** Restore the application schema, migration revision and publication pointer into an empty database before running migrations. Compare both published versions and the current pointer before and after a container recreate with the same volume.
- **Example:** [Azure deployment procedure](../DEPLOY.md).

## PATTERN-005 · Resume an atomic MySQL index migration
- **Status:** candidate
- **Date:** 2026-11-28
- **How:** Add related indexes in one atomic ALTER TABLE. On retry, compare the existing index definitions with the intended definitions before advancing the Alembic revision. Keep the migration read timeout independent of HTTP query timeouts.
- **Example:** `backend/migrations/versions/0003_public_api_indexes.py` and the interrupted migration check in `backend/tests/test_database.py`.

## PATTERN-006 · Atomic admission under a key row lock
- **Status:** candidate
- **Date:** 2026-11-28
- **How:** Lock the API key row before reading and updating its minute and day
  counters. Update both counters in the same transaction after both checks pass.
  Reuse the key row lock for revocation so admission and revocation serialize.
- **Example:** `backend/app/auth/limits.py` and `backend/tests/test_api_access.py`.
