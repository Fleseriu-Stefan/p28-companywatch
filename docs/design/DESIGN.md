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
- Token source for design: the approved Section D tokens below. The application has no visual token source yet.

## Tokens

The project owner approved these tokens and dashboard design rules in Lab 1
Section D. Screen-specific Figma and matching repository mock approval still
follow D-002 and Q-004.

### Color

| Token | Light | Dark | Use |
|---|---|---|---|
| `canvas` | `#F5F7FA` | `#101820` | Page background |
| `surface` | `#FFFFFF` | `#17222E` | Cards, header, menus and tables |
| `surface-subtle` | `#EEF3F8` | `#202E3D` | Table headers and quiet panels |
| `text` | `#192638` | `#EDF2F8` | Headings, labels and values |
| `text-secondary` | `#48596E` | `#B0BECF` | Metadata and supporting text |
| `divider` | `#D6DFE9` | `#334659` | Row and section separators |
| `control-border` | `#72849A` | `#7B8FA5` | Input and control outlines |
| `accent` | `#36597F` | `#9EBCE0` | Primary actions, links and brand icon |
| `accent-hover` | `#2D4C70` | `#B1CBEB` | Primary action hover |
| `accent-active` | `#233E5E` | `#8CAACD` | Primary action pressed |
| `on-accent` | `#FFFFFF` | `#142335` | Text and icons on primary actions |
| `accent-surface` | `#E7EFF8` | `#233B54` | Selected rows and options |
| `focus-ring` | `#3C6A9B` | `#B1D3FF` | Keyboard focus |
| `chart-fill` | `#5278A3` | `#89AED8` | Data bars with labels and exact values |

| Status token | Label and icon | Light text / background | Dark text / background |
|---|---|---|---|
| `added` | + Adăugată | `#206140` / `#E6F3EB` | `#A6DDB9` / `#193828` |
| `removed` | − Eliminată | `#823A53` / `#F8EAF0` | `#F3B5CB` / `#402535` |
| `modified` | ↔ Modificată | `#36597F` / `#E7EFF8` | `#B2CEEE` / `#233B54` |
| `unchanged` | = Neschimbată | `#48596E` / `#EEF3F8` | `#B0BECF` / `#202E3D` |
| `unavailable` | — Indisponibilă | `#545F6E` / `#EDF0F4` | `#BEC7D4` / `#2B3541` |
| `warning` | Atenție with a warning icon | `#774700` / `#FFF1DA` | `#FFD18A` / `#412F17` |
| `error` | Eroare with an error icon | `#A12632` / `#FCECEF` | `#FFB4B8` / `#48262F` |

Use a label and icon for every status. Added and removed describe presence in the
compared snapshots. The tested text and status pairs reached at least 5.67:1.
The tested control borders, focus rings and chart bars reached at least 3.30:1.
Verify contrast and keyboard interaction again in the finished screens.

### Typography

Use Inter with a system sans-serif fallback. Use sentence case and tabular
numerals for identifiers, dates, counts and percentages.

| Token | Family | Size / line height | Weight | Use |
|---|---|---|---|---|
| `page-title` | Inter | 32 / 40 px, 26 / 34 px on narrow screens | 700 | Page heading |
| `section-title` | Inter | 22 / 30 px | 600 | Section headings |
| `card-title` | Inter | 18 / 26 px | 600 | Chart and card headings |
| `body` | Inter | 16 / 24 px | 400 | Main copy |
| `control` | Inter | 16 / 24 px | 500 | Control and navigation labels |
| `supporting` | Inter | 14 / 22 px | 400–500 | Table values, metadata and supporting copy |

### Spacing

| Token | Value |
|---|---|
| Spacing scale | 4, 8, 12, 16, 24, 32, 48 px |
| Page gutter | 16 px narrow, 24 px medium, 32 px wide |
| Section gap | 24 px below 1024 px, 32 px from 1024 px |
| Card padding | 16 px below 1024 px, 24 px from 1024 px |
| Table row | Minimum 48 px, with 12 px vertical and 16 px horizontal padding. Rows grow to fit wrapped values. |
| Control target | Minimum 44 × 44 px |
| Focus ring | 2 px outline with 2 px offset |

### Radius, shadow, motion

| Token | Value | Use |
|---|---|---|
| `radius-control` | 8 px | Inputs and buttons |
| `radius-card` | 12 px | Cards |
| `radius-status` | Full radius | Status labels |
| `shadow-menu` | `0 8px 24px` black at 12% light or 28% dark | Menus. Use borders for cards. |
| `motion-control` | 120 ms | Control feedback |
| `motion-disclosure` | 180 ms | Disclosure transitions |
| `loading-feedback` | Within 100 ms | Pending requests. Keep section layout stable. |

