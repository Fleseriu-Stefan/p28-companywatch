# AI log

## 2026-11-27 · PR #8 Section G remediation

The owner accepted all three specialist passes for PR #8 at
`345f2962b1a380da5d4c238ecf33d8bbcb5c886e` against
`750af84da07a0e4f682d5cb5724820ecec7043b9`. The initial GitHub Actions run
45829550271 passed on that head.

The terminal canonical-pointer regression now requires the injected pointer
change after hashing, verifies the uppercase pointer on an independent MySQL
connection, and expects the exact `retry_cleanup_not_allowed` error. The
original checks for the loading state, report, hash, attempt, and row counts
remain. The ETL guide now explains that a valid session and continued advisory
lock ownership are required to record `failed`. Disconnect or lock loss can
stop cleanup before the failure report is committed and leave the attempt
`loading` for M2.3B recovery.

The owner deferred both performance recommendations. Gate 2 (Q-013) will
measure purge lag for retry, successful finalization, failure cleanup, and
the terminal staging emptiness probe. Gate 4 will measure simultaneous
staging and prepared-row storage, undo footprint, and recovery headroom.
Q-005, Q-013, and Q-014 remain investigating, PATTERN-003 remains a
candidate, and Gates 2–4 and real-data validation remain pending.

The first focused invocation stopped at Ruff E501 before starting MySQL.
The wrapper verified cleanup of `companywatch-check-850f6b85e6bf6bf2`.
After splitting the long assertion across two lines, the approved wrapper
passed all 12 focused cases in 7.58 s with assertions enabled on
`companywatch-check-7d52f628a61591ea`. Ruff lint and format, ledger lint,
Git whitespace checks, and the focused invocation's Compose smoke checks
passed. The wrapper verified graceful MySQL exit 0 at all three shutdowns
and removal of the disposable containers, volume, network, and image tags.
Read-only metadata checks confirmed both protected volume ownership labels.
The full local suite was skipped for this test and documentation change.
The complete CI workflow must pass on the remediation head after push.

## 2026-11-26 · M2.3C Gate 1 test-first preparation

The owner approved the M2.3C plan and authorized Gate 1 only. After a fetch
and fast-forward-only pull, local main, its tracking ref, and the live remote
main all resolved to `750af84da07a0e4f682d5cb5724820ecec7043b9`. The build
uses the local branch `fix/m2-3c-etl-finalization`.

The ledger records the owner's 2026-11-26 confirmations for D-001,
D-003 through D-009, C-002, PATTERN-001 through PATTERN-003 for awareness,
and Q-003, Q-005, Q-008, Q-010, Q-013, and Q-014. Q-010 confirms the real
benchmark protocol only. The patterns remain candidates and Q-005, Q-013,
and Q-014 remain investigating.

Five new MySQL test functions cover 12 cases for bounded finalization and
failure cleanup, loading-state visibility, interruption and retry, terminal
commit acknowledgment, and terminal eligibility. An AST comparison confirmed
all 33 pre-existing test functions were preserved. Ruff lint and format checks
for the test file, ledger lint, and `git diff --check` passed.

The owner separately approved focused RED with the reviewed, temporary
graceful-shutdown wrapper (SHA-256
`ca3a987ba6b1a2f661ca7649be6b7bb4da73082ac2f2327bb0dc7112f4c66f18`).
With assertions enabled, focused collection matched all 12 expected cases
and pytest reported 12 failed and 0 passed in 3.44 s. Ten failures
demonstrated the baseline's whole-version deletes, missing batch interruption
boundaries, or missing terminal revalidation. The two uncertain-commit cases
reported `DID NOT RAISE ETLError`. Those results do not establish that the
injected commit fault reached the terminal transaction and are not accepted
as RED evidence. They need a test-setup diagnosis before implementation.

The wrapper verified a graceful MySQL exit of 0 for
`companywatch-check-89315e63a8500cb2` and confirmed that its containers,
volume, network, and image tags were removed. Both protected volumes retained
their expected ownership labels. The ETL service and repository verifier
still match the baseline. GREEN, the complete verifier, October-scale
synthetic validation, and real SQL diff performance remain pending.

