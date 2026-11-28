# Open questions — p28-companywatch

<!-- graffino-agentic:begin v1 -->
> Unknowns. Work that depends on an open question is out of scope until it is
> answered. Only the user answers; an agent never answers by guessing. An agent may
> write a `Proposed answer` the evidence supports; the question stays
> `investigating` until the user confirms it.
> Answered entries stay, with the answer and date, and usually become a D- or PATTERN-.
<!-- graffino-agentic:end -->

## Index
- Q-001 · What application purpose, users, requirements and domain terms are confirmed? · _investigating_
- Q-002 · Which application stack and Docker services should this project use? · _answered_
- Q-003 · Which install, build, run, test and lint/type-check commands should verify the application? · _answered_
- Q-004 · What UI, design tokens, viewport sizes and screenshot procedure are required? · _answered_
- Q-005 · Which public dataset and real versions can be approved? · _answered_
- Q-006 · What interview evidence and checkpoint rubric must be delivered? · _investigating_
- Q-007 · Where and how should the public deployment run? · _answered_
- Q-008 · Can the verified legal-entity subset be extended?
- Q-009 · How often should scheduled ETL check for ONRC updates?
- Q-010 · How should the real SQL diff benchmark be measured? · _answered_
- Q-011 · What API request limits and quotas should apply?
- Q-012 · Can the accountant supply a verified, anonymized example if needed?
- Q-013 · Does delayed InnoDB purge make retry batches revisit deleted index entries? · _deferred_
- Q-014 · Can idempotent ingest reuse avoid holding the publication pointer lock? · _deferred_

---

## Q-001 · What application purpose, users, requirements and domain terms are confirmed?
- **Status:** investigating
- **Blocks:** Claiming that the accountant has validated the main demo workflow.
- **Who answers:** Project owner.
- **Partial answer:** The [stakeholder interview](../../INTERVIEW.md) records a recurring problem: the accountant must consult several sources and compare information manually when checking a potential partner. The owner confirmed scope, roles and the proposed demo workflow in D-009, D-011 and D-015. The accountant has yet to validate this prioritization in a working demo.

## Q-002 · Which application stack and Docker services should this project use?
- **Status:** answered
- **Who answers:** Project owner.
- **Answer:** On 2026-11-17 the user approved D-003 and M1: React + TypeScript + Vite, FastAPI, MySQL, SQLAlchemy, PyMySQL, Alembic and Docker Compose. Services: db, migrate, api; tooling profiles: tests and frontend build. No frontend web server before Figma approval.

## Q-003 · Which install, build, run, test and lint/type-check commands should verify the application?
- **Status:** answered
- **Who answers:** Project owner.
- **Answer:** On 2026-11-17 the user approved D-004 and the M1 verification plan: Docker builds, Ruff, pytest unit and real-MySQL integration tests, frontend ESLint/type-check/build, ledger lint and Compose smoke checks. See ../../README.md for executable commands and scripts/verify.py for the complete check.
- **Confirmed:** 2026-11-27

