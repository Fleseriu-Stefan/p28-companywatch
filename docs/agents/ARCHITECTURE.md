# Architecture — p28-companywatch

<!-- graffino-agentic:begin v1 -->
> How this repo is built, generated from the code at backfill and kept current by
> whoever changes the structure. The code wins: when this page is wrong, fix it.
<!-- graffino-agentic:end -->

## Overview
M1 implements the technical foundation selected in D-003–D-005.
The frontend has build tooling and a React entry rendering null; it has no visual UI.
The backend exposes the health/documentation contract C-001. No dataset or ETL
schema is assumed. Q-004 and Q-005 block UI and dataset-dependent implementation.

## Parts
| Part | Path | Responsibility | Talks to |
|---|---|---|---|
| API | backend/app/ | FastAPI, configuration, SQL connection and health | MySQL |
| Migrations | backend/migrations/ | Alembic baseline and revision tracking | MySQL |
| Database | compose.yaml: db | MySQL with persistent named volume | API and migrations |
| Frontend tooling | frontend/ | React, TypeScript, ESLint and Vite build | No API consumer yet |
| Verification | scripts/verify.py, backend/tests/ | Unit, MySQL and Compose behaviour checks | Isolated Docker project |
| CI | .github/workflows/ci.yml | Same verification on PR and main push | Docker |
| Agent instructions | AGENTS.md | Shared working rules | Knowledge ledger |
| Knowledge ledger | docs/agents/ | Confirmed knowledge and open questions | Agent instructions |
| Design documentation | docs/design/ | Guardrails and future design records | No visual UI yet |
| Claude workflows | .claude/ | Original plan/build skills and agents | Knowledge ledger |

## Data flow
`db` healthy → `migrate` exits successfully → `api` starts. API readiness queries
MySQL and compares its Alembic revision with the application's heads. Liveness
does not access MySQL. Contract details live only in CONTRACTS.md, C-001.
No company data, ingestion, diff or dashboard flow exists yet.

## State and storage
MySQL stores only Alembic revision tracking in M1. Its named volume survives
normal `stop` and `down`. The verification script owns a separate randomly named
project and deletes only that project's volume at cleanup.

## Configuration
Non-secret defaults live in `.env.example`. The user explicitly authorized local
MySQL credentials in the Git-ignored, untracked `.env` with mode `600`, generated
once and preserved for existing databases. Exported environment variables remain
an alternative; no credentials belong in versioned files or logs. SQLAlchemy URL objects
handle password encoding; settings representations omit passwords. SQL connection,
read/write and pool acquisition timeouts are finite. API uses a non-root DB user.
MySQL has no host port; API binds to host loopback only.

## Build, deploy, runtime
All application servers run in Docker (D-001). Backend and frontend base images
are pinned by digest; Python and npm dependencies are locked. The tests and
frontend build are optional Compose tools, not additional public servers.
See ../../README.md for executable commands. CI uses the same verification script.
No deployment or public URL exists; see ../CHECKPOINT.md.

## Boundaries
The API owns C-001 in CONTRACTS.md. Consumers are the Compose healthcheck, tests
and verification script. There are no frontend API consumers or external dataset
contracts yet. No auth or production deployment architecture is selected.
