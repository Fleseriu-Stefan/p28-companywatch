# AI log

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