Respect reduced-motion preferences.

### Breakpoints / window sizes

| Name | Width | Layout |
|---|---|---|
| Narrow | Below 768 px | Single-column profile fields, stacked comparison cards and stacked charts. Use a compact accessible navigation menu where needed. |
| Medium | 768–1023 px | Profile facts grid and comparison table. Charts stay stacked. |
| Wide | From 1024 px | Profile facts grid, comparison table and two side-by-side chart cards. |

Cap content width at 1280 px. Review at 360 px and 1440 px and check intermediate
widths for wrapping and reflow. Keep the main comparison usable without horizontal
scrolling.

## Public dashboard components

Use a restrained accounting dashboard style. Use Romanian for public labels,
navigation, filters, chart labels, validation and state messages. Keep official
ONRC terminology accurate.

| Component | Approved design |
|---|---|
| Header | Pair the CompanyWatch wordmark with a small geometric monitoring icon in the accent color. Link to **Căutare**, **Comparație** and **Analiză**. Place the accessible theme control and secondary **Autentificare** link on the right. After sign-in, show a separate entry for authorized role-specific tools. |
| Theme | Follow the system theme until a visitor explicitly chooses light or dark. Remember the choice locally across visits. |
| Company search | Place search first. Use verified name or CUI. Show a limited suggestion list with company names and verified identifiers after three characters and a 300 ms debounce. Support arrow keys, Enter and Escape. Retain the **Caută** button. |
| Company profile | Place the profile above the comparison. Show company name, CUI, EUID, registration number, legal form, county, locality and registration date. Use a facts grid on desktop and one column on mobile. Show the date and source of the newer selected edition. Label older values as historical when the company is absent from the newer edition. |
| Edition comparison | Default to the two latest published editions by edition date. Label them **Ediția anterioară** and **Ediția curentă** with actual dates and visible sources. Let visitors select any two published editions and order them from older to newer. Refresh the profile and comparison together when the pair is valid. Show changes first with **Arată câmpurile neschimbate**. Desktop rows show previous and current values side by side. Mobile cards stack the values and include the field, status and edition labels. |
| Analytics | Place **Firme după forma juridică** and **Calitatea datelor pe ediții** below the comparison. Keep charts and relevant filters usable before company selection. Company counts default to the latest published edition. Quality defaults to the two latest published editions. Its filter includes older editions and **Toate edițiile**. Show actual dates and distinguish accepted, quarantined and intentionally excluded records. |
| Chart accessibility | Give each chart a screen-reader summary and an independent, keyboard-accessible **Vezi datele** control. Keep the table collapsed initially. Its exact values follow the same filters and editions as the chart. |
| Export and saved views | Place contextual **Exportă** menus in exportable sections. Offer CSV and XLSX for the complete filtered and sorted selection across pages. On each chart card, show **Salvează vizualizarea** for authorized curators and administrators. The stable public link preserves the chart type, filters, settings and exact published editions. |

## Dashboard screen states

- **Populated dashboard.** Lead the Figma review with a selected company, visible
  edition changes and both charts. Clearly label all synthetic example data.
- **First visit.** In the profile, show „Caută și selectează o firmă pentru a
  vedea informațiile acesteia.” In the comparison, show „Selectează o firmă
  pentru a compara datele dintre edițiile ONRC.” Keep analytics available.
- **Search and edition refresh.** Cover typing, suggestions, no matches, loading,
  invalid selections and recoverable errors. Refresh the profile and comparison
  consistently for the selected pair.
- **Data coverage.** Explain no changes, missing fields, company absence from the
  newer edition and filters with no results. When fewer than two editions exist,
  explain why comparison is unavailable. Show the available quality results with
  an explanation of the limitation.
- **Component review.** Cover default, hover, visible focus, active, selected,
  disabled and success states. Include long values, one result and many results.
  Check keyboard access to search, navigation, edition selectors, filters,
  chart disclosures and exports.

Use `DS-CW-dashboard` for the first design registration. Review the populated
and first-visit states in both themes at 360 px and 1440 px. Verify the matching
repository mock against the specific Figma version before recording approval.

## V4 visual review direction

The project owner approved these revisions for the separate
[V4 HTML draft](mocks/DS-CW-dashboard-v4.html). The preceding sections preserve
the earlier Section D direction used for V1–V3. Use the overrides below for V4
and the preceding rules for behavior and tokens that V4 retains.
D-002 still requires approval of a specific Figma version and matching
repository mock before UI implementation.

### V4 color and surface tokens

