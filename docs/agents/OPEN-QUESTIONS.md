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
- Q-004 · What UI, design tokens, viewport sizes and screenshot procedure are required?
- Q-005 · Which public dataset and real versions can be approved? · _investigating_
- Q-006 · What interview evidence and checkpoint rubric must be delivered? · _investigating_
- Q-007 · Where and how should the public deployment run?
- Q-008 · Can the verified legal-entity subset be extended?
- Q-009 · How often should scheduled ETL check for ONRC updates?
- Q-010 · How should the real SQL diff benchmark be measured?
- Q-011 · What API request limits and quotas should apply?
- Q-012 · Can the accountant supply a verified, anonymized example if needed?

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

## Q-004 · What UI, design tokens, viewport sizes and screenshot procedure are required?
- **Status:** open
- **Blocks:** UI implementation, registry entries, mocks and screenshot verification.
- **Who answers:** Project owner.
- **Partial answer:** The owner reconfirmed D-002 and approved the proposed keyboard and narrow-screen acceptance workflow. D-015 specifies the main dashboard features. See [design guardrails](../design/DESIGN.md) and [acceptance criteria](../P28-REQUIREMENTS.md#acceptance-for-the-main-workflow).
- **Still open:** Detailed screen and state design, token values, supported widths, screenshot procedure, and approval of each specific Figma version and matching local mock. The registry has no design entries yet.

## Q-005 · Which public dataset and real versions can be approved?
- **Status:** investigating
- **Blocks:** Publication of real ONRC data until full-file validation; does not block the approved synthetic M2 build.
- **Who answers:** Project owner, after source investigation.
- **Partial answer:** User approved the two verified OD_FIRME.CSV editions (19.10.2026 and 04.11.2026) for M2 development, the candidate EUID key, minimal legal-entity fields and temporary protected raw processing. D-006–D-008 and C-002 govern implementation. Full downloads and mutation of existing development data remain unauthorized. Complete row counts, global quality and at least 100,000 accepted legal-entity rows per edition must be measured before manual publication. See ../ONRC-SOURCE.md.
- **Still open:** Measure total source rows, eligible legal entities per edition, and real SQL diff input size separately. If the approved editions cannot meet the requirements or the existing publication gate, investigate another official ONRC edition first and present it for separate approval. Keep the approved classification. Full validation still requires explicit authorization.

## Q-006 · What interview evidence and checkpoint rubric must be delivered?
- **Status:** investigating
- **Blocks:** Final evidence of the accountant's reaction to the working dashboard.
- **Who answers:** Project owner.
- **Partial answer:** The [committed interview summary](../../INTERVIEW.md) records the real interview. The owner supplied the authoritative [P28 and general requirements](../P28-REQUIREMENTS.md) and approved the Section C audit. Preserve the summary. Add actual feedback after the accountant tries the working demo.

## Q-007 · Where and how should the public deployment run?
- **Status:** open
- **Blocks:** Public URL, hosting, production configuration and deployment.
- **Who answers:** Project owner.
- **Partial answer:** The owner requires public HTTPS with persistent MySQL, scheduled ETL and all P28 features. D-001 applies to every application server. Compose remains required for complete local development. Evaluate a Docker host alongside compatible container hosting. Compare cost, persistence and backup recovery, protected temporary storage, scheduled jobs and benchmark capacity. Provider choice and deployment require separate approval.

## Q-008 · Can the verified legal-entity subset be extended?
- **Status:** open
- **Blocks:** Expansion beyond the verified J + SRL/SA/SNC subset, not the approved M2 implementation.
- **Who answers:** Project owner after evidence of source coding.
- **Proposed answer:** Keep unknown forms and branches quarantined. Verify additional legal-form mappings before extending the profile; never infer a legal category only from initials. See ../ONRC-SOURCE.md.
- **Partial answer:** The owner confirmed the current classification. A low eligible count alone does not justify expanding it. Investigate another official edition first if Q-005 identifies a shortfall.

## Q-009 · How often should scheduled ETL check for ONRC updates?
- **Status:** open
- **Blocks:** Final schedule interval. Scheduled ingestion and source change detection are mandatory.
- **Who answers:** Project owner after verifying the source cadence.
- **Proposed answer:** Match the verified publication cadence with the simplest configurable interval. Consider a daily check only if the cadence is unclear. Skip unnecessary downloads for unchanged sources and retain idempotent processing and guarded publication.

## Q-010 · How should the real SQL diff benchmark be measured?
- **Status:** open
- **Blocks:** Final benchmark protocol and evidence.
- **Who answers:** Project owner.
- **Proposed answer:** Identify the two published versions, input sizes and match counts. Record the measurement boundary, environment, elapsed time and reproducible command. Demonstrate a SQL diff on at least 100,000 real records in under 30 seconds after authorization.

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
