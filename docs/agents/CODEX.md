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
Skip fetch/pull until a remote and upstream exist; report the reason.
Explicit user authorization overrides automatic branch and commit steps in the original templates.
Current permission covers setup files and verification only.
No commit, merge, GitHub repository creation, push or application implementation is authorized.
Team, ClickUp and Slack addons are disabled; their conditional template sections do not apply.
Do not create tickets, PRs, workflows or external messages.

## Design
Keep local mocks, tokens and screenshots under docs/design/.
No design board, publishing integration or screenshot command exists.
Use explicit user confirmation for local designs; do not assume Claude board tools exist.
Q-004 blocks implementation until UI requirements and verification are confirmed.

## Verification
Run the ledger checker with --fix, then without --fix.
Check frontmatter, local documentation paths and Git ignore rules.
Application tests, builds and screenshots are unavailable until requirements and tooling exist.
Report unavailable checks honestly; never substitute invented commands.

## Sources
- Local Graffino skill: release 1.4.0, marker version v1.
- Lab Setup.pdf: pages 1 and 8–14; Codex compatibility is explained on page 11.
- Official Codex instructions: https://learn.chatgpt.com/docs/agent-configuration/agents-md
- Official Codex skills: https://learn.chatgpt.com/docs/build-skills