### M2.3C Gate 1 · corrected terminal-commit RED

The owner authorized a test-only correction for the two unverified cases.
The baseline transaction in `Pipeline._ingest` hashes the prepared rows
and writes version `review` and attempt `ready` together in the
`record_review` block. The original hook compared the raw PyMySQL connection
with the pool proxy passed to SQLAlchemy's `do_commit`, so the injected fault
never ran. The corrected test confirms that both writes use the same
transaction, matches the pool proxy, and verifies the actual rollback or
commit on an independent MySQL session before raising the simulated error.
All 33 original test functions and the other 10 Gate 1 cases were preserved.

The same approved wrapper selected all 12 focused nodes. Pytest reported
12 failed and 0 passed in 3.48 s. The previous ten failures reproduced.
Both corrected cases reached `commit_transaction` with the injected code
1205 and verified exactly one fault. The observer saw version/attempt
`loading`/`loading` after rollback and `review`/`ready` after commit.
Each observation showed zero staging rows and one prepared row. After
the fault, baseline failure cleanup attempted two deletes and two updates.
The final observer saw `failed`/`failed` and zero prepared rows in both
cases. Both corrected failures now demonstrate a baseline defect.

Ruff lint and format, ledger lint, and `git diff --check` passed. The
wrapper verified MySQL exit 0 for `companywatch-check-24aa9e8da407c0b0`
and confirmed removal of its containers, volume, network, and image tags.
Both protected volumes retained their ownership labels in the read-only
metadata checks. The application service, repository verifier, and
temporary wrapper were unchanged. Implementation and GREEN await approval.

### M2.3C Gate 1 · bounded finalization BUILD

The owner accepted the 12 genuine RED cases and approved Gate 1 implementation
on `fix/m2-3c-etl-finalization` from `750af84da07a0e4f682d5cb5724820ecec7043b9`.
The service now shares the existing indexed cleanup loop across retry,
finalization, and failure. Finalization deletes only staging. Recognized
failures capture the existing aggregate failure report before draining staging
and prepared rows. Each committed delete is capped at 1,000 rows. Each batch
and terminal transaction uses the advisory-lock session and checks the
canonical publication pointer, loading version, and active loading attempt
in that order.

The complete report, its hashes, and the version and attempt states become
visible in one terminal transaction. The ingest hash stream checks the
prepared count outside the shared publication pointer lock. The terminal
transaction checks the expected presence or absence of rows in both tables.
An interrupted cleanup leaves committed batches drained and lets a successor
recover the remainder. A terminal commit error stops further writes and
discards the session when it is still valid. The two fault cases verified
that the successor rebuilds if the terminal transaction rolled back and reuses
the intact version if MySQL committed it.

The diagnostics mock now returns loading states and empty cleanup results to
exercise the new checks. This mechanical fixture change preserves every
original assertion and exception expectation. All 33 original integration
test functions and the approved RED case assertions were preserved. The
initial Ruff pass identified E501 and B007 in the service, and a later format
check identified a blank line in the mock fixture. These were corrected before
verification.

- Focused GREEN exited 0 with 12 passes in 5.24 s on
  `companywatch-check-d8be090bb1d3793e`. The focused invocation also passed
  the non-integration suite, baseline migration test, and Compose smoke checks.
- The full verifier exited 0 on `companywatch-check-cb499531c9ac548e`.
  It passed 74 non-integration tests in 3.58 s, the historical baseline
  migration test in 0.99 s, and 54 additional MySQL integration tests in
  33.04 s. The existing opt-in two-edition volume test was skipped by its marker.
  Docker builds, Ruff lint and format, frontend lint/typecheck/build, migration
  gates, raw tmpfs, API checks, outage recovery, and persistence passed.
- Both runs used the approved wrapper with assertions enabled and its SHA-256
  checked before execution. The wrapper verified MySQL exit 0 at all three
  shutdowns in each project and verified no project containers, volume, network,
  or image tags remained. Read-only metadata checks confirmed the expected
  ownership labels on both protected volumes.
