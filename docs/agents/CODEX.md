# Graffino with Codex CLI

The original `.claude/` skills and agents remain unchanged.
`AGENTS.md` supplies shared rules. `CLAUDE.md` remains exactly `@AGENTS.md`.

## Load before work
Read AGENTS.md, CONTEXT.md and the decisions, patterns, contracts and questions indexes.
Open each referenced entry before relying on it. Read ARCHITECTURE.md for structural work.
Read docs/design/DESIGN.md and registry.yaml before UI work.

## Invoke
Codex discovers repository skills under `.agents/skills/`.
Use `$graffino-plan` or `$graffino-build` when the adapters are available.
These adapters load the original workflow rather than duplicating its rules.
If adapters are unavailable, explicitly ask Codex to read the original SKILL.md and follow this compatibility guide.
Claude's `/plan` and `/build` are not assumed to be Codex slash commands.

## Tool and role mapping
Read/Grep/Glob/Bash mean the available file, search and shell tools in Codex.
Write/Edit mean the available workspace editing tools, subject to permissions.
ToolSearch means tool discovery when supported; never assume an integration exists.
The `.claude/agents/*.md` files are role instructions, not native Codex agent registrations.
For planning, read `.claude/agents/planner.md`; for building, read `.claude/agents/builder.md`.
Use one Codex session when delegation is unavailable or not authorized.
Do not assume Claude's `isolation: "worktree"` is a Codex tool argument.

## Initial repository and authorization
This repository started on main, without commits, remote or upstream.
It is now published at https://github.com/Fleseriu-Stefan/p28-companywatch.
Remote `origin` points to that repository; local `main` tracks `origin/main`.
Follow AGENTS.md synchronization rules now that the remote and upstream exist.
Explicit user authorization overrides automatic branch and commit steps in the original templates.
M1 and M2 are merged into `main`. Under D-016, verification runs on every
push and on pull requests. Team, ClickUp and Slack addons are disabled by user choice.

## Delivery mode through December 3, 2026
Under D-017, plan one S or M delivery unit at a time. The M2.3C campaign is
closed. Through the end of December 3 in Europe/Bucharest, the project owner
pre-authorizes feature-branch commits and pushes, opening PRs, merging after CI
is green for the current PR revision, full download and ingestion of the two
D-006 editions (19.10.2026 and 04.11.2026), and deployment to the owner's Oracle
VM. Per-action authorization resumes December 4. Preserve existing MySQL data
and follow the protected raw-data, validation, and manual publication rules in
D-007, D-008 and C-002.

## Design
Keep local mocks, tokens and screenshots under docs/design/.
D-002 and docs/design/DESIGN.md define Figma as the place to create and visually
approve designs. Preserve the approved representations as versioned local mocks
in docs/design/mocks/ and verify their correspondence to the approved Figma version
before implementation. Record the frame reference, approved version and confirmation date.
Implement from those approved local mocks and documented tokens.
Q-004 records the approved CompanyWatch Draft 1 design and its review procedure.
Use the [registered Figma references and mockups](../design/registry.yaml). Verify
Figma access for each session. A design board requires separate authorization.

## Verification
Run the ledger checker with --fix, then without --fix.
Check frontmatter, local documentation paths and Git ignore rules.
Run `python3 scripts/verify.py` for the approved M1/M2 application checks in Docker.
It uses an isolated MySQL volume and generated in-memory credentials. See README.md.
Draft 1 has registered Chromium reference captures. Include the application
screenshot command in any UI implementation plan. Report unavailable checks honestly.

## Sources
- Local Graffino skill: release 1.4.0, marker version v1.
- Lab Setup.pdf: pages 1 and 8–14; Codex compatibility is explained on page 11.
- Official Codex instructions: https://learn.chatgpt.com/docs/agent-configuration/agents-md
- Official Codex skills: https://learn.chatgpt.com/docs/build-skills
