# AI log

## 2026-11-19 · Lab 1 Section D Draft 1 review

The project owner selected the existing CompanyWatch Draft 1 with its original
sidebar and the refined Perspectivă, Stare and Temă controls. Codex verified the
nine mockup screens at 360, 768 and 1440 px in both themes and all five states.
The 40 existing Figma review frames were updated in place with the matching
Chromium captures. Image hashes and frame dimensions were checked. The design
registry remains at `draft` pending the owner's D-002 equivalence confirmation.
[Review package](docs/design/DESIGN.md#pachet-pentru-aprobarea-vizuală).

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
[historical interview](INTERVIEW.md) were preserved. Section D is pending approval.
