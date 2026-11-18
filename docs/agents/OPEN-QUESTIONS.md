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
- Q-006 · What interview evidence and checkpoint rubric must be delivered?
- Q-007 · Where and how should the public deployment run?
- Q-008 · Can the verified legal-entity subset be extended?

---

## Q-001 · What application purpose, users, requirements and domain terms are confirmed?
- **Status:** investigating
- **Blocks:** Domain behaviour beyond M1, user roles and domain vocabulary.
- **Who answers:** Project owner.
- **Partial answer:** On 2026-11-17 the user approved an ETL + API + Dashboard project and the professor requirements recorded in D-005. M1 infrastructure is explicitly approved independently of dataset and UI questions. No interview findings or user roles have been supplied.

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
- **Partial answer:** On 2026-11-06, the user approved Figma for design creation and visual approval, with approved representations preserved and versioned in `docs/design/mocks/`; implementation must follow the approved version. See D-002 and ../design/DESIGN.md.
- **Still open:** Screen requirements, token values, supported viewport sizes and the screenshot procedure. No Figma file link or Figma MCP integration is configured.

## Q-005 · Which public dataset and real versions can be approved?
- **Status:** investigating
- **Blocks:** Publication of real ONRC data until full-file validation; does not block the approved synthetic M2 build.
- **Who answers:** Project owner, after source investigation.
- **Partial answer:** User approved the two verified OD_FIRME.CSV editions (19.10.2026 and 04.11.2026) for M2 development, the candidate EUID key, minimal legal-entity fields and temporary protected raw processing. D-006–D-008 and C-002 govern implementation. Full downloads and mutation of existing development data remain unauthorized. Complete row counts, global quality and at least 100,000 accepted legal-entity rows per edition must be measured before manual publication. See ../ONRC-SOURCE.md.

## Q-006 · What interview evidence and checkpoint rubric must be delivered?
- **Status:** open
- **Blocks:** Interview deliverable and confirmation of the complete checkpoint requirements.
- **Who answers:** Project owner.
- **Partial answer:** On 2026-11-17 the user asked to track the missing interview separately. No interview transcript, findings, participant details or complete professor rubric have been supplied. See ../CHECKPOINT.md.

## Q-007 · Where and how should the public deployment run?
- **Status:** open
- **Blocks:** Public URL, hosting, production configuration and deployment.
- **Who answers:** Project owner.
- **Partial answer:** On 2026-11-17 the user requested documentation of the missing public URL deployment and explicitly withheld deployment authorization. No provider or public URL is confirmed. See ../CHECKPOINT.md.

## Q-008 · Can the verified legal-entity subset be extended?
- **Status:** open
- **Blocks:** Expansion beyond the verified J + SRL/SA/SNC subset, not the approved M2 implementation.
- **Who answers:** Project owner after evidence of source coding.
- **Proposed answer:** Keep unknown forms and branches quarantined. Verify additional legal-form mappings before extending the profile; never infer a legal category only from initials. See ../ONRC-SOURCE.md.
