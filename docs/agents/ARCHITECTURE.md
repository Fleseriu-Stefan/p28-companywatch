# Architecture — p28-companywatch

<!-- graffino-agentic:begin v1 -->
> How this repo is built, generated from the code at backfill and kept current by
> whoever changes the structure. The code wins: when this page is wrong, fix it.
<!-- graffino-agentic:end -->

## Overview
This repository contains the Graffino working system only.
No application code, services, database or runtime configuration exists.
No architecture is selected. Q-001 and Q-002 block application design.

## Parts
| Part | Path | Responsibility | Talks to |
|---|---|---|---|
| Agent instructions | AGENTS.md | Shared working rules | Knowledge ledger |
| Knowledge ledger | docs/agents/ | Confirmed knowledge and open questions | Agent instructions |
| Design documentation | docs/design/ | Guardrails and future design records | No application yet |
| Claude workflows | .claude/ | Original plan/build skills and agents | Knowledge ledger |

## Data flow
No application data flows exist.

## State and storage
No application state or storage exists.

## Configuration
No application environment variables or secrets are configured.

## Build, deploy, runtime
Application commands are unavailable; see AGENTS.md sections 2 and 5.
All future application servers run in Docker; see DECISIONS.md, D-001.

## Boundaries
No application interfaces have been identified; see CONTRACTS.md.
