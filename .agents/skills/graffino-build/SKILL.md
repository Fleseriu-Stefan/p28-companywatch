---
name: graffino-build
description: Execute only an explicitly approved Graffino plan; load the original Claude build workflow and preserve user restrictions.
---

# Graffino build for Codex CLI

1. Read `AGENTS.md` and `docs/agents/CODEX.md` from the repository root.
2. Load the knowledge indexes and each entry this task relies on.
3. Read `.claude/skills/build/SKILL.md` and `.claude/agents/builder.md`.
4. Follow that original workflow using the tool mapping in `docs/agents/CODEX.md`.
5. Explicit user restrictions override automatic branch, commit, merge and publishing steps.
6. With no remote/upstream, report synchronization as unavailable; do not create one implicitly.
7. Do not implement application requirements while their blocking questions remain unanswered.
