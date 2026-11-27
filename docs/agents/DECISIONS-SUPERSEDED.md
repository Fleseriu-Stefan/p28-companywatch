# Decisions superseded — p28-companywatch

<!-- graffino-agentic:begin v1 -->
> Decisions that no longer apply. **Never obeyed**; read only to explain old code or a
> past choice. Each points to the entry that replaced it. `ledger-lint.py --fix`
> keeps this file in sync: superseded entries move here from `DECISIONS.md`, and
> their index lines move here from its index.
<!-- graffino-agentic:end -->

## Index
- D-004 · Docker verification and continuous integration · _superseded-by D-016_

---

## D-004 · Docker verification and continuous integration
- **Status:** superseded-by D-016
- **Date:** 2026-11-17
- **Rule:** Run application verification in Docker, with real MySQL integration tests. Use pytest and HTTPX for backend tests, Ruff for Python checks, TypeScript and ESLint for frontend checks, and GitHub Actions on pull requests and pushes to main. CI checks the ledger, backend tests, frontend build and Compose smoke behaviour. Pin compatible dependencies during implementation.
- **Why:** Make M1 startup and verification reproducible locally and in CI.
- **Evidence:** User explicitly approved the M1 plan and D-004 on 2026-11-17.
