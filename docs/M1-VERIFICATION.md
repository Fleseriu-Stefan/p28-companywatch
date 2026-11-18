# M1 — implementare și verificare

Verificarea locală inițială a avut loc pe `feat/m1-foundation` la 2026-11-17.
Planul M1, D-003–D-005 și C-001 au fost aprobate explicit de utilizator.
Ulterior, M1 a fost integrat în `main` prin
[PR #1](https://github.com/Fleseriu-Stefan/p28-companywatch/pull/1), la `c5c0b71`.
[GitHub Actions a trecut pe commitul din main](https://github.com/Fleseriu-Stefan/p28-companywatch/actions/runs/44161857724).

## Rezultatul execuției complete

Comandă executată pe host: `python3 scripts/verify.py`.
Rezultat final: **exit 0**, cu mesajul `M1 verification passed`.
Docker Engine 29.9.3, Docker Compose v5.7.0; containere Python 3.13,
Node 24 și MySQL 8.4, fixate prin digest în configurație.

| Verificare | Rezultat |
|---|---|
| Ledger lint | `✓ ledger ok` |
| Build backend/frontend | Ambele imagini construite |
| Ruff backend și scriptul de verificare | Check și format trecute |
| pytest fără integrare | `7 passed, 2 deselected` |
| pytest integrare pe MySQL real | `2 passed, 7 deselected` |
| ESLint frontend | Trecut |
| TypeScript `tsc --noEmit` | Trecut |
| Vite build | Trecut, artefacte produse în container |
| Pornire Compose pe bază nouă | MySQL sănătos, migrare reușită, API sănătos |
| API live/ready, OpenAPI și docs | Răspunsuri verificate prin HTTP |
| Reaplicarea migrării | Aceeași revizie; doar tabela `alembic_version` |
| Revizie incompatibilă | Readiness 503, apoi restaurare |
| MySQL oprit | Readiness 503, liveness 200 |
| MySQL repornit | Readiness revine la 200 |
| Migrare eșuată intenționat | Cod 17; API nu pornește |
| Persistență după `down` fără eliminarea volumului | Revizia verificată înainte de o nouă migrare |
| Recuperare după scenariul negativ | Migrare normală și API sănătos |
| Cleanup | Containerele, rețeaua și volumul proiectului de test eliminate |
| Verificări documentație | Căi locale rezolvate, frontmatter și nume unice per tool, import CLAUDE păstrat |
| Git ignore și whitespace | Fișiere sensibile/cache ignorate, exemple și skills versionabile, `git diff --check` trecut |

Suitele pytest însumează **9 teste**. Scenariile Compose/HTTP sunt verificări
suplimentare în script. Aserțiuni schimbate pentru a face implementarea să treacă:
**0**. Nicio bază de dezvoltare nu a fost folosită pentru testele negative.

## Probleme întâlnite și corectate

- Prima colectare a testelor, înainte de existența aplicației:
  `ModuleNotFoundError: No module named 'app'`. Nu constituie o probă de
  comportament funcțional; a precedat implementarea modulelor.
- Prima verificare Ruff în imaginea fără drept de scriere pe directorul de lucru:
  `Failed to initialize cache at /app/.ruff_cache: Permission denied`.
  Directorul de lucru aparține acum utilizatorului neprivilegiat al aplicației.
- Verificări statice: `F821 Undefined name Settings` și
  `E501 Line too long (103 > 100)`. Corectate cu tipul `Self` și formatare.
- Două teste readiness au eșuat cu `ResponseValidationError`, deoarece răspunsul
  negativ era validat ca răspuns de succes. Răspunsul 503 folosește acum explicit
  `JSONResponse`, cu modelul negativ documentat separat în OpenAPI. Aceleași teste
  trec după corectarea implementării.
- Build Compose invocat direct fără credențiale exportate:
  `required variable MYSQL_PASSWORD is missing a value` și echivalentul pentru
  `MYSQL_ROOT_PASSWORD`. Configurarea obligatorie rămâne intenționată; scriptul
  complet furnizează credențiale temporare în memorie, README explică pornirea locală.
- ESLint 9 a emis avertisment de ieșire din suport la rezolvarea inițială.
  Dependențele finale folosesc ESLint 10, iar verificarea a trecut.

Formatarea/importurile din fișierele Python au fost corectate mecanic. Nicio
aserțiune de test nu a fost relaxată sau eliminată.

## Avertismente și verificări neexecutate

- Starlette 1.10.0 emite un avertisment de depreciere pentru utilizarea HTTPX cu
  `TestClient`: `Using httpx with starlette.testclient is deprecated; install
  httpx2 instead`. Dependențele sunt fixate; toate testele trec. Nu a fost adăugat
  un nou client HTTP în afara planului aprobat.
- npm a semnalat scriptul de instalare esbuild în politica sa `allowScripts`.
  Build-ul Vite a trecut cu configurația imaginii Node fixate.
- Screenshots/UI nu s-au executat: nu există interfață vizuală aprobată în Figma.
- Nu s-au verificat date ONRC, nu s-a realizat un interviu și nu s-a făcut deploy.
  Aceste lipsuri sunt urmărite separat în [CHECKPOINT.md](CHECKPOINT.md).

## Fișiere create

| Grup | Fișiere |
|---|---|
| Rădăcină | `README.md`, `compose.yaml`, `.env.example`, `.dockerignore` |
| Backend build | `backend/Dockerfile`, `backend/.dockerignore`, `backend/pyproject.toml`, `backend/requirements.in`, `backend/requirements.lock` |
| Backend aplicație | `backend/app/__init__.py`, `backend/app/main.py`, `backend/app/config.py`, `backend/app/db.py`, `backend/app/api/__init__.py`, `backend/app/api/health.py` |
| Migrări | `backend/alembic.ini`, `backend/migrations/env.py`, `backend/migrations/script.py.mako`, `backend/migrations/versions/0001_baseline.py` |
| Teste | `backend/tests/test_config.py`, `backend/tests/test_health.py`, `backend/tests/test_database.py` |
| Frontend build | `frontend/Dockerfile`, `frontend/.dockerignore`, `frontend/package.json`, `frontend/package-lock.json`, `frontend/tsconfig.json`, `frontend/vite.config.ts`, `frontend/eslint.config.js` |
| Frontend intrare fără UI | `frontend/index.html`, `frontend/src/main.tsx` |
| Verificare/CI | `scripts/verify.py`, `.github/workflows/ci.yml` |
| Documentație separată | `docs/CHECKPOINT.md`, `docs/M1-VERIFICATION.md` |

Fișiere actualizate: `.gitignore`, `AGENTS.md`, `CONTEXT.md`,
`docs/agents/ARCHITECTURE.md`, `CODEX.md`, `CONTRACTS.md`, `DECISIONS.md`,
`OPEN-QUESTIONS.md`, `PATTERNS.md`, `README.md` din `docs/agents/`, precum și
`docs/design/DESIGN.md` pentru a reflecta existența fundației fără UI.

## Registru și limite

- D-003–D-005 și C-001 înregistrate ca aprobate, cu data confirmării.
- Q-002 și Q-003 răspunse din aprobarea utilizatorului.
- Q-001 parțial clarificată; Q-004 rămâne deschisă pentru design.
- Q-005 urmărește datasetul; Q-006 interviul/grila; Q-007 deploy-ul public.
- PATTERN-001 este doar candidat: verificare Compose izolată. Nu a fost promovat.

Nu există abatere funcțională de la planul aprobat. Scriptul comun de verificare
este concretizarea testelor Compose și a aceleiași verificări locale/CI.

## Verificare înainte de commit

Utilizatorul a autorizat ulterior păstrarea parolelor MySQL o singură dată în
`.env` local privat, cu permisiuni `600`. README, AGENTS și arhitectura reflectă
această excepție; `.env.example` nu conține parole. Parolele locale au fost
comparate în memorie cu toate cele 46 de fișiere candidate: nicio potrivire.
Scanarea pentru tokenuri, chei private și URL-uri cu credențiale nu a găsit rezultate.
Aceste verificări nu reprezintă o garanție universală de detectare a secretelor.

La pregătirea commitului au fost rerulate cele 7 teste unitare, Ruff backend,
ESLint, TypeScript și build Vite: toate au trecut. Rămâne avertismentul cunoscut
Starlette/HTTPX. Cele 2 teste de integrare și scenariile Compose complete au trecut
în execuția M1 consemnată mai sus; nu au fost rerulate în această verificare,
pentru a respecta instrucțiunea ulterioară de a nu șterge volume. Scriptul complet
elimină propriul volum temporar la cleanup.

Aplicația locală a fost verificată separat: endpointurile live, ready și docs au
răspuns HTTP 200, MySQL a răspuns la SELECT 1, iar Alembic a raportat
`0001_baseline (head)`. Nu s-au schimbat funcționalități sau aserțiuni de test
în pregătirea commitului.
