# AI log

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
