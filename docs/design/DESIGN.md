# DESIGN — p28-companywatch

<!-- graffino-agentic:begin v1 -->
> The design guardrails for this app. Every UI change follows them. A change to a
> token or a rule here is a PROPOSAL (AGENTS.md → The gate).

## Where designs live
**Designs are created and visually approved in Figma (D-002).** Preserve the
approved representation in `mocks/<DS-id>.html`, using the documented tokens,
and verify that it matches the approved Figma version before building. The places:

| Place | Role | Updated |
|---|---|---|
| Figma (Source) | design creation and explicit visual approval of a specific version | during design and revision |
| `docs/design/` (this repo) | versioned approved representations, tokens, screenshots and registry used for implementation | after approval and when implementing an approved change |
| Design board (Source, optional) | optional presentation only; not a required approval step | only when explicitly authorized and configured |

Implementation follows the approved Figma version through its corresponding local
mock and documented tokens. If they disagree, stop and reconcile the difference
before implementation; neither silently overrides the approved version. Later Figma
edits require approval and an updated local mock before implementation.

For awareness only: the initial Graffino setup required designs to be created in
the repository and treated Figma as an optional snapshot. User-approved D-002
replaces that unnumbered workflow rule; this historical description is not a template.

## Procedure for any UI change

1. **Find the design.** Resolve the screen's `DS-` ID in `registry.yaml` and open
   its mock (`mocks/`) and screenshots (`screens/`). A **new or changed screen**
   needs confirmed requirements, tokens, states and viewport sizes first. Create
   its design in Figma (status `draft`), then obtain explicit user confirmation of
   a specific version. Preserve the approved representation in `mocks/<DS-id>.html`,
   with its frame reference, approved version and confirmation date. Compare the
   local mock with that version; resolve discrepancies before marking it `approved`
   or building it. Visual changes require reconfirmation. Team addon: the screen's
   design subtask records this confirmation. Never extrapolate a screen.
2. **Reuse first.** Use an existing component from `registry.yaml` (kind
   `component`). A new component needs a reason in the plan.
3. **Tokens only.** Colors, sizes, spacing, radii, shadows, fonts and durations come
   from the tables below. No raw hex, px or font name in component code.
4. **Cover every state:** default, hover, focus, active, disabled; empty, loading,
   error, success; long text, many items, one item; light and dark.
5. **Screenshot and compare** (command in AGENTS.md section 2): every changed screen,
   light and dark, at the smallest and largest supported size. Save as
   `screens/<DS-id>.<light|dark>.png`. Look at each one before you report.
6. **Record.** Update `registry.yaml` (new DS- ID, status `implemented`, source
   file). Keep the local mock tied to the approved Figma version. A reusable UI
   practice becomes a `candidate` pattern.

## Guardrails

**Color and contrast**
- Text contrast ≥ 4.5:1 (≥ 3:1 for text ≥ 18.66 px bold / 24 px). Icons, borders of
  inputs and focus rings ≥ 3:1 against their background. Check both themes.
- Color never carries meaning alone: pair it with an icon or text.
- Dark mode uses its own token values, not inverted light values.

**Layout and spacing**
- Spacing comes from the scale only. Align to the grid; equal gaps for equal
  relationships.
- No horizontal scroll at the smallest supported width. Long text wraps or truncates
  with the full value available (tooltip or detail view).

**Typography**
- Only the type scale below. One primary heading per screen. Sentence case for
  labels, buttons and headings.

**Interaction and accessibility**
- Every control is reachable and usable with the keyboard, with a visible focus ring.
- Hit targets ≥ 44 × 44 px on touch, ≥ 24 × 24 px with a pointer.
- Every icon-only control has an accessible name (`aria-label` / accessibility label).
- Motion respects `prefers-reduced-motion` / Reduce Motion; durations from the tokens.

**Copy**
- Plain, short, active voice. Buttons name the action ("Install", not "OK").
- Error text says what happened and what to do next. No raw error codes alone.
- Terms from `CONTEXT.md` only.

**States**
- Empty states explain what will appear and offer the next action.
- Loading shows within 100 ms of a wait; skeletons keep the final layout.
- Destructive actions ask for confirmation or offer undo.

## Figma approval and local records
Frame names are `<DS-id> · <screen>`. Approval identifies the specific Figma version;
comments and the mere presence of a frame do not constitute approval.

Preserve the approved representation as `mocks/<DS-id>.html` and record its frame
reference, approved version and confirmation date with the mock. Verify correspondence
before implementation. Any later visual revision repeats approval and local mock
updates; edits in Figma do not automatically change the approved implementation basis.

A design board is optional and is not required for approval. Do not create or publish
one implicitly. No Figma link or integration is configured; using Figma as the selected
design tool does not imply that Figma MCP access exists.

DS- IDs are for the tools (registry, mocks, board, Figma frames). Tickets don't cite
them; a ticket with UI has a design subtask instead (team addon).

<!-- graffino-agentic:end -->

## Source
- Design board: none configured.
- Figma: selected for design creation and visual approval (D-002); no file link or MCP integration configured.
- Token source in code: none; no application code exists.

## Tokens
No token values, font families, sizes or breakpoints have been selected.
Q-004 blocks UI implementation. Do not use sample token values as approved choices.

### Color
| Token | Light | Dark | Use |
|---|---|---|---|

### Typography
| Token | Family | Size / line height | Weight | Use |
|---|---|---|---|---|

### Spacing
| Token | Value |
|---|---|

### Radius, shadow, motion
| Token | Value | Use |
|---|---|---|

### Breakpoints / window sizes
| Name | Min | Max |
|---|---|---|

## Hard-coded values found (to migrate)
None; no application code exists.

## Codex CLI compatibility
Codex follows D-002: create and visually approve designs in Figma, preserve the
approved representations locally, and implement only their approved version.
The original build workflow's requirement to use confirmed local mocks still applies.
No Figma MCP access, board integration or publishing is configured or authorized by
this documentation update. Report unavailable access; do not invent links or assume
tool availability. Do not create or publish a board implicitly. See ../agents/CODEX.md.
