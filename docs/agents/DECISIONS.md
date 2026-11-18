# Decisions — p28-companywatch

<!-- graffino-agentic:begin v1 -->
> Constraints the code must obey. Status: `approved` (obey) · `proposed` (do not
> build on it) · `superseded-by <ID>` (kept to explain old code).
> Adding or changing an entry needs the user's OK (AGENTS.md → The gate).
<!-- graffino-agentic:end -->

## Index
- D-001 · All application servers run in Docker
- D-003 · CompanyWatch technical stack
- D-004 · Docker verification and continuous integration
- D-005 · CompanyWatch requirements and dataset approval
- D-002 · Figma approval with versioned local design mocks
- D-006 · Approved ONRC development sources
- D-007 · ONRC parsing, candidate identity and minimal legal-entity scope
- D-008 · ETL version lifecycle, SQL diff and atomic publication

---

## D-001 · All application servers run in Docker
- **Status:** approved
- **Date:** 2026-11-06
- **Rule:** All application servers, including databases, API servers and web servers, run in Docker.
- **Why:** The professor requires Docker for every server used in the laboratory project.
- **Evidence:** Lab Setup.pdf, page 1, “Cum lucrăm la laborator”; user approval dated 2026-11-06.
- **Source:** user · confidence high
- **Confirmed:** 2026-11-06

## D-003 · CompanyWatch technical stack
- **Status:** approved
- **Date:** 2026-11-17
- **Rule:** Use React, TypeScript and Vite for the frontend; FastAPI for the backend; MySQL, SQLAlchemy, PyMySQL and Alembic for persistence; Docker Compose for application services. M1 supplies frontend structure and build tooling without visual UI pending D-002.
- **Why:** Establish the first technical milestone without assuming dataset structure or visual requirements.
- **Evidence:** User explicitly approved the M1 plan and D-003 on 2026-11-17.
- **Confirmed:** 2026-11-17

## D-004 · Docker verification and continuous integration
- **Status:** approved
- **Date:** 2026-11-17
- **Rule:** Run application verification in Docker, with real MySQL integration tests. Use pytest and HTTPX for backend tests, Ruff for Python checks, TypeScript and ESLint for frontend checks, and GitHub Actions on pull requests and pushes to main. CI checks the ledger, backend tests, frontend build and Compose smoke behaviour. Pin compatible dependencies during implementation.
- **Why:** Make M1 startup and verification reproducible locally and in CI.
- **Evidence:** User explicitly approved the M1 plan and D-004 on 2026-11-17.
- **Confirmed:** 2026-11-17

## D-005 · CompanyWatch requirements and dataset approval
- **Status:** approved
- **Date:** 2026-11-17
- **Rule:** Build an ETL + API + Dashboard project using a real public dataset with at least 100,000 rows and two real versions, idempotent ingestion, quality reports, SQL-computed diff, schema-change detection, documented API and interactive dashboard. ONRC is a candidate only until its source, schema and versions are verified. M1 implements technical foundations, not these dataset-dependent features.
- **Why:** Preserve the professor requirements supplied by the user without inventing dataset or interview evidence.
- **Evidence:** User supplied the requirements and explicitly approved D-005 and M1 on 2026-11-17.
- **Confirmed:** 2026-11-17

## D-002 · Figma approval with versioned local design mocks
- **Status:** approved
- **Date:** 2026-11-06
- **Rule:** Create and visually approve designs in Figma. Preserve and version the approved representations in `docs/design/mocks/`. Implementation must follow the approved version, using its corresponding local mocks and documented tokens.
- **Why:** The project owner selected Figma for design creation and visual approval while retaining reviewable design representations in the repository.
- **Evidence:** User explicitly approved D-002 and the six-file documentation plan on 2026-11-06.
- **Source:** user · confidence high
- **Confirmed:** 2026-11-06

## D-006 · Approved ONRC development sources
- **Status:** approved
- **Date:** 2026-11-17
- **Rule:** The official OD_FIRME.CSV editions dated 19.10.2026 and 04.11.2026 are approved for M2 development. Preserve source/resource identifiers, URLs, CC BY 4.0 attribution, transfer metadata and SHA-256. Complete source validation remains mandatory before publication. This implementation session may use synthetic fixtures and bounded source investigation only, not full ONRC downloads.
- **Why:** Two authentic editions were verified without claiming full-file integrity or complete quality.
- **Evidence:** User explicitly approved D-006 and the M2 build with these conditions.
- **Confirmed:** 2026-11-17

## D-007 · ONRC parsing, candidate identity and minimal legal-entity scope
- **Status:** approved
- **Date:** 2026-11-17
- **Rule:** Use UTF-8 with BOM, separator ^ and literal quote characters as the candidate ONRC profile, validating the full file before publication. EUID is a candidate natural key; missing keys and all rows participating in duplicate keys must not be published automatically. Persist only reliably identified legal entities and minimal identifiers, name, legal form, county, locality and registration date. Detailed addresses and natural-person records are not retained. Unknown classifications fail closed and are reported. Temporary protected local raw files are permitted only during processing, excluded from Git and public output, and removed after processing including failures.
- **Why:** Sampling found malformed standard CSV quoting, duplicate/missing identifiers and natural-person records.
- **Evidence:** User explicitly approved D-007 and the M2 scope/data-minimization conditions; classification evidence is documented in ../ONRC-SOURCE.md.
- **Confirmed:** 2026-11-17

## D-008 · ETL version lifecycle, SQL diff and atomic publication
- **Status:** approved
- **Date:** 2026-11-17
- **Rule:** Implement streaming download and SHA-256, strict parsing, validation, staging, reconciled quality reports, idempotent immutable versions, explicit manual approval and transactional atomic publication in MySQL. Compare published versions in SQL using EUID and NULL-safe field comparisons. Preserve existing MySQL data. Initially test only with synthetic fixtures and isolated MySQL databases. Evolve schema-dependent M1 tests as explicitly authorized, preserving baseline history and verifying upgrade data preservation. No commit, push, merge or deploy is authorized.
- **Why:** Incomplete or unapproved imports must not replace published data; M2 migrations supersede the test assumption that the database contains only the M1 baseline.
- **Evidence:** User explicitly approved D-008, C-002 and the M2 implementation conditions, including evolution of M1 migration tests.
- **Confirmed:** 2026-11-17
