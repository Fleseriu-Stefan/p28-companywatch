# CompanyWatch requirements and roadmap

The project owner supplied and approved the mandatory P28 catalog and general university
requirements during Lab 1 Section C. This document records the scope for future plans.
Implementation evidence reflects the audited baseline at `719f45d`. The application
verification cited below comes from the existing repository records.

CompanyWatch uses the two approved ONRC development editions and the existing legal-entity
projection. Multi-year financial analysis using additional data, fiscal or TVA checks,
automatic email or SMS notifications, and commercial accounting-software integration are
excluded. Another dataset requires a demonstrated mandatory need and explicit approval.
CSV/XLSX, API access, version history, authentication and authorization are in scope.
[Approved decisions](agents/DECISIONS.md)

## Section C decision review

The project owner explicitly confirmed each existing decision as written during the
2026-11-19 interview. The original entries and their historical confirmation dates are
preserved.

| Decision | Owner's confirmation |
|---|---|
| D-001 | Keep all application servers in Docker. Hosting is still open under Q-007. |
| D-002 | Keep Figma approval of a specific version and its matching versioned local mock before UI implementation. |
| D-003 | Keep React, TypeScript, Vite, FastAPI, MySQL, SQLAlchemy, PyMySQL, Alembic and local Docker Compose. |
| D-004 | Keep Docker-based verification, isolated real MySQL integration tests, and GitHub Actions. |
| D-005 | Keep the baseline and record the complete mandatory scope in a companion decision. |
| D-006 | Keep the two development editions and validate full files before publication. Propose any replacement separately. |
| D-007 | Keep the candidate profile and EUID, quarantine rules, approval-gated changes, and eight-field legal-entity projection. |
| D-008 | Keep immutable versions, SQL comparisons, and atomic publication with explicit curator approval. |

The owner also approved D-009 through D-015. The approval covered documentation.
[Decision ledger](agents/DECISIONS.md) · [Session log](../AI_LOG.md)

## Acceptance for the main workflow

The accountant described a recurring workflow problem. Checking a possible partner
takes time because the accountant consults several sources and compares information
manually. The interview records no verified company or transaction as a case study.
The owner chose lookup and edition comparison as the main demo. The accountant's
reaction to a working dashboard remains to be collected. [Stakeholder interview](../INTERVIEW.md)

- The accountant can find the correct company unaided by name or CUI where verified.
  Multiple results remain selectable. EUID remains the candidate matching identity.
- The main page shows the available public profile and lets the visitor compare two
  published editions. Show edition dates and sources, added and removed records,
  changed and unchanged fields, previous and current values, and unavailable values.
  Snapshot absence describes the available export. The visitor can perform a
  preliminary partner check without comparing the source files manually.
- Search, selection, profile, comparison, filters and both exports work with a
  keyboard and on a narrow mobile screen. Verify visible focus, accessible labels,
  readable text, adequate contrast and access to essential controls.
- A historical query chooses the latest published ONRC edition dated on or before
  the request and returns its observed state, date and source. Earlier-than-coverage
  requests return unavailable. Entity absence is reported for the selected snapshot.
  Validity intervals describe observations. The query makes no claim about the
  exact legal state or the exact date of a change.

## Requirements traceability matrix

**Implemented** indicates repository evidence for the stated capability. **Partial**
indicates some required behavior exists. **Missing** means the deliverable or capability
is absent. **Unverified** means the required evidence has yet to be collected.
Prior synthetic verification establishes implementation behavior. The real-data,
performance and live acceptance rows track their own evidence.

### ETL, history and performance

