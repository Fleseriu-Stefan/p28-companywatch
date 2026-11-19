# CompanyWatch P28 · Lab 1 Section E · Approved plan

On 2026-11-19 the project owner explicitly approved the bounded
`Pipeline.diff_details()` implementation unit and all individual Knowledge
used verdicts, subject to the conditions below. The approval closes Section E.
Section F requires separate authorization. [Approval record](../AI_LOG.md#2026-11-19--lab-1-section-e-plan-approval).

## Size and approach

**M, one builder.** Reuse M2's published-version validation, EUID matching,
retained fields, and SQL comparison predicates. Add a context-managed detail
stream while keeping the existing aggregate path. Preserve the M1 Docker,
health, migration and frontend-tooling baseline, the M2 ETL lifecycle and
publication safeguards, and the M2.1 advisory quality comparison and schema
drift behavior. The existing implementations are cited for awareness.
[Existing SQL diff](../backend/app/etl/diff.py) · [P28 roadmap](P28-REQUIREMENTS.md#roadmap).

Python-side joins and comparisons would duplicate MySQL semantics and increase
client memory use. Feeding the aggregate CLI from detail rows would transfer
wide records for an operation that needs only totals. The proposed two-branch
SQL statement can use the existing key without a materialized key union, a
persisted diff, or new indexes.

## Files

| Action | Path | Planned change |
|---|---|---|
| Modify | `backend/app/etl/diff.py` | Share validation and comparison predicates. Add the detail statement, stream lifecycle and row mapping. |
| Modify | `backend/app/etl/service.py` | Add `Pipeline.diff_details(old_id, new_id)` with the existing synthetic opt-in. |
| Modify | `backend/tests/test_etl_database.py` | Add detailed diff integration cases and two-edition volume coverage using the existing large-edition scenario and helpers. Preserve all existing assertions. |
| Add | `backend/tests/benchmark_etl_diff.py` | Provide an opt-in benchmark module outside ordinary pytest collection and the ETL CLI. |
| Modify | `docs/M2-ETL.md` | Document the internal stream and reproducible volume and real benchmark commands, including isolated MySQL setup. |

The other C-002 consumer, `backend/app/etl/cli.py`, stays on `Pipeline.diff()`.
Keep its commands, arguments, JSON keys, error codes and exit behavior. Use the
existing models, migrations, Compose setup, verification runner and CI workflow.

## Internal result contract and SQL

Use `with pipeline.diff_details(old_id, new_id) as rows:`. Validate the pair on
entry. Yield one row per EUID in the union, in unspecified row order. Each row
supplies `euid`, `change_type`, `previous`, `current`, and `changed_fields`.
A present side contains all eight retained fields. An absent side is `None`.
Within a present side, a field with SQL NULL maps to Python `None`.

| Category | Previous | Current | Changed fields |
|---|---|---|---|
| Added | Absent | Present | Empty tuple |
| Removed | Present | Absent | Empty tuple |
| Modified | Present | Present | Every flagged name in `RETAINED` order |
| Unchanged | Present | Present | Empty tuple |

1. On the diff connection, look up the distinct input IDs. Missing or
   non-published input raises `published_versions_required`. A published
   synthetic snapshot requires explicit test opt-in and otherwise raises
   `synthetic_not_allowed`. Preserve this validation order. Older published
   snapshots remain eligible independently of the current pointer.
2. Left join the old snapshot to the new snapshot to obtain matched and removed
   rows. Left join in the other direction and retain only missing old EUIDs to
   obtain additions. Use a top-level `UNION ALL` without global ordering. Bind
   the version IDs and join the bare EUID columns under `utf8mb4_0900_bin`.
   The non-null primary key `(version_id, euid)` supports the edition lookup
   and guarantees at most one match per side.
3. Generate flags with the existing SQLAlchemy equivalent of
   `NOT (old.field <=> new.field)` for `cui`, `registration`, `name`,
   `legal_form`, `county`, `locality`, and `registration_date`. SQL classifies
   the row and emits both value projections and the seven flags. Python maps
   the flags to names and assembles the sides. Two NULLs are equal, NULL versus
   a value differs, and case-only changes survive binary collation. Leave
   EUID out of the flags. A changed EUID yields a removal and an addition
   even if CUI matches. Removal describes snapshot absence.
4. The first argument supplies previous values and the second supplies current
   values. A same-version pair is all unchanged. Reversing a pair swaps the
   sides and the added/removed categories. Matched categories and field names
   persist. Choosing distinct chronological editions belongs to future API/UI
   code.

## Tests and acceptance

Write tests first. Use isolated MySQL for integration. Keep existing tests and
their assertions, including CLI, health, migrations, publication, quality
comparison, and drift coverage.

| Behavior | Automated check in `backend/tests/test_etl_database.py` |
|---|---|
| Four categories and value sides | Publish small synthetic editions. Assert exact previous/current values, absence, one row per EUID, category, and field names. Include distinct EUIDs sharing a CUI. |
| NULL and case changes | Assert NULL-to-value, value-to-NULL, both NULLs, a case-only text change, and a multi-field change in canonical order. |
| Binary EUID and all seven predicates | Seed a storage-level synthetic fixture in isolated MySQL for values outside the parser profile, including case-only EUIDs and a matched EUID with changed registration. Assert removal/addition and all seven flags without changing the production parser or editing an existing published fixture. |
| Version rules and orientation | Cover missing and non-published IDs, synthetic without opt-in, a previously published snapshot, same-version, and reversed comparisons. Assert errors and directional values. |
| Aggregate parity | Tally the full stream and reconcile four category totals and all seven `by_field` values with `Pipeline.diff()`. The old count is removed plus matched, the new count is added plus matched, and the union is all four categories. A modified row can increment more than one field count. |
| Two 100,001-row editions | Generate A from indices 1–100,001. B removes 1, adds 100,002, and changes the name at 2. Ingest, approve, and publish each with 100,001 accepted rows using the existing synthetic test opt-in and full threshold. Consume incrementally and expect 1 added, 1 removed, 1 modified, 99,999 unchanged, and 100,002 union rows. Only `name` increments. Check reingestion reuses the original version ID. |
| Stream lifecycle | Verify full drain, early exit and consumer-error cleanup. Check that the cursor closes before pool return and the connection is usable or safely discarded. |

Run the ordinary `python3 scripts/verify.py` suite. Keep its existing CI
coverage. Make the additional full two-edition volume exercise explicitly
selectable and document the command and isolation preflight as a separate
check. Run it for Section F acceptance and report it separately from ordinary
CI. Measure the complete detail query with the existing two-second client
read timeout in isolated MySQL. Record whether it completes under that
configuration and record any failure with the environment and evidence. If
the timeout is incompatible, bring back a narrowly scoped proposal for
approval. Leave the application timeout settings as they are pending approval.

Use an unbuffered result and fixed-size fetch batches. Review memory use,
cursor close/drain behavior, and connection occupancy during slow consumption.
Inspect the full synthetic `EXPLAIN ANALYZE` for edition access, composite-key
lookups, actual versus estimated rows, loops, sorts, and materialization or
spills. Diagnose query-shape issues within the existing schema first. Any
physical design change needs its own evidence and approval.

## Real-data benchmark under Q-010

The build delivers the runner and documentation. Real execution requires
separate Q-005 authorization for validation and publication. Document Docker
and Compose prerequisites, credentials supplied through the approved private
mechanism, a dedicated project and volume, ownership checks, starting healthy
MySQL and running the opt-in migration, connection from the tool container
through Compose, and enabling and reading the required Performance Schema
instrumentation. Keep the development and legacy volumes outside this run.

After authorization, use two manually published real ONRC editions with at
least 100,000 accepted legal-entity rows each. Record IDs, edition dates, source
and accepted counts, shared EUIDs and union size. If an edition falls short,
return the evidence through Q-005 and follow the approved source-investigation
process. The planned invocation, after isolated setup, is:

```bash
docker compose -p "$BENCHMARK_PROJECT" run --rm --no-deps tests \
  python -m tests.benchmark_etl_diff "$OLD_VERSION" "$NEW_VERSION"
```

Use one complete warm-up and at least three complete timed runs in the same
configuration. Drain all rows with all categories, both value sets and all
flags, and reconcile totals each time. Record the completed data statement's
MySQL Performance Schema `TIMER_WAIT` in seconds, identified by connection/thread
and event. Missing, ambiguous, untimed or incomplete events invalidate the
sample. Separately measure elapsed Python time with a monotonic clock from
detail execution through the last mapped row. MySQL time can include server
result delivery waits. Keep the two measurements separate without subtracting
them. Use a finite benchmark-only read timeout that can observe a run at or
above the target. Capture `EXPLAIN ANALYZE` separately for the same SQL and pair.

Exclude preparation, ingestion, publication, query-plan execution, HTTP and
export serialization from the timed runs. Preserve the exact command and pair,
revision, MySQL version and image digest, environment, Docker limits, timeout
and instrumentation settings, plan, every timing and checked totals. Report
aggregate evidence only. Flag every SQL run at or above 30 seconds. The
professor's real performance criterion requires complete measured runs below
the target on real published data. Synthetic results, a count query, time to
first row and partial consumption do not establish that criterion.
[Approved benchmark protocol](M2.1-BENCHMARK.md#protocol-aprobat-pentru-diff-ul-sql-pe-date-reale).

## Design and separate units

`DS-CW-registru` needs both value sides and distinguishes missing values from
snapshot absence. `DS-CW-editii` needs the four change categories and edition
provenance. Future API and UI plans will supply provenance, distinct
chronological selection, validated filters and sort, stable cursors and
response contracts. Future visual builds must use the approved Draft 1 mock
pinned to `2dc3bf2c6823ca733bc8d4b045a4dea241055106`, including tokens, labels,
keyboard access, and states at 360, 768 and 1440 px in both themes.
[Approved design registry](design/registry.yaml) · [Design procedure](design/DESIGN.md#etapa-d--registrul-onrc).

This unit supports SQL-based diffs, natural-key matching, explanations by
field, synthetic edition-scale verification, and real benchmark
reproducibility. Separate plans cover scheduled source discovery and
hash/ETag changes, validation and quality reports, schema mapping and curator
review, observed validity intervals and as-of queries, published REST and
changelogs, authentication and authorization, API keys and limits, response
ETags, dashboard and grouped analytics, saved views, CSV/XLSX exports, real
publication, public HTTPS deployment and submission evidence. The latter
includes the accountant's demo feedback, complete source documentation,
CI/live evidence and video. [Requirements and roadmap](P28-REQUIREMENTS.md#roadmap).

## Sequencing and Git

After separate Section F authorization, start from the verified
`design/companywatch-etapa-d` checkout at `5de33c3`. Check status and sync,
verify the approved local documentation and guard against any other edits.
If the proposed branch name is unused, run
`git switch -c feat/onrc-diff-details 5de33c3` in that checkout. Confirm that
the local edits carried over intact, including the untracked plan. The new
branch starts without an upstream. Preserve the existing patch as the baseline
for the five pre-approval edits. The approved plan and new AI log entry are
additional local documentation. Stop on a divergent tip, unexpected edits or a
branch name collision before switching.

Invoke the repository's `$graffino-build` skill in Codex with this plan and
explicit Section F authorization. Implement tests first, run ordinary
verification and the dedicated volume check, inspect query plans, and report
all failures and skips with their reasons. Check documentation links,
frontmatter, ignore coverage and the final diff. Commit, push, merge and
deployment each require separate authorization.

## Knowledge used

The owner approved these individual verdicts on 2026-11-19. This record
preserves the existing ledger entries and their historical confirmation dates.
Candidate patterns were considered for awareness. The approved decisions
and contracts govern use of the existing verifier and publication workflow.
[Decisions](agents/DECISIONS.md) · [Contracts](agents/CONTRACTS.md) · [Patterns](agents/PATTERNS.md) · [Open questions](agents/OPEN-QUESTIONS.md).

| Entry | Status | Use in this plan | Approved verdict |
|---|---|---|---|
| D-001 | Approved | Docker for application servers, including isolated MySQL. | Confirm |
| D-002 | Approved | Future consumers follow the approved Figma version and local mock. | Confirm |
| D-003 | Approved | Existing stack and services. | Confirm |
| D-004 | Approved | Docker verifier, isolated MySQL and CI. | Confirm |
| D-005 | Approved | Real data, scale, snapshots and baseline acceptance. | Confirm |
| D-006 | Approved | Two development editions, with full validation required. | Confirm |
| D-007 | Approved | EUID, minimal legal-entity fields, quarantine and raw-data rules. | Confirm |
| D-008 | Approved | Immutable published snapshots, SQL comparisons and atomic publication. | Confirm |
| D-009 | Approved | Mandatory scope and preservation of M1, M2 and M2.1. | Confirm |
| D-010 | Approved | Future observed history and as-of queries. | Confirm |
| D-011 | Approved | Future reader and privileged access boundaries. | Confirm |
| D-012 | Approved | Future saved views pin exact versions and stable links. | Confirm |
| D-013 | Approved | Future schema review and publication gate. | Confirm |
| D-014 | Approved | Future grouped analytics and quality metric definitions. | Confirm |
| D-015 | Approved | Future same-page comparison and complete active-selection export. | Confirm |
| C-001 | Approved | Health and OpenAPI baseline. | Confirm |
| C-002 | Approved, clarified | Published-only comparison, binary EUID and NULL-safe fields. | Confirm approved clarification |
| PATTERN-001 | Candidate | Existing isolated Compose verifier, for awareness only. | Confirm as candidate |
| PATTERN-002 | Candidate | Existing immutable snapshot seals, for awareness only. | Confirm as candidate |
| Q-001 | Investigating | Accountant validation of the working demo is pending. | Confirm investigating |
| Q-002 | Answered | Stack and Docker selection. | Confirm recorded answer |
| Q-003 | Answered | Docker verification commands. | Confirm recorded answer |
| Q-004 | Answered | Draft 1 visual review procedure. | Confirm recorded answer |
| Q-005 | Investigating | Real validation, counts and publication require authorization. | Confirm investigating |
| Q-006 | Investigating | Working demo and stakeholder evidence are pending. | Confirm investigating |
| Q-007 | Open | Hosting and production configuration. | Confirm open |
| Q-008 | Open | Any expansion of the verified subset. | Confirm open |
| Q-009 | Open | Scheduled interval informed by source cadence. | Confirm open |
| Q-010 | Answered | Benchmark protocol only. Real timings are pending. | Confirm protocol |
| Q-011 | Open | External API limits and quota values. | Confirm open |
| Q-012 | Open | Verified anonymized example if later needed. | Confirm open |
| DS-CW-registru | Approved | Profile, previous/current values, and absence. | Confirm |
| DS-CW-editii | Approved | Categories and future chronology. | Confirm |
| DS-CW-istoric | Approved | Future observed history. | Confirm |
| DS-CW-analiza | Approved | Future grouped analytics and exports. | Confirm |
| DS-CW-vizualizari | Approved | Future saved visualizations. | Confirm |
| DS-CW-calitate | Approved | Future quality and ingestion interface. | Confirm |
| DS-CW-schema | Approved | Future curator mapping review. | Confirm |
| DS-CW-api | Approved | Future API and source documentation. | Confirm |
| DS-CW-acces | Approved | Future user, role and key administration. | Confirm |
| DS-CW-dashboard | Draft | Earlier draft reviewed for awareness. Draft 1 supplies the approved references. | Confirm draft status |

The context-managed result, unspecified row order, benchmark module and
proposed branch name are the approved implementation choices for this unit.
They define no public API contract.
