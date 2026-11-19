# AI log

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