| Requirement | Professor category | Existing implementation evidence | Status | Required next work | Verification or test evidence |
|---|---|---|---|---|---|
| Real, periodically updated public dataset with at least 100,000 rows | ETL | Two official ONRC editions with 100,000 source rows parsed in each bounded prefix. | Partial | Verify cadence, full source counts and eligible counts separately. | Catalog history and full-file reports. |
| Two real versions live with quality reports and changelog | P28 Definition of Done | Real editions identified and synthetic publication tested. | Missing | Validate, approve and publish both real editions in the live app. | Live IDs, source hashes, reconciled reports and changelog. |
| Scheduled ingestion | ETL | Manual CLI exists. | Missing | Schedule discovery and validated preparation. | Scheduled-job tests with changed and unchanged inputs. |
| Automatic source change detection using hash or ETag | ETL | Streaming SHA-256, transfer ETag capture and content identity. | Partial | Check sources automatically and avoid unnecessary unchanged downloads or new versions. | Changed-source, unchanged-source and retry tests. |
| Parse, validate, import and version snapshots | ETL | Streaming parser, staging and version records. | Implemented | Reuse for authorized real validation. | Existing parser and isolated MySQL tests. |
| Validate types, domains, uniqueness and references | ETL | Date and identity checks, classification, duplicate quarantine and foreign keys. | Partial | Define applicable canonical field and reference rules and complete coverage. | Fixtures for valid values and each failure class. |
| Idempotent ingestion | ETL | Identical input reuses the version. Concurrent ingestion is tested. | Implemented | Verify against authorized real editions. | Stable version ID, totals and report after a repeat. |
| Per-run quality reports, including previous-version anomalies | ETL | Reports reconcile outcomes, reasons, projected nulls and legal-form distributions. M2.1 provides advisory comparisons. | Partial | Cover individual run outcomes, missing values per required column and automatic comparison with the previous version. | Reconciliation, failure, reuse, distribution and anomaly cases. |
| Failed validation prevents publication | ETL | Approval seal, failed-input tests and rollback tests. | Implemented | Reuse the gate during scheduling and schema review. | Failed input leaves current version intact. |
| Store each version's source schema and canonical mapping | ETL and twist | Schema hash and profile stored. Header and mapping defined in code. | Partial | Persist inspectable schema and explicit mapping artifacts for each version. | Retrieve and compare artifacts for two versions. |
| Batch and index ingestion of at least 100,000 rows | ETL and performance | Batches of 1,000, staging index, version/entity key and 100,001-row synthetic verification. | Partial | Measure real throughput and validate indexes for actual queries. | Batch timings, real counts and query plans. |
| Detect renamed or added columns and changed separator or encoding | Twist | Strict profile detects drift through mismatch and rejection tests. | Partial | Identify, classify and display the actual schema changes. | Rename, addition, encoding and separator cases. |
| Block publication, propose mappings and require curator approval | Twist and P28 Definition of Done | Drift blocks publication. Curator mapping workflow is documented. | Partial | Add supported suggestions, corrections, explicit mapping approval and revalidation. | Simulated drift blocks publication, proposes a mapping and preserves older editions. Include an ambiguous required field. |
| Compute dataset differences in SQL | History and performance | MySQL computes counts and `Pipeline.diff_details()` streams each change category with changed fields and previous/current values. | Implemented | Expose detail results through approved API/dashboard work. | Synthetic MySQL regression coverage and opt-in benchmark tooling cover detailed diffs; real ONRC performance remains unverified pending Q-005. |
| Preserve old published versions unchanged and queryable | History | Immutable published versions remain available to the ETL diff. | Implemented | Expose prior versions through approved readers. | Prior version remains intact and queryable after later publication. |
| Validity intervals and entity state at a requested date | History and API | Snapshots carry version IDs and edition dates. | Missing | Add observed validity intervals and the as-of query. | Exact date, between editions, before first edition, and absent entity cases. |
| Real SQL diff on at least 100,000 records in under 30 seconds | Performance and P28 Definition of Done | Q-010 records the [approved real benchmark protocol](M2.1-BENCHMARK.md#protocol-aprobat-pentru-diff-ul-sql-pe-date-reale). | Unverified | After Q-005 authorization, validate and publish two real editions with at least 100,000 accepted records each, then measure the complete SQL diff. | Version IDs, input counts, match counts, environment, `EXPLAIN ANALYZE`, measured run times and reproducible command. |

### REST API, roles and security

| Requirement | Professor category | Existing implementation evidence | Status | Required next work | Verification or test evidence |
|---|---|---|---|---|---|
| REST endpoints documented with OpenAPI | API and P28 Definition of Done | OpenAPI documents health endpoints. | Partial | Document business endpoints. | OpenAPI and business API integration checks. |
| Filtering, sorting and cursor pagination | API | Published rows already carry filterable fields. | Missing | Add validated filters, supported sort keys and stable cursors. | Stable multi-page ordering without duplicates or gaps. |
| Grouped count, sum and average | API | Company rows and quality counters exist. | Missing | Implement the D-014 aggregates. | Known totals, null versus zero, and deduplication tests. |
| Dataset version selection | API | ETL diff accepts explicit published version IDs. | Partial | Expose selected versions in REST and use consistent defaults. | Explicit, latest and unpublished version cases. |
| Dataset changelogs and historical entity endpoints | API | ETL lineage and diff counts exist. | Partial | Expose lineage, changes and observed historical state through REST. | Compare two editions and query historical state by date. |
| API keys, rate limits and quotas | API and P28 Definition of Done | No business API key handling. | Missing | Add keys, limits and quotas. | Valid, invalid, revoked, throttled and quota-exhausted key cases. |
| Response ETags and tested publication invalidation | API | ETag capture applies to source transfers. | Missing | Issue response validators and invalidate relevant cached latest-version responses on publication. | Conditional 304 before publication, fresh response after publication and stable pinned versions. |
| Visitor, API consumer, curator and administrator permissions | Roles | Manual ETL approval exists. Application roles are absent. | Missing | Enforce D-011 on shared query logic and on protected operations. | Allow/deny matrix, self-escalation denial and published-only public reads. |
| Securely hashed passwords and server-side authorization | General security | DB credential configuration exists. Application sign-in is absent. | Missing | Add protected accounts and authorize operations on the backend. | Password storage, sign-in, session and permission tests. |
| Input validation and SQL injection/XSS protection | General security | ETL input validation and SQLAlchemy queries exist. | Partial | Extend validation, safe query construction and safe rendering to new surfaces. | Defensive tests for implemented inputs and outputs. |

### Dashboard and evidence

| Requirement | Professor category | Existing implementation evidence | Status | Required next work | Verification or test evidence |
|---|---|---|---|---|---|
| Main page answers the documented real user's question | Dashboard and P28 Definition of Done | Stakeholder interview exists. React entry renders no UI. | Missing | Build same-page lookup, profile and two-edition comparison according to the approved mock. | Unaided end-to-end user walkthrough with actual feedback. |
| Interactive charts and filters | Dashboard | No visual UI. | Missing | Add charts and verified filters. | Interaction checks against known outcomes. |
| Persistent saved visualizations with stable, shareable URLs | Dashboard and P28 Definition of Done | No saved visualization store. | Missing | Save filters, chart config and pinned versions with authorized writes. | Same public result after restart and later publication. |
| CSV and XLSX exports of all selected data | Dashboard | No export paths. | Missing | Export every matching row or group across pages. Preserve sort, scope and unavailable values. | Format parity, multi-page selection, missing values and grouped results. |
| Compare two editions with added, removed and modified rows and field-level old/new values | Dashboard | SQL category and field counts exist. | Partial | Expose row details, unchanged records, prior/current values and sources. Reuse those details in exports. | Fixtures cover all categories, unavailable values and matching exports. |
| Responsive, keyboard-accessible interface | General | Design guardrails exist. UI absent. | Missing | Approve the mock and implement the full keyboard/mobile workflow. | Keyboard, visible focus, labels, contrast and narrow-screen checks. |
| Document source, license, update frequency, data dictionary and limitations | P28 documentation | DATA.md and source notes contain provenance, attribution, samples, header and limitations. | Partial | Complete verified cadence and the canonical data dictionary. | Documentation checked against metadata and mapping. |
| Record real data problems in DATA.md | P28 documentation | Samples document missing keys, duplicates, CUI anomalies and unusual quoting. | Implemented | Add authorized full-file findings. | Existing sample evidence and future reconciled reports. |
| Preserve real interview and record actual demo feedback | P28 documentation and Definition of Done | Historical summary committed. Feedback is pending. | Partial | Have the accountant try the working workflow and record the reaction. | Dated, actual stakeholder feedback. |

### General submission requirements

| Requirement | Professor category | Existing implementation evidence | Status | Required next work | Verification or test evidence |
|---|---|---|---|---|---|
| Graffino Agentic Code Setup and valid ledger | General workflow | Setup present. Read-only ledger lint passed during the audit. | Implemented | Maintain ledger and review gates. | Ledger lint on final revision. |
| At least eight approved decisions | General workflow | Eight baseline decisions and seven approved Section C additions. | Implemented | Preserve decision history as plans evolve. | Approved ledger entries and audit above. |
| Documented backend API and C- contracts | General documentation | C-001 health and C-002 ETL boundaries. | Partial | Add the business API contracts and identify consumers. | Contract review, OpenAPI and endpoint tests. |
| Relational database with at least six related tables, versioned migrations and real data | General data | MySQL and Alembic with five related ETL tables. Alembic bookkeeping is separate. | Partial | Add tables required by approved features and load authorized real data. | Migrations, foreign keys and live record evidence. |
| Docker Compose for all required local application services | General infrastructure | DB, migrations, API, ETL tooling and frontend build. | Partial | Provide runnable frontend and scheduled ETL for full local development. | Compose startup, scheduled job and persistence checks. |
| At least ten meaningful automated tests, four for business rules or the twist | General testing | M2 verification recorded 46 passes. Business cases include quarantine, idempotency, publication, drift and SQL diff. | Implemented | Extend verification for remaining milestones. | M2 record and final CI evidence. |
| GitHub Actions runs tests and ledger-lint.py | General CI | CI invokes the shared verifier. Prior M2 success is documented. | Implemented | Run the complete suite for the submission revision. | Green CI run tied to final commit. |
| Public HTTPS deployment | General deployment | Local API binds to loopback. | Missing | Select hosting, obtain authorization and deploy the complete app. | Public HTTPS URL, live workflow and persistence evidence. |
| README, architecture docs, .env.example and SUBMISSION.md | General documentation | First three files exist. SUBMISSION.md is absent. | Partial | Update final setup and architecture evidence and prepare SUBMISSION.md. | Review documented install and final evidence links. |
| At least ten genuine AI_LOG.md entries | General workflow | One approved Section C entry. | Partial | Record actual work sessions and outcomes as they occur. | Ten dated, substantive entries. |
| At least 25 meaningful commits on at least eight distinct days | General workflow | Six commits on three author dates on the audited main branch. | Partial | Record meaningful authorized changes over real working days. | Final main history and distinct author dates. |
| Final 3–5 minute demonstration and evidence-based Definition of Done | General submission | Checkpoint and this matrix track the evidence gaps. | Partial | Record the working demo and tie each final claim to evidence. | Timed video, live URL, CI, measured diff and actual user feedback. |

Baseline implementation references are for awareness only.
[Data evidence](../DATA.md) · [ETL guide](M2-ETL.md) · [M2 verification](M2-VERIFICATION.md)
· [SQL diff](../backend/app/etl/diff.py) · [Architecture](agents/ARCHITECTURE.md)
· [Contracts](agents/CONTRACTS.md) · [CI](../.github/workflows/ci.yml)
· [Synthetic benchmark protocol](M2.1-BENCHMARK.md)

## Roadmap

M1 provides the Docker, FastAPI, MySQL, migrations, React tooling and CI foundation.
M2 provides versioned ETL, guarded publication and SQL diffs with synthetic
verification. M2.1 adds advisory quality comparisons and schema-drift coverage.
Reuse these implementations and tests. Each future implementation unit follows the
repository's Graffino plan, approval, tests-first build, verification and review.

| Order | Milestone and dependencies | Completion evidence |
|---|---|---|
| 1 | **Lab 1 D.** After explicit approval to start, propose tokens, register DS- screens, and obtain approval of the main dashboard Figma version and matching mock. | Approved frame, specific version, mock, tokens and review states. |
| 2 | **Lab 1 E–G first unit.** After design and plan approval, extend the existing SQL diff to return change categories and previous/current fields for published editions. Review before any merge. | Focused real-MySQL tests with synthetic data and a reviewed change. |
| 3 | **ETL and curator workflow.** Plan small units for source checks, run reports, explicit schemas and mappings, then curator review and publication. Verify cadence before choosing an interval. | Scheduled-change and simulated-drift tests. Existing atomic publication and previous editions are preserved. |
| 4 | **History and API.** Add observed validity intervals and as-of queries. Add published lookup, filters, cursor pagination, aggregates and changelog. Add privileged access, API keys, limits and cache invalidation in dependent units. | Approved C- contracts and focused query, access and caching tests. |
| 5 | **Dashboard.** After approval of each design, connect the main workflow, then charts, saved links and exports to approved published data routes. | Keyboard and mobile review, persistent links and format parity. |
| 6 | **Real data, benchmark and deployment.** Full-file validation can proceed once separately authorized in an isolated environment. Keep source totals, eligible rows per edition and benchmark size separate. Validate, benchmark, approve hosting and publish two real editions in the HTTPS app. | Full-file reports, reproducible real diff under 30 seconds, live changelog, public HTTPS and persistence checks. |
| 7 | **Submission.** Run the accountant's demo, record actual feedback, verify all requirements, and assemble SUBMISSION.md and the 3–5 minute video. Log genuine sessions and track meaningful commit dates throughout. | Final evidence package tied to the submission revision. |

For hosting, evaluate a modest Linux Docker host with an HTTPS entry point, React
and FastAPI, persistent MySQL with recoverable backups, and scheduled ETL. This
would reuse the local architecture, with the database and application sharing a
host. Compare it with compatible container hosting based on cost, protected ETL
temporary storage, job support, persistence and measured resource needs. Hosting
remains Q-007 and requires explicit approval. [Docker production guidance](https://docs.docker.com/compose/how-tos/production/)

Full downloads, publication, infrastructure changes and Git actions follow their
separate authorization gates. [Open questions](agents/OPEN-QUESTIONS.md)