| Token | Light | Dark |
|---|---|---|
| `canvas` | `#F4F2FB` | `#131123` |
| `surface` | `#FFFFFF` | `#1C192F` |
| `surface-subtle` | `#F1EDF9` | `#26223B` |
| `text` | `#231C35` | `#F4F0FA` |
| `text-secondary` | `#554D66` | `#C1B7D0` |
| `divider` | `#DDD6ED` | `#3E3555` |
| `control-border` | `#837496` | `#8C7FA6` |
| `accent` | `#593BB0` | `#BBA7FA` |
| `accent-hover` | `#4C2F99` | `#CFBEFF` |
| `accent-active` | `#3D237D` | `#AB91F3` |
| `on-accent` | `#FFFFFF` | `#211633` |
| `accent-surface` | `#EEE7FB` | `#35294B` |
| `focus-ring` | `#6845BD` | `#CFBCFF` |
| `chart-fill` | `#7352C8` | `#B6A0F3` |
| `chart-secondary` | `#087573` | `#65DDCF` |
| `secondary-surface` | `#E2F5F2` | `#19363A` |

The **Modificată** status uses `#593BB0` on `#EEE7FB` in light mode and
`#D3C3FF` on `#35294B` in dark mode. The **Neschimbată** status uses
`text-secondary` on `surface-subtle`. Retain the other status pairs and their
label and icon rules.

| Token | V4 value |
|---|---|
| `radius-card` | 16 px. Controls retain 8 px. Filter chips can use a full radius. |
| `shadow-card` | Light `0 1px 2px rgb(35 28 53 / 6%), 0 4px 12px rgb(35 28 53 / 4%)`. Dark `0 4px 12px rgb(0 0 0 / 16%)`. Keep card borders. |
| `gradient-kpi` | `linear-gradient(105deg, var(--chart-secondary), var(--chart-fill))` for thin KPI accents. |
| `gradient-mini-chart` | `linear-gradient(180deg, var(--chart-fill), var(--chart-secondary))` for miniature bars. Use solid fills and direct labels in the main charts. |
| `metric-value` | Inter with tabular numerals, 36 / 44 px on desktop and 26 / 34 px on narrow screens, weight 700. |
| `sidebar-width` | 232 px from 1024 px. |
| `rail-width` | 288 px from 1280 px. |
| `workspace-gap` | 24 px. |
| `toolbar-min-height` | 72 px on desktop and 64 px for the mobile header row. |
| `motion-chart` | 240 ms ease-out after filter changes. Keep 120 ms control feedback, 180 ms disclosures and reduced-motion support. |

### V4 layout and screen behavior

- **Desktop shell.** Keep the sidebar visible from 1024 px with the wordmark and
  links to search, comparison and analytics. Put name or CUI search, theme and
  sign-in in the top toolbar. Light mode leads review. The runtime still follows
  the system theme until the visitor chooses a theme.
- **Overview.** Use four summary cards for firms in the reference edition,
  published editions, quarantined rows and intentional exclusions. Use the same
  dated edition series for KPI values, changes and miniature charts. Identify
  synthetic data throughout the draft.
- **Main workspace.** Present the profile above field comparison. At 1440 px,
  place the KPI and profile area beside the information column. Let the comparison
  and analytics span the full workspace for readable values and controls. At large
  widths use a 3:2 analytics grid only when both cards can retain their readable
  widths. Otherwise stack the charts. Keep company search and comparison prominent.
- **Information column.** Show published edition dates and provenance, plus the
  selected company's observed field changes. Link the change summary to the main
  comparison. The first-visit history card guides visitors to select a company.
- **Mobile.** Use a collapsible accessible sidebar menu, full-width search,
  two-column KPI cards, a single-column profile, stacked comparison cards, and
  stacked charts. Move the information cards below the main workflow. Verify
  360 px and 1440 px plus intermediate layout changes.
- **Public and curator review states.** Keep the earlier populated, first-visit,
  loading, empty, unavailable, error and keyboard states. Keep contextual CSV/XLSX
  exports and exact chart tables. Saved visualizations remain writable by
  authorized curators and administrators and readable through stable links.

## Hard-coded values found (to migrate)
None in visual component code; M1 has no visual components or styles.

## Codex CLI compatibility
Codex follows D-002: create and visually approve designs in Figma, preserve the
approved representations locally, and implement only their approved version.
The original build workflow's requirement to use confirmed local mocks still applies.
No Figma MCP access, board integration or publishing is configured or authorized by
this documentation update. Report unavailable access; do not invent links or assume
tool availability. Do not create or publish a board implicitly. See ../agents/CODEX.md.
