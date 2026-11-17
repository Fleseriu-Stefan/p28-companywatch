# Patterns — p28-companywatch

<!-- graffino-agentic:begin v1 -->
> How we build things here. Copy only `approved` entries. `candidate` = seen once or
> not yet confirmed; agents add these freely. Promotion needs the user's OK.
<!-- graffino-agentic:end -->

## Index
- PATTERN-001 · Isolated Compose verification · candidate

---

No application patterns are approved for replication.

## PATTERN-001 · Isolated Compose verification
- **Status:** candidate
- **Date:** 2026-11-17
- **How:** Exercise database and service lifecycle behaviours in a randomly named Compose project, with temporary credentials generated in memory, an ephemeral loopback port and project-scoped cleanup. Share the entry command between local verification and CI. Never target the development database for schema-negative tests.
- **Example:** scripts/verify.py and .github/workflows/ci.yml establish this practice during approved M1 implementation. Candidate only; promotion requires user approval.
