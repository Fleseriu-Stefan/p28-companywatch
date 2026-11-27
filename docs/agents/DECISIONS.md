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
- D-009 · Mandatory final project scope
- D-010 · Observed company history
- D-011 · Application roles and access boundaries
- D-012 · Reproducible saved visualizations
- D-013 · Schema review and publication
- D-014 · Grouped ONRC aggregates
- D-015 · Main dashboard and export semantics

---

## D-001 · All application servers run in Docker
- **Status:** approved
- **Date:** 2026-11-06
- **Rule:** All application servers, including databases, API servers and web servers, run in Docker.
- **Why:** The professor requires Docker for every server used in the laboratory project.
- **Evidence:** Lab Setup.pdf, page 1, “Cum lucrăm la laborator”; user approval dated 2026-11-06.
- **Source:** user · confidence high
- **Confirmed:** 2026-11-26

## D-003 · CompanyWatch technical stack
- **Status:** approved
- **Date:** 2026-11-17
- **Rule:** Use React, TypeScript and Vite for the frontend; FastAPI for the backend; MySQL, SQLAlchemy, PyMySQL and Alembic for persistence; Docker Compose for application services. M1 supplies frontend structure and build tooling without visual UI pending D-002.
- **Why:** Establish the first technical milestone without assuming dataset structure or visual requirements.
- **Evidence:** User explicitly approved the M1 plan and D-003 on 2026-11-17.
- **Confirmed:** 2026-11-26

## D-004 · Docker verification and continuous integration
- **Status:** approved
- **Date:** 2026-11-17
- **Rule:** Run application verification in Docker, with real MySQL integration tests. Use pytest and HTTPX for backend tests, Ruff for Python checks, TypeScript and ESLint for frontend checks, and GitHub Actions on pull requests and pushes to main. CI checks the ledger, backend tests, frontend build and Compose smoke behaviour. Pin compatible dependencies during implementation.
- **Why:** Make M1 startup and verification reproducible locally and in CI.
- **Evidence:** User explicitly approved the M1 plan and D-004 on 2026-11-17.
- **Confirmed:** 2026-11-26

## D-005 · CompanyWatch requirements and dataset approval
- **Status:** approved
- **Date:** 2026-11-17
- **Rule:** Build an ETL + API + Dashboard project using a real public dataset with at least 100,000 rows and two real versions, idempotent ingestion, quality reports, SQL-computed diff, schema-change detection, documented API and interactive dashboard. ONRC is a candidate only until its source, schema and versions are verified. M1 implements technical foundations, not these dataset-dependent features.
- **Why:** Preserve the professor requirements supplied by the user without inventing dataset or interview evidence.
- **Evidence:** User supplied the requirements and explicitly approved D-005 and M1 on 2026-11-17.
- **Confirmed:** 2026-11-26

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
- **Confirmed:** 2026-11-26

## D-007 · ONRC parsing, candidate identity and minimal legal-entity scope
- **Status:** approved
- **Date:** 2026-11-17
- **Rule:** Use UTF-8 with BOM, separator ^ and literal quote characters as the candidate ONRC profile, validating the full file before publication. EUID is a candidate natural key; missing keys and all rows participating in duplicate keys must not be published automatically. Persist only reliably identified legal entities and minimal identifiers, name, legal form, county, locality and registration date. Detailed addresses and natural-person records are not retained. Unknown classifications fail closed and are reported. Temporary protected local raw files are permitted only during processing, excluded from Git and public output, and removed after processing including failures.
- **Why:** Sampling found malformed standard CSV quoting, duplicate/missing identifiers and natural-person records.
- **Evidence:** User explicitly approved D-007 and the M2 scope/data-minimization conditions; classification evidence is documented in ../ONRC-SOURCE.md.
- **Confirmed:** 2026-11-26

## D-008 · ETL version lifecycle, SQL diff and atomic publication
- **Status:** approved
- **Date:** 2026-11-17
- **Rule:** Implement streaming download and SHA-256, strict parsing, validation, staging, reconciled quality reports, idempotent immutable versions, explicit manual approval and transactional atomic publication in MySQL. Compare published versions in SQL using EUID and NULL-safe field comparisons. Preserve existing MySQL data. Initially test only with synthetic fixtures and isolated MySQL databases. Evolve schema-dependent M1 tests as explicitly authorized, preserving baseline history and verifying upgrade data preservation. No commit, push, merge or deploy is authorized.
- **Why:** Incomplete or unapproved imports must not replace published data; M2 migrations supersede the test assumption that the database contains only the M1 baseline.
- **Evidence:** User explicitly approved D-008, C-002 and the M2 implementation conditions, including evolution of M1 migration tests.
- **Confirmed:** 2026-11-26

