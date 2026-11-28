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
- C-003 · Public ONRC visitor API · provided
- C-004 · Operator sessions and API access · provided

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

### C-003 · Public ONRC visitor API
- **Status:** approved
- **Date:** 2026-11-28
- **Interface:** Read-only GET routes serve published ONRC legal-entity snapshots and allowlisted quality counts. They are mounted at `/api/web/v1` for visitors and `/api/v1` for external clients under C-004. FastAPI describes response models, parameters and conditional requests in `/openapi.json`. Edition dates are ISO calendar dates. Version parameters use the IDs returned by `/versions`.
- **Versions:** `/versions` returns edition dates, version IDs, source URL, resource ID and license, quality counts, and the current publication flag.
- **Search:** `/companies` accepts `name` with `name_match=contains|prefix` (default contains) using literal, case- and accent-insensitive matching. `cui`, `legal_form`, `county` and `locality` use exact matching. Supplied filters combine with AND. `sort=name|registration_date` is ascending, defaults to name, puts missing dates last, and breaks ties by binary EUID. Registration dates sort by parsed calendar date and return `YYYY-MM-DD` or null. Company responses return CUI as a positive ASCII digit string or null for missing or invalid values, including zero. `version` defaults to the current publication.
- **History:** `/companies/{euid}` uses binary EUID. With `as_of=YYYY-MM-DD`, resolve the latest published edition dated on or before that date, breaking same-date ties by greatest version ID. Without `as_of`, use the current publication pointer. Return `present`, `absent` or `unavailable` with the selected edition source and observed interval when available. `valid_from` is the selected edition date. `valid_to` is the next later published edition date, exclusive, or null. Snapshot absence describes only the observed coverage.
- **Diff:** `/versions/{a}/diff/{b}` compares two published versions, from a to b. Optional `change_type` selects added, removed, modified or unchanged rows. Changes sort by binary EUID and include previous and current values and changed field names. Changed field names reflect C-002 retained-value comparisons. Display normalization can make two changed values appear equal.
- **Pagination:** Search and diff use `limit` (default 50, range 1–200) and `cursor`. Send `next_cursor` with the same query settings to continue within the same version or comparison. A null cursor ends traversal. Invalid parameters, mismatched cursors and selections of different versions for the same aggregate edition receive 422. An unknown or unpublished selected version receives 404. Database failures receive a generic 503.
- **Aggregates:** `/aggregates` returns company counts by edition and legal form, a further county breakdown, and separate edition totals for accepted, quarantined and excluded records. D-018 out-of-subset counts stay separate. Repeat `version` to select exact versions. The default selects one published version per edition, breaking same-date ties by greatest version ID. The average quarantine rate is the equally weighted mean of quarantined/source-record ratios with both counts available and nonzero source counts. Missing counts and an average with no eligible editions are null. Measured zero remains zero.
- **Caching:** Successful responses include `ETag` and revalidate via `If-None-Match`. A match returns 304 with the validator and an empty body after C-004 access checks. The unpinned version list, first search page, current company lookup and default aggregates incorporate the current published version in the validator. Explicit version selections and cursor continuations stay stable across unrelated publication. Historical date validators follow the selected snapshot and the returned validity interval.
- **Consumers:** OpenAPI clients and `backend/tests/test_public_api.py`.
- **Evidence:** The project owner approved the public API plan, C-003 and the index and query adjustments on 2026-11-28. The owner subsequently approved the two mounts and response normalization in the authentication delivery.
- **Confirmed:** 2026-11-28

### C-004 · Operator sessions and API access
- **Status:** approved
- **Date:** 2026-11-28
- **Interface:** Operators authenticate through session routes. The two C-003 read mounts use independent access and rate-limit checks.
- **Sessions:** `POST /api/v1/auth/login` accepts email and password and sets a signed, opaque `HttpOnly; Secure; SameSite=Strict` cookie. The API process stores sessions with an eight-hour absolute expiry. Logout at `POST /api/v1/auth/logout` invalidates the session and clears the cookie. `GET /api/v1/auth/me` returns the active account. Restarting the single API worker ends active sessions. Authenticated operations check current account status and role in MySQL. Cookie-authenticated writes require a same-origin browser request.
- **Roles:** Visitors can read `/api/web/v1` without credentials. External clients use an API key for C-003 reads at `/api/v1`. Operators use a session for privileged routes. A missing or invalid session receives 401 and the wrong operator role receives 403. Either operator role needs a key for external reads.
- **Administrator:** `POST /api/v1/admin/curators` creates a curator with a salted Argon2id password hash. `DELETE /api/v1/admin/curators/{user_id}` deactivates only curator accounts. `POST /api/v1/admin/api-keys` issues a named key owned by an active account and discloses the full key once. The database retains the display prefix and SHA-256 digest alongside metadata. `DELETE /api/v1/admin/api-keys/{key_id}` revokes the key. Issued keys stay valid until revoked. The first administrator is created by the interactive server bootstrap.
- **Curator:** `GET /api/v1/curator/versions` returns real versions in review with their reports and report hashes. The optional `state=approved` filter lists approved versions awaiting publication. `POST /api/v1/curator/versions/{version_id}/approve` requires the reviewed report hash. `POST /api/v1/curator/versions/{version_id}/publish` uses the stored approval. Both writes pass through the C-002 Pipeline gate. An invalid transition receives 409.
- **External limits:** OpenAPI declares the `X-API-Key` security scheme. A missing, invalid, or revoked key receives 401. Admitted requests, including conditional 304s, consume both a fixed UTC minute window of 60 and a fixed UTC calendar-day quota of 5,000 per issued key. Counters are atomic in MySQL. Keyed responses use private revalidation.
- **Dashboard limits:** Web reads share the C-003 query logic and use a fixed window of 120 requests per minute per client IP. Production identifies clients through forwarding headers set by the dedicated Caddy peer. The single worker keeps expiring dashboard counters in memory. Limit responses on either mount use 429 and an integer `Retry-After` in seconds.
- **Consumers:** OpenAPI clients, `backend/tests/test_auth.py`, `backend/tests/test_api_access.py`, `backend/tests/test_public_api.py`, the proxy verification in `scripts/verify.py`, and the Azure operator procedure.
- **Evidence:** The project owner approved this contract and its implementation with the auth delivery plan.
- **Confirmed:** 2026-11-28

## Consumed
None identified; M1 has no consumed application contracts.

## External
None identified; no service integration is configured.