- Ledger lint, Git whitespace and ignore checks, changed documentation links,
  and skill and agent frontmatter passed.

The ingest read timeout remains 120 s. Full-range aggregation, quarantine,
prepared-row copy, and hashing remain scale-sensitive. Q-005, Q-013, and Q-014
remain investigating and PATTERN-003 remains a candidate. Gates 2–4,
October-scale synthetic validation, and real SQL diff performance remain pending.
[ETL lifecycle documentation](docs/M2-ETL.md#m23c--finalizare-și-curățare-la-eșec)

## 2026-11-25 · PR #7 Section G specialist review and remediation

Three independent specialists reviewed PR #7 at `dd5faac0`. The Security
Engineer found that Python equality could miss a case-equivalent MySQL
publication pointer and that the protection fixture did not exercise a
non-null approval seal on a historical published version. The SEO and GEO
review found no changed visitor-facing functionality. It identified an
overbroad failure description in the ETL guide and the missing second-attempt
reference in Q-005. The owner approved those corrections and deferred the
Performance Specialist's findings to the M2.3C evaluation.

Test first: both UUID columns used `utf8mb4_0900_ai_ci` on fresh synthetic
MySQL. The old code accepted an uppercase pointer to a lowercase version
in retry preparation and within a batch. Both guard tests failed with
`DID NOT RAISE ETLError`. The focused RED run recorded 2 failed and 11
passed in 2.54 s. The two sealed non-current cases passed on the original
code and now guard real synthetic approval seals and historical prepared rows.
The focused GREEN run recorded 13 passed in 2.58 s on a different disposable
MySQL project.

The shared pointer query now resolves the stored reference to the canonical
version primary key using MySQL comparison. Both guard sites use this
result while retaining the existing lock order, transaction boundaries and
independent version-state checks. The new assertions compare rows, metadata,
seals and the pointer before and after the attempted retry. The ETL guide
now distinguishes errors in retry cleanup from failures after parsing begins.
Q-005 links to the M2.3A diagnosis and remains investigating. Its previous
confirmation date was removed under the edited-entry convention.

The complete verifier exited 0 with assertions enabled: 74 non-integration
tests passed in 3.63 s, the baseline migration test passed in 0.97 s, and 42
remaining MySQL integration tests passed in 25.78 s. The existing opt-in
two-edition volume test was skipped by its marker. Ruff lint and format,
Docker builds, frontend checks, migration gates, protected tmpfs, API outage
and recovery, and persistence passed. Ledger lint and `git diff --check`
passed. The focused runs reused the guarded runner with the added tests and
the PR head check. The full run reused the temporary graceful-shutdown
wrapper. The runners verified disposable ownership and required MySQL exit 0
before teardown. Docker inspection found no remaining resources for the
three test projects. Both preserved volumes retained their ownership labels.

The deferred index scan and pointer lock findings are recorded as Q-013 and
Q-014 for M2.3C evaluation before another full real-data retry. Long-running
read views may delay purge and make later batches revisit delete-marked
index entries. Idempotent reuse may also hold the shared publication pointer
lock while waiting on a version row held by approval, delaying publication of
an unrelated version. Neither optimization is implemented here.
PATTERN-003 remains candidate-only and real SQL diff performance remains
unverified.

## 2026-11-25 · M2.3A diagnosis and M2.3B retry cleanup

The owner approved the isolated diagnosis, then approved M2.3B separately.
The October retry lost its connection in `prepare_attempt` after 120,067 ms
with driver code 2013. The retained Docker events show SIGTERM followed by
SIGKILL 3.02 seconds later. After authorized InnoDB recovery, the isolated
database still showed Alembic `0002_etl`, the expected October source hash, one
`loading` version and one `loading` attempt, 4,229,451 staging rows, zero prepared
rows, absent seals and a null publication pointer. The SQL report column was
non-NULL and its JSON content was not inspected. There were no active
transactions or lock waits when sampled. The diagnostic DB later exited 0
after SIGTERM. The single large staging DELETE remains a hypothesis because
the old log grouped multiple SQL statements under one operation name.

Test first: the corrected three-test run gave 3 expected failures in 0.97 s.
The original code deleted all 2,501 staged rows in one statement, reached
parsing before a second retry batch, and logged a DELETE failure only as
`prepare_attempt`. The expanded RED run gave 6 failed and 3 passed in 1.86 s
across six test functions and four publication-state cases. The new failures
covered repeated interruption, connection loss during cleanup and a loading
version referenced by the publication pointer. Review, approved and published
cases already passed. Earlier test setup issues were a missing parenthesis,
a hook that caught the later staging delete, and shared synthetic version
identities. The corrected RED runs used separate synthetic identities and
the interruption hook observed committed rows from another connection.

M2.3B creates the loading attempt before cleanup and holds the same advisory
lock across transactions. Each transaction rechecks lock ownership and
locks the publication pointer and target version in publication order.
It reads at most 1,000 keys scoped to the target and commits one DELETE for
those keys. Empty lookups for both tables precede parsing on a retry.
Retry preparation stays outside legacy failure cleanup. The logs distinguish
statement and transaction errors without recording SQL parameters. The
focused GREEN run gave 9 passed in 1.95 s. The B023 lint fix bound the expected
row count at callback creation. The first full verifier run passed Ruff and
stopped at 72 passed and 2 failed in the non-integration suite. Two staging
diagnostic cases returned `retry_cleanup_not_allowed` because the mock used a
version ID different from the generated fresh-ingest ID. The test setup now
returns deterministic version and attempt IDs so those cases reach their
original staging failure. Assertions were preserved.

On isolated MySQL 8.4.13, three interleaved synthetic versions held 180,003
staging rows. Cleanup of the target removed 60,001 staging rows in 61 committed
batches (median 27.64 ms, P95 32.46 ms, max 47.35 ms) and 8,001 prepared rows
in 9 committed batches (median 20.20 ms, P95 and max 25.48 ms). Batch sizes
ranged from 1 to 1,000. Wall time from the first cleanup transaction to
parsing was 1,879.00 ms, including 26.69 ms of plan capture. P95 uses nearest
rank. The SELECT plans used a covering staging version index and the covering
prepared primary key. Plain EXPLAIN showed primary-key range access for both
sampled DELETEs. Before and after fingerprints matched for both unrelated
versions' staging, prepared data, metadata, seals and the publication pointer.

The full verifier finished with exit 0 and Python assertions enabled. It ran
`scripts/verify.py` through a temporary wrapper that sends SIGTERM and requires
MySQL exit 0 before Compose teardown. It recorded 74 non-integration passes
in 3.46 s, one baseline migration pass in 0.97 s, and 38 further MySQL
integration passes in 24.99 s. The existing opt-in two-edition volume test
was skipped by its own marker. Both Ruff lint checks passed. Ruff format checked
35 backend files and one verifier script. Docker builds, ignore coverage,
frontend lint, type checking and build, offline migration SQL, migration
gates, ETL metadata and protected tmpfs, API outage and recovery, and
persistence checks passed. Ledger lint and Git whitespace checks passed.
MySQL exited 0 at each of the three stops in the final verifier run. Docker
inspection after the run found no disposable containers, volumes, networks,
or image tags for the verified projects. Both preserved volumes retained
their expected Docker ownership labels.

The measurement supports 1,000 rows per transaction on this fixture. The
full October scale, final staging and failure cleanup after parsing, other
large ETL operations, and the default two-second read timeout during approval
and publication remain separate work. Q-005 remains investigating and real
SQL diff performance remains unverified. [ETL recovery guide](docs/M2-ETL.md).

## 2026-11-25 · PR #6 Section G specialist review fix

The independent Performance Specialist and SEO/GEO Expert found no actionable
issues in PR #6. The Security Engineer found a P1 integration-test isolation
regression: the new `ingest_engine` fixture and the standalone timeout test could
bypass the shared `engine` fixture's development-database guard. In a manually
selected integration test, the 100,001-row synthetic test could then ingest and
publish against an unsafe configured database. The owner approved this focused
review fix, without authorizing a commit, push, merge, real ingestion or publication.

Test first: added a mock-only regression for an unsafe database name and an unsafe
Compose project name. It replaces engine creation with a mock, so neither case
contacts a database. `docker build --pull=false --tag
companywatch-m2-2-isolation:red ./backend` succeeded; `docker run --rm --network
none companywatch-m2-2-isolation:red pytest -q --tb=short
tests/test_etl_test_isolation.py` produced the expected RED result: both cases
failed with `DID NOT RAISE Failed`, proving the ingest fixture accepted the unsafe
settings. No connection was opened.

The correction extracts the existing guard into `isolated_test_settings()` in
`backend/tests/conftest.py`, returning the exact checked settings object. Both the
default and 120-second ingest engines use that object; the standalone read-timeout
test now requests the guarded ingest fixture. The duplicate-disconnect regression's
separate ingest engine also uses the same guard. No application code, ETL behavior,
existing assertion or timeout value changed. A rebuilt network-disabled image ran
the focused isolation, engine-timeout and CLI-timeout tests: 10 passed in 0.55 s.

The first `python3 scripts/verify.py` run stopped at Ruff lint because one existing
integration test still used `Settings` after its import was removed. The second
stopped at Ruff format on the new test's function signature. Both stopped before
MySQL startup, and their fresh verification projects were cleaned up. After those
mechanical corrections, `docker run --rm --network none
companywatch-m2-2-isolation:final ruff check .` returned `All checks passed!` and
`ruff format --check .` reported 35 files formatted. The final
`python3 scripts/verify.py` used fresh project
`companywatch-check-60f4ec7ccdfec73d`, verified its disposable configuration
and database-volume ownership, and exited 0 with `M1/M2 verification passed`:
74 non-integration passes, 1 baseline MySQL pass, 29 other MySQL integration
passes, and 1 opt-in volume test skipped. Frontend lint/typecheck/build, protected
tmpfs, startup gates, outage/recovery and persistence checks passed. The verifier
checked the volume mount and ownership before removing only its own resources.
The development and retained benchmark volumes were not selected or modified.
`python3 docs/agents/tools/ledger-lint.py` returned `✓ ledger ok`, and
`git diff --check` passed. Q-005 and real-data validation remain open.

## 2026-11-25 · M2.2 ETL read-timeout reliability build

The owner approved the focused M2.2 plan and explicitly authorized this build,
but not another ONRC download, real ingestion, approval, publication, diff
benchmark, commit, push, or merge. D-001, D-003–D-009, C-001/C-002 and
Q-005/Q-010 were confirmed; Q-005 remains investigating. PATTERN-001/002
remain candidate-only. `git fetch --all --prune` and `git pull --ff-only`
succeeded (`Already up to date`); the clean main revision was
`50c2be09a384d05f6c96c7c66525532631ac9f6f`. Created branch
`fix/m2-2-etl-read-timeout` from that revision.

The isolated October diagnostic had staged 4,229,451 rows before
`count_duplicate_groups` lost its connection after 2005.2 ms with driver code
2013. MySQL remained healthy; the version and attempt stayed `loading`, no
company rows were prepared, and the publication pointer remained NULL. A
separate read-only aggregation under a 120 s session limit returned 4,713
duplicate groups in 23.16 s wall time, including client startup. The existing
index was used for a covering range scan, followed by a temporary table. The
measurement exceeds the old 2 s PyMySQL read timeout; it is not a completed
quality report or a real SQL diff measurement.

Tests were written before the implementation. Commands and outcomes:

- `docker build --pull=false --tag companywatch-m2-2-tests:red ./backend`
  succeeded. `docker run --rm --network none companywatch-m2-2-tests:red pytest
  -q tests/test_db_timeout.py tests/test_etl_cli_timeout.py` first produced
  6 failures and 2 passes. Four failures were a non-serializable test mock;
  corrected that setup without changing assertions.
- Rebuilt the red image with the same command. `docker run --rm --network none
  companywatch-m2-2-tests:red pytest -q --tb=short tests/test_db_timeout.py
  tests/test_etl_cli_timeout.py` then produced the intended 2 failures and
  6 passes: the engine rejected `read_timeout`, and ingest did not select 120 s.
- Added a keyword-only engine read timeout with a 2 s default and passed 120 s
  only for `etl ingest`. Connect, write and pool timeouts remain 2 s; other
  commands and API readiness use the default. `docker build --pull=false
  --tag companywatch-m2-2-tests:green ./backend` succeeded; `docker run
  --rm --network none companywatch-m2-2-tests:green pytest -q --tb=short
  tests/test_db_timeout.py tests/test_etl_cli_timeout.py` returned
  8 passes in 0.27 s.
- `docker run --rm --network none companywatch-m2-2-tests:green ruff check .`
  first reported three E501 lines, and `docker run --rm --network none
  companywatch-m2-2-tests:green ruff format --check .` reported one unformatted
  integration test. Adjusted only line wrapping; no assertions changed.
- `python3 docs/agents/tools/ledger-lint.py --fix` and then without `--fix`
  each returned `✓ ledger ok`. `python3 scripts/verify.py` first used a fresh
  `companywatch-check-b5bd69d002c92635` project. Unit, Ruff and frontend
  checks passed; MySQL integration had 28 passes, 1 skip and 1 failure. The
  existing 100,001-row synthetic test used the default 2 s engine directly,
  and `copy_prepared_rows` disconnected after 2001.7 ms. The verifier proved
  ownership before removing its own test volume.
- Changed only that existing test's engine setup to the ingest-configured 120 s
  engine, preserving every assertion. A second `python3 scripts/verify.py`
  used fresh `companywatch-check-fe869b80d06462f1` resources and exited 0:
  72 non-integration passes; 1 baseline MySQL pass; 29 other MySQL integration
  passes and 1 opt-in volume skip. Ruff, frontend lint/typecheck/build,
  protected tmpfs, startup gates, outage/recovery and persistence checks
  passed. The verifier checked the mount and volume labels before cleanup and
  reported `M1/M2 verification passed`.

The new MySQL regressions cover an ingest-configured `SELECT SLEEP(3)`,
connection invalidation during duplicate-group aggregation, unchanged
publication, lock-protected rebuilding of an abandoned attempt, and 20,006
high-cardinality synthetic source rows with reconciled duplicate counts. No
ONRC data was downloaded or ingested in this build. The development volume
`companywatch_mysql_data` and retained benchmark volume
`companywatch-bench-3458f6c9bd974af5_mysql_data` were never selected for
tests or cleanup. Real validation, real publication and the under-30-second
real SQL diff remain unverified under Q-005. Final read-only `docker volume
inspect` confirmed both preserved volume names and project labels. Separate
`docker ps -a --filter label=com.docker.compose.project=...` and
`docker volume ls --filter label=com.docker.compose.project=...` checks found
no remaining resources in either temporary verification project. `git diff
--check` and ledger lint passed. No commit, push or merge was made.

## 2026-11-19 · Lab 1 Section G PR review correction

After independent review of PR #5, the owner approved one low-severity
requirements-matrix correction. The SQL diff row now records the implemented
`Pipeline.diff_details()` behavior and synthetic coverage, keeps API/dashboard
exposure as future work, and states that real ONRC performance remains
unverified and gated by Q-005.

## 2026-11-19 · Lab 1 Section G corrected prototype approval

The owner personally inspected the corrected Section D prototype in the browser
and approved the four selected fixes: preserving the unsubmitted search draft
when sorting changes, retaining the closed quality disclosure after review
confirmation, correcting state-message heading levels, and distinguishing ONRC
source editions in accessible link names. The owner also confirmed navigation,
Light/Dark themes and the corrected visual design. Correction evidence records
24 passed interaction checks and browser comparisons.

The correction approval is recorded in the [design registry](docs/design/registry.yaml)
and [design record](docs/design/DESIGN.md#corecții-aprobate-pentru-prototipul-etapei-d).
The original approved mock revision `2dc3bf2c6823ca733bc8d4b045a4dea241055106`,
D-002, Q-004, Figma references and all 40 reference screenshots remain historical
references. A Git revision for the corrected prototype can be recorded only after
an authorized commit; none is asserted here.

## 2026-11-19 · Lab 1 Section F benchmark UUID correction

The project owner approved the single correction identified in the pre-commit
audit. The benchmark argument parser now validates both version IDs and passes
canonical lowercase UUIDs to the existing runner. Invalid arguments exit with
status 2 and identify the affected argument before engine creation. The SQL,
timing, and JSON reporting code were preserved.

Wrote `tests/test_benchmark_etl_diff.py` before changing the runner and ran it
in the pinned backend image. The red run had 3 failures and 1 pass in 0.13 s.
The uppercase case raised `KeyError`, and invalid input reached the old runner
for either argument. The final focused run had 4 passes in 0.08 s, and Ruff
lint and format checks passed after a test line-length correction.

The isolated synthetic benchmark smoke check passed. The entry point rejected
synthetic editions, and the instrumentation captured four completed MySQL
statement events, separate Python timings, and the detail execution plan.
`python3 scripts/verify.py` exited 0 with 91 passes (64 non-integration,
1 baseline, and 26 other MySQL integration tests). It skipped the opt-in
two-edition volume test, which was outside this argument-handling correction.
The real benchmark remains unverified, with validation and publication gated
by Q-005. This correction was left unstaged for review.

## 2026-11-19 · Lab 1 Section F detailed SQL diff

Built the approved `Pipeline.diff_details()` stream on local branch
`feat/onrc-diff-details` from `5de33c3`. MySQL classifies the union by binary
EUID and compares the seven other retained fields with NULL-safe predicates.
The stream returns both value sides and the exact changed-field names.
The existing CLI, migration, ledger entries and approved Section D design
were preserved.

The first red run exposed an idempotent fixture collision in two tests.
After giving those fixtures distinct source IDs, all four focused tests
failed at the missing method. The two-edition volume test also failed at
the missing method before implementation. The green focused run passed
all five new integration tests. No pre-existing assertions changed.

The initial full verifier stopped on three Ruff E501 line-length errors.
After formatting fixes, `python3 scripts/verify.py` exited 0 with 60
non-integration tests, one historical baseline test and 26 other MySQL
integration tests passing. The verifier skipped the opt-in volume case,
which ran separately. Docker builds, Ruff, frontend checks, migration
and startup gates, outage recovery and persistence checks passed.

With separate approval, ran the reviewed
`bash /tmp/companywatch-section-f-volume.sh` once on MySQL 8.4.13. Each
synthetic edition had 100,001 accepted rows. The union had 100,002 rows
with 1 added, 1 removed, 1 modified and 99,999 unchanged. The single field
change was `name`. Totals reconciled and repeat ingestion reused both
version IDs. Pytest reported 1 passed in 34.07 s. Complete Python stream
consumption took 1.595 s with the unchanged two-second MySQL read timeout.
A separate `tracemalloc` pass measured a 473,044-byte Python allocation peak.
Synthetic `EXPLAIN ANALYZE` showed a streaming append finishing at 671 ms,
with edition scans and single-row lookups using the composite primary key
and no sort or materialization operator shown. The script removed the
owned test project resources.

The benchmark runner rejected synthetic editions at its entry point. A
separate synthetic instrumentation check verified four completed MySQL
statement events, separate Python timings and plan capture. Q-005 still
gates real validation and publication. Q-010 is answered for the protocol
only. Real ONRC performance remains unverified.
[Approved plan](docs/SECTION-E-PLAN.md) · [Reproduction procedure](docs/M2-ETL.md#verificarea-sintetică-de-volum).

## 2026-11-19 · Lab 1 Section E plan approval

The project owner explicitly approved the bounded `Pipeline.diff_details()`
implementation plan and every individual Knowledge used verdict. The approval
preserves the approved decisions and contracts, including clarified C-002,
the two candidate patterns, and the approved Section D design. Q-005 remains
investigating. Q-010 is answered for the procedure only. Real ONRC performance
remains unverified.

The owner required evidence for the existing two-second MySQL read timeout,
a reproducible two-edition volume check clearly distinguished from ordinary CI,
and prerequisites for starting and connecting to isolated benchmark MySQL.
These conditions are recorded in the approved plan. This session records the
approval only. Section F requires separate authorization.
[Approved Section E plan](docs/SECTION-E-PLAN.md).

## 2026-11-19 · Lab 1 Section E control decisions

The project owner resolved all three questions from the Section E control review.
They approved `Pipeline.diff_details()` as the first bounded implementation unit.
The existing CLI and its contracts stay intact. The internal service preserves
same-version and reversed-pair comparisons. The future API and dashboard will
enforce distinct chronological edition selection where the approved mock requires
it. React, API routes, exports, historical validity intervals, and deployment are
outside this unit. Implementation awaits a fresh Graffino plan and explicit approval.

The owner confirmed D-001 through D-015 and C-001, approved the C-002 wording
clarification, and confirmed both patterns as relevant candidates. Q-002 through
Q-004 retain their answered status. Q-010 records the approved protocol for the
complete real SQL diff and a separate Python stream measurement. Q-005 remains
investigating. Real validation, publication, and benchmark results remain pending.
The owner reported successful WSL checks with `docker version`,
`docker compose version`, and `docker run hello-world`. The application suite
has yet to be rerun after Docker recovery.
[Contract ledger](docs/agents/CONTRACTS.md#c-002--etl-snapshots-and-publication-boundary) · [Benchmark protocol](docs/M2.1-BENCHMARK.md#protocol-aprobat-pentru-diff-ul-sql-pe-date-reale).

## 2026-11-19 · Lab 1 Section D design approval

The project owner personally reviewed CompanyWatch Draft 1 in Figma and in the
HTML mockup, confirmed their visual equivalence, and explicitly approved all nine
screens under D-002. Codex recorded the approval against mockup revision
`2dc3bf2c6823ca733bc8d4b045a4dea241055106`, checked the hashes and dimensions of
all 40 Figma review frames, and answered Q-004 for the approved design scope.
[Design approval record](docs/design/DESIGN.md#etapa-d--registrul-onrc).

## 2026-11-19 · Lab 1 Section D Draft 1 review

The project owner selected the existing CompanyWatch Draft 1 with its original
sidebar and the refined Perspectivă, Stare and Temă controls. Codex verified the
nine mockup screens at 360, 768 and 1440 px in both themes and all five states.
The 40 existing Figma review frames were updated in place with the matching
Chromium captures. Image hashes and frame dimensions were checked. The design
registry remained at `draft` pending the owner's D-002 equivalence confirmation.
[Review package](docs/design/DESIGN.md#pachetul-aprobat-pentru-evaluarea-vizuală).

Git whitespace, JavaScript syntax and ledger lint checks passed. The application
verification suite stopped before its runtime checks because the Docker Desktop
Linux engine was unavailable.

## 2026-11-19 · Lab 1 Section C interview and decision audit

Codex inspected the CompanyWatch repository read-only, compared the committed
stakeholder interview with the ledger and checkpoint, and interviewed the project
owner one question at a time. The owner supplied the mandatory P28 and general
university scope and explicitly confirmed D-001 through D-008. The interview
defined the main demo workflow, observed history, access boundaries, saved
visualizations and export behavior. The owner approved the documentation changes
and D-009 through D-015. See the [requirements matrix and roadmap](docs/P28-REQUIREMENTS.md).

The read-only audit passed ledger lint. Runtime tests, the full ONRC import and
deployment were outside the session. The M1, M2 and M2.1 implementation and the
[historical interview](INTERVIEW.md) were preserved. Section D was pending approval.