## D-009 · Mandatory final project scope
- **Status:** approved
- **Date:** 2026-11-19
- **Rule:** Deliver the mandatory P28 and general university requirements in [the requirements matrix](../P28-REQUIREMENTS.md). Preserve and reuse M1, M2 and M2.1. Exclude multi-year financial analysis from additional sources, fiscal/TVA checks, automatic notifications and commercial accounting-software integration. Add another dataset only if necessary for a mandatory requirement and explicitly approved.
- **Why:** The project owner supplied the complete scope and chose to retain the baseline in D-005.
- **Evidence:** [Section C decision review and scope](../P28-REQUIREMENTS.md#section-c-decision-review).
- **Confirmed:** 2026-11-26

## D-010 · Observed company history
- **Status:** approved
- **Date:** 2026-11-19
- **Rule:** Resolve the latest published edition dated on or before the requested date. Query by EUID using validity intervals and show the selected edition date and source. Return unavailable before the earliest eligible edition. If the company is absent, report its absence from the selected snapshot. Infer no exact real-world change date.
- **Why:** A dated export establishes an observed state and its source. Historical queries must exclude later observations.
- **Evidence:** Section C question 7 and explicit approval of this documentation package. See [historical acceptance](../P28-REQUIREMENTS.md#acceptance-for-the-main-workflow).
- **Confirmed:** 2026-11-19

## D-011 · Application roles and access boundaries
- **Status:** approved
- **Date:** 2026-11-19
- **Rule:** Serve visitors through protected read-only routes for published data, history, comparisons and saved visualizations, without visitor accounts or API keys. Require valid API keys, rate limits and quotas for the external API. Share query logic across both route sets. Require authenticated, server-side authorization for privileged actions. Curators run and review ingestion, approve mappings and publish validated editions. Administrators manage users, roles, API keys and permissions. Curators cannot grant themselves privileges or manage administrator permissions.
- **Why:** The four roles need distinct access boundaries while public visitors must be able to use the dashboard without credentials.
- **Evidence:** Section C questions 11 and 17 and explicit approval of this documentation package.
- **Confirmed:** 2026-11-19

## D-012 · Reproducible saved visualizations
- **Status:** approved
- **Date:** 2026-11-19
- **Rule:** Authenticated curators and administrators can create and manage saved visualizations. Visitors can open stable links without write permission. Store filters, chart configuration and the exact published version or version pair. Resolve the latest published version at save time if none was selected. Keep the links and selected versions available after restarts and new publications until authorized deletion.
- **Why:** A shared visualization should keep displaying the data selection it was created with.
- **Evidence:** Section C questions 12 and 13 and explicit approval of this documentation package.
- **Confirmed:** 2026-11-19

## D-013 · Schema review and publication
- **Status:** approved
- **Date:** 2026-11-19
- **Rule:** Record each version's source schema and explicit canonical mapping. Display detected differences, including old and new column names, and suggest only mappings supported by evidence. Curators explicitly resolve ambiguous required mappings, review or correct suggestions, and approve the mapping. Publication stays blocked until required mappings are resolved, validation succeeds and the curator approves publication under D-008. Earlier published versions stay immutable and queryable.
- **Why:** Schema changes must undergo explicit review and must preserve previously published data.
- **Evidence:** Section C question 10 and explicit approval of this documentation package.
- **Confirmed:** 2026-11-19

## D-014 · Grouped ONRC aggregates
- **Status:** approved
- **Date:** 2026-11-19
- **Rule:** COUNT company rows by published edition and legal form. SUM accepted and quarantined records separately by edition using one selected published report per edition. Report intentional exclusions separately. AVG the equally weighted per-edition rates `quarantined_records / source_records` for selected editions of the ONRC dataset. Missing counts remain unavailable. Omit missing inputs and zero denominators from AVG and return null when none qualify. Preserve measured zeroes. Use only verified fields and ETL metrics.
- **Why:** Existing company rows and quality reports supply meaningful aggregates without duplicate counts from idempotent runs.
- **Evidence:** Section C question 6 and explicit approval of the resulting aggregate definitions.
- **Confirmed:** 2026-11-19

## D-015 · Main dashboard and export semantics
- **Status:** approved
- **Date:** 2026-11-19
- **Rule:** Keep search by verified name or CUI, company selection, profile and edition comparison on the main page. Offer verified legal form, county and locality filters, plus edition and applicable change-type filters for comparisons. CSV and XLSX export all matching results using the active filters, sort, editions and view. Include identifier, change type, edition references and previous/current values for comparisons. Export grouped rows for aggregate views and identify unavailable values in both formats.
- **Why:** The main page supports the accountant's preliminary partner check. Both export formats must represent the same selected data across pagination.
- **Evidence:** Section C questions 2–4 and 14–16 and explicit approval of this documentation package. See [main workflow acceptance](../P28-REQUIREMENTS.md#acceptance-for-the-main-workflow).
- **Confirmed:** 2026-11-19
