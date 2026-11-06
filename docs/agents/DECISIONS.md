# Decisions — p28-companywatch

<!-- graffino-agentic:begin v1 -->
> Constraints the code must obey. Status: `approved` (obey) · `proposed` (do not
> build on it) · `superseded-by <ID>` (kept to explain old code).
> Adding or changing an entry needs the user's OK (AGENTS.md → The gate).
<!-- graffino-agentic:end -->

## Index
- D-001 · All application servers run in Docker
- D-002 · Figma approval with versioned local design mocks

---

## D-001 · All application servers run in Docker
- **Status:** approved
- **Date:** 2026-11-06
- **Rule:** All application servers, including databases, API servers and web servers, run in Docker.
- **Why:** The professor requires Docker for every server used in the laboratory project.
- **Evidence:** Lab Setup.pdf, page 1, “Cum lucrăm la laborator”; user approval dated 2026-11-06.
- **Source:** user · confidence high
- **Confirmed:** 2026-11-06

## D-002 · Figma approval with versioned local design mocks
- **Status:** approved
- **Date:** 2026-11-06
- **Rule:** Create and visually approve designs in Figma. Preserve and version the approved representations in `docs/design/mocks/`. Implementation must follow the approved version, using its corresponding local mocks and documented tokens.
- **Why:** The project owner selected Figma for design creation and visual approval while retaining reviewable design representations in the repository.
- **Evidence:** User explicitly approved D-002 and the six-file documentation plan on 2026-11-06.
- **Source:** user · confidence high
- **Confirmed:** 2026-11-06