## Q-004 · What UI, design tokens, viewport sizes and screenshot procedure are required?
- **Status:** answered
- **Who answers:** Project owner.
- **Answer:** On 2026-11-19 the project owner personally confirmed visual equivalence and approved all nine CompanyWatch Draft 1 screens under D-002. The approval applies to the screen designs, states and tokens represented in the pinned HTML mock and Figma review frames. Review the mock at 360, 768 and 1440 px in both themes, with the registered desktop and mobile Chromium captures as the visual references. Apply the documented keyboard and narrow-screen checks and agree on an application screenshot command in the implementation plan. [Design approval and review procedure](../design/DESIGN.md#etapa-d--registrul-onrc) · [Screen registry](../design/registry.yaml).

## Q-005 · Which public dataset and real versions can be approved?
- **Status:** answered
- **Who answers:** Project owner, after source investigation.
- **Answer:** Both OD_FIRME.CSV editions (19.10.2026 and 04.11.2026) passed full-file validation with the approved D-018 subset. The owner approved both quality reports and published the editions locally in order. October has 120,000 accepted EUIDs and November has 120,163. November is current. [Step B evidence](../../DATA.md#calitatea-edițiilor-publicate).
- **Confirmed:** 2026-11-28

## Q-006 · What interview evidence and checkpoint rubric must be delivered?
- **Status:** investigating
- **Blocks:** Final evidence of the accountant's reaction to the working dashboard.
- **Who answers:** Project owner.
- **Partial answer:** The [committed interview summary](../../INTERVIEW.md) records the real interview. The owner supplied the authoritative [P28 and general requirements](../P28-REQUIREMENTS.md) and approved the Section C audit. Preserve the summary. Add actual feedback after the accountant tries the working demo.

## Q-007 · Where and how should the public deployment run?
- **Status:** answered
- **Who answers:** Project owner.
- **Answer:** The owner selected Azure VM `companywatch-live` and `https://companywatch-sf.austriaeast.cloudapp.azure.com`. The initial deployment uses Docker Compose, Caddy HTTPS, and persistent MySQL restored from the local published database. The owner authorized generating and storing the database credentials in the VM's ignored mode-600 `.env.production`. Scheduled ETL and the remaining P28 features are later delivery units. [Deployment procedure](../DEPLOY.md).
- **Confirmed:** 2026-11-28

## Q-008 · Can the verified legal-entity subset be extended?
- **Status:** open
- **Blocks:** Expansion beyond the verified J + SRL/SA/SNC subset, not the approved M2 implementation.
- **Who answers:** Project owner after evidence of source coding.
- **Proposed answer:** Keep unknown forms and branches quarantined. Verify additional legal-form mappings before extending the profile; never infer a legal category only from initials. See ../ONRC-SOURCE.md.
- **Partial answer:** The owner confirmed the current classification. A low eligible count alone does not justify expanding it. Investigate another official edition first if Q-005 identifies a shortfall.
- **Confirmed:** 2026-11-26

## Q-009 · How often should scheduled ETL check for ONRC updates?
- **Status:** open
- **Blocks:** Final schedule interval. Scheduled ingestion and source change detection are mandatory.
- **Who answers:** Project owner after verifying the source cadence.
- **Proposed answer:** Match the verified publication cadence with the simplest configurable interval. Consider a daily check only if the cadence is unclear. Skip unnecessary downloads for unchanged sources and retain idempotent processing and guarded publication.

## Q-010 · How should the real SQL diff benchmark be measured?
- **Status:** answered
- **Who answers:** Project owner.
- **Answer:** On 2026-11-19 the owner approved timing the complete per-company SQL diff separately from Python result-stream consumption. Use two published real ONRC editions with at least 100,000 accepted legal-entity records each. Warm up, record at least three complete timed runs with an under-30-second SQL target, and preserve every timing, the `EXPLAIN ANALYZE` output, the environment and the reproducible command. [Approved benchmark protocol](../M2.1-BENCHMARK.md#protocol-aprobat-pentru-diff-ul-sql-pe-date-reale).
- **Evidence:** [Step B measurements for both published editions](../M2.1-BENCHMARK.md#rezultate-q-010--2026-10-19--2026-11-04).
- **Confirmed:** 2026-11-27

## Q-011 · What API request limits and quotas should apply?
- **Status:** open
- **Blocks:** Production limit values and quota windows.
- **Who answers:** Project owner after the applicable deployment is known.
- **Partial answer:** External API requests require valid keys, rate limits and quotas. Public dashboard routes need appropriate protections without visitor accounts. See D-011.

## Q-012 · Can the accountant supply a verified, anonymized example if needed?
- **Status:** open
- **Blocks:** A concrete case study only if later required.
- **Who answers:** Project owner with the accountant.
- **Partial answer:** The interview documented a recurring workflow and no verified company or transaction. Keep any later example anonymized and free of confidential client material.

## Q-013 · Does delayed InnoDB purge make retry batches revisit deleted index entries?
- **Status:** deferred
- **Deferral:** On 2026-11-28 the project owner closed M2.3C and deferred further investigation. This question no longer blocks a real-data retry.
- **Evidence:** The PR #7 performance review found that each limited batch starts at the beginning of the same version's index range. An older read view can delay purge, so later batches may revisit delete-marked entries while holding the shared publication pointer lock. The synthetic M2.3B timing did not exercise purge lag.
- **Previous proposal:** Hold a synthetic read view open and compare early and late batch plans, scan work, and time. Evaluate a seek cursor in existing index order, including nullable staging digests and the staging ID tie-breaker. Advance the cursor only after a successful commit.

## Q-014 · Can idempotent ingest reuse avoid holding the publication pointer lock?
- **Status:** deferred
- **Deferral:** On 2026-11-28 the project owner closed M2.3C and deferred further investigation. This question no longer blocks a real-data retry.
- **Evidence:** The PR #7 performance review found that ingest takes the shared pointer lock before establishing reuse. If approval holds version A's row lock while verifying its seal, reuse of A can wait with the pointer held and delay publication of version B.
- **Previous proposal:** Measure simultaneous approval of A, reuse of A, and publication of B with synthetic resources. Evaluate a reuse path without the pointer lock and a separate eligibility recheck for cleanup that preserves pointer-before-version ordering.
