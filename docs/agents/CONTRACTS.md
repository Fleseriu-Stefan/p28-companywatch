# Contracts — p28-companywatch

<!-- graffino-agentic:begin v1 -->
> Promises across a boundary. **Provided:** this repo owns the contract; the text
> lives here only. **Consumed:** a link to the provider's entry plus the fields this
> repo relies on. **External:** what we rely on from a third-party service.
> Changing a provided contract is a PROPOSAL (AGENTS.md → The gate) and the plan
> lists the consumers' files too. Status: `approved` · `proposed` · `superseded-by`.
<!-- graffino-agentic:end -->

## Index
- C-001 · Health and API documentation · provided
- C-002 · ETL snapshots and publication boundary · provided

---

## Provided

### C-001 · Health and API documentation
- **Status:** approved
- **Date:** 2026-11-17
- **Interface:** `GET /health/live` returns HTTP 200 with `{"status":"ok"}` when the API process responds, independently of database availability. `GET /health/ready` returns HTTP 200 with `{"status":"ready"}` only when MySQL responds and the migration revision matches the application head; otherwise it returns HTTP 503 with `{"status":"not_ready"}`. Database checks have finite timeouts. Responses expose no SQL errors or connection credentials. `/openapi.json` and `/docs` provide the API contract and interactive documentation.
- **Consumers:** `compose.yaml` API healthcheck; `backend/tests/test_health.py`; `backend/tests/test_database.py`; `scripts/verify.py`. No frontend API consumer exists in M1.
- **Evidence:** User explicitly approved C-001 in the M1 plan on 2026-11-17.
- **Confirmed:** 2026-11-17

### C-002 · ETL snapshots and publication boundary
- **Status:** approved
- **Date:** 2026-11-17
- **Interface:** Staged data is not public. A version is identified by source resource, input kind, full SHA-256 and transformation version. Reports reconcile parsed records into excluded, accepted and quarantined categories. Approval binds the source hash, transformation/schema profile, immutable prepared data and quality report. Only fully validated, manually approved versions with at least 100,000 accepted legal-entity records may be published by the real-import CLI. Missing/duplicate EUID groups are quarantined, never resolved by last-write-wins. Synthetic publication is available only to explicitly opted-in isolated tests. Publication locks the dataset pointer and changes pointer/version state in one short InnoDB transaction; consumers resolve the version once per operation. Published versions remain immutable and accessible for SQL diff. EUID is the natural identity used for binary-sensitive matching between published editions. The other seven retained fields are compared with NULL-safe, binary-sensitive predicates to detect changes. A disappearance is not a legal assertion of deregistration. Raw files, detailed addresses and natural-person rows never cross this boundary.
- **ONRC subset profile:** D-018 applies one frozen EUID threshold to both approved editions during parsing. Only occurrences of selected EUIDs may reach staging, including occurrences from ineligible records needed for duplicate detection. Reports reconcile the complete source into accepted, quarantined, policy-excluded and out-of-subset rows. Invalid rows outside staging remain in the quality counts. The version manifest binds the selection rule and threshold to the calibration evidence for both editions. Real versions under this profile require at least 110,000 accepted distinct EUIDs before manual publication.
- **Consumers:** backend/app/etl/service.py, backend/app/etl/cli.py, backend/app/etl/diff.py and backend/tests/test_etl_database.py. No frontend consumer or new HTTP API is provided in M2.
- **Evidence:** User explicitly approved the M2 plan and C-002, with the stated source-validation and data-minimization conditions. The owner explicitly approved the diff wording clarification on 2026-11-19 during the Lab 1 Section E control review. [Approval record](../../AI_LOG.md#2026-11-19--lab-1-section-e-control-decisions).
- **Confirmed:** 2026-11-28

## Consumed
None identified; M1 has no consumed application contracts.

## External
None identified; no service integration is configured.
