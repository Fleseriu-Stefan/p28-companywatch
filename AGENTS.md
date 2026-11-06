# AGENTS.md — p28-companywatch

<!-- graffino-agentic:begin v1 -->
## How we work here

**Before any work:** inspect the branch and working tree. With a configured remote
and upstream, run `git fetch --all --prune`, then `git pull --ff-only`. Stop on a
non-fast-forward or on uncommitted changes you did not make. Without an upstream,
report synchronization as unavailable; do not create a remote implicitly.

**Always load** (indexes; open the entry, or its topic file, before you rely on it):
`docs/agents/DECISIONS.md`, `docs/agents/PATTERNS.md`,
`docs/agents/CONTRACTS.md`, `docs/agents/OPEN-QUESTIONS.md`, `CONTEXT.md`.

**Load on demand:**

| When | Load |
|---|---|
| You rely on an entry | the entry, or its topic file under `docs/agents/<kind>/` |
| Structural work | `docs/agents/ARCHITECTURE.md` |
| Old code or a past decision needs explaining | `docs/agents/DECISIONS-SUPERSEDED.md`, `PATTERNS-SUPERSEDED.md` (never obeyed) |
| UI work | `docs/design/DESIGN.md`, `docs/design/registry.yaml` |
| Codex CLI workflow | `docs/agents/CODEX.md` |

**Flow:** a change to more than a few lines, or one with a design choice, starts with
`/plan`. The approved plan runs with `/build`. Small fixes go straight to build, with
tests first where tests exist.

### The gate
Ask yourself: **does this change something already approved?**
- **Do, then report:** add a `candidate` pattern; add or answer an open question
  (only with an answer the user gave); write a `Proposed answer` the evidence
  supports (the question stays `investigating` until the user confirms it); fix a
  typo, link or moved path; code that follows the approved entries.
- **Propose and wait:** change, supersede or delete an `approved` pattern or
  decision; promote `candidate → approved`; add a decision; code that contradicts an
  entry. Use this shape, then stop:

```text
PROPOSAL: <add-decision | change | supersede | promote | delete>
- Existing: <ID and what it says, or "none">
- Proposed: <the new rule>
- Why now: <what changed>
- Impact: <files that follow the old rule>
- If approved: <old ID> → superseded-by <new ID> (kept, not deleted)
```
Before you propose, check `docs/agents/REJECTED.md`: never re-propose a rejected item
without new evidence. A rejected proposal is added there with the reason.

### Hard rules
- Build only from `approved` entries. Unanswered means out of scope: record a Q-,
  never invent a value, a requirement or a behaviour.
- Add nothing nobody asked for. Note it as a suggestion instead.
- Build the smallest change that meets the approved criteria, reusing existing code.
  A new abstraction, dependency, configuration option, extension point or broad
  refactor needs a concrete reason today. Never at the cost of tests or error handling.
- Tests first where the repo has tests. Never change what an existing test asserts
  to make code pass; an assertion you think is wrong goes to the user.
- Never write a secret, token, password or personal data into a file, commit or log.
- Never push, tag, release, or deploy without the user's go for that action.
- When you cite past work, label the intent: **replicate** (only for an `approved`
  pattern) or **for awareness only**. History is not a template.
- The code wins over any document. When they disagree, say so and fix the document.
- Report honestly: a failed check is reported with its output; a skipped step is
  named with its reason.

### Ledger rules
- IDs are one sequence per kind in this repo: `D-`, `PATTERN-`, `C-`, `Q-`. Never renumber.
- A provided contract (C-) lives here only; consumers link to it. Changing one is a
  PROPOSAL, and the plan names the consumer files too.
- Superseded entries stay (`status: superseded-by <ID>`) so old code stays explainable.
  Their index lines live in `DECISIONS-SUPERSEDED.md` / `PATTERNS-SUPERSEDED.md`, not
  in the always-loaded indexes; the lint (`--fix`) moves them.
- After any ledger change: `python3 docs/agents/tools/ledger-lint.py --fix` (next free
  ID: `--next D`). It must pass.
- **Confirmed:** when the user confirms an entry in a plan, set `- **Confirmed:** <date>`
  on it. Any edit to an entry removes its Confirmed line.
- A new reusable practice becomes a `candidate` pattern in the same session.
- A settled constraint becomes a decision PROPOSAL in the same session.
<!-- graffino-agentic:end -->

## 1. What this repo is
p28-companywatch is a new Tehnologii Web II laboratory repository.
It currently contains agent working instructions only. No application exists yet.
Application purpose and users remain open in `docs/agents/OPEN-QUESTIONS.md`.

## 2. Stack and commands
Application stack: not selected. Python 3 runs the supplied ledger checker.

```bash
python3 docs/agents/tools/ledger-lint.py --fix
python3 docs/agents/tools/ledger-lint.py
```

Install, build, run, test, lint/type-check and screenshot commands: not run;
no application, stack, test suite or screenshot tooling exists yet.
Future application servers must run in Docker (D-001).

## 3. Layout
- `docs/agents/`: knowledge ledger, architecture, human guide and Codex compatibility.
- `docs/design/`: design guardrails, empty registry, future mocks and screenshots.
- `.claude/skills/`: original Graffino plan and build workflows.
- `.claude/agents/`: original planner and builder definitions.
- `.agents/skills/`: optional Codex adapters; consult CODEX.md for availability.
- `CONTEXT.md`: confirmed vocabulary; `CLAUDE.md`: imports these instructions.

## 4. Rules for this repo
- Read D-001 before planning or implementing application servers.
- Follow D-002 and `docs/design/DESIGN.md` for Figma approval and versioned local mocks.
- No application implementation is currently authorized.
- This setup authorizes no commit, merge, GitHub repository creation or push.
- Explicit user restrictions override commit instructions in the workflow templates.
- Team, ClickUp and Slack addons are disabled by user choice.
- Do not infer domain requirements from the repository name.
- In Codex, use `docs/agents/CODEX.md` to invoke the Graffino workflows.

## 5. Release
At initial setup, the branch was `main`, without commits, remote or upstream.
The repository is now published on GitHub at
https://github.com/Fleseriu-Stefan/p28-companywatch.
Remote `origin` points to that repository; local `main` tracks `origin/main`.
No application version, changelog, deployment or release procedure exists.
Existing publication does not authorize future commits, merges, pushes or deploys.
Creating history or publishing requires the user's explicit authorization.

## 6. Definition of done
- The ledger checker passes after every ledger change.
- Documentation links resolve and templates contain no unfilled placeholders.
- Skills and agent definitions retain frontmatter with unique names per tool.
- Application checks remain unavailable until the stack and commands are confirmed.
- Future UI changes require confirmed designs and verified screenshots.
- Open points remain Q- entries; report failed or skipped checks with their reasons.
