# M2 — implementare și verificare

Verificările locale au fost finalizate la 2026-11-18 pe `feat/m2-etl`.
M2 a fost integrat în `main` prin
[PR #2](https://github.com/Fleseriu-Stefan/p28-companywatch/pull/2), la
`b8a2b6f4e67ad50d6a9d3087c01f76820a50786b`.
GitHub Actions a trecut pe [PR](https://github.com/Fleseriu-Stefan/p28-companywatch/actions/runs/44303506687)
și pe [commitul din main](https://github.com/Fleseriu-Stefan/p28-companywatch/actions/runs/44305433658).

## Rularea locală completă M2

Comanda `python3 -B scripts/verify.py` a ieșit cu codul **0** și mesajul
`M1/M2 verification passed`, după remedierea problemelor de concurență și migrare
și după actualizarea finală a regulilor `.dockerignore`.

| Verificare | Rezultat |
|---|---|
| Ledger lint și excluderi Git și Docker | Trecute |
| Docker build backend/frontend | Trecut |
| Ruff check și format, backend/script | Trecut |
| Teste unitare API/configurare/ETL | `30 passed, 16 deselected` |
| Baseline istoric și upgrade M1→M2 | `1 passed` |
| Integrare MySQL M2 și readiness | `15 passed, 31 deselected` |
| Total pytest | **46 trecute, 0 eșuate** |
| Recuperare Alembic | Reluare după DDL parțial, refuzul schemei incompatibile, păstrarea markerului M1 și a rândului inițial de publicare, upgrade repetat și generare SQL offline |
| Concurență ETL | După pierderea lock-ului, workerul inițial nu mai scrie și nu poate șterge snapshotul pregătit de succesor |
| Protecție Compose | Refuz fără opt-in și refuzul proiectului M1 simulat în proiectul de test. Comenzile ETL de metadate au rulat fără pornirea bazei sau a migrării. |
| Volum parser | 100.001 rânduri sintetice; peak Python sub 16 MiB |
| Volum ingestie/publicare | 100.001 persoane juridice sintetice; prag integral 100.000 |
| ESLint, TypeScript, Vite | Trecute |
| tmpfs raw | Mount tmpfs, proprietar corect și mod 0700 confirmate în Docker |
| HTTP și Compose | Live/ready/docs, outage/recovery, persistență, migrare eșuată și recuperare trecute |
| Baza existentă | Verificare read-only înainte și după. Același volum `companywatch_mysql_data`, revizia `0001_baseline` și doar tabela `alembic_version`. |

Testele de integrare verifică minimizarea proiecției, duplicate complete și între
clase, idempotenta și concurența, approval/report/data seals, refuzul publicării
neaprobate, diff SQL NULL-safe și sensibil la litere, rollback atomic și recuperarea
versiunii abandonate. Snapshoturile sintetice sunt marcate distinct; CLI nu le
poate publica și nu poate coborî pragul pentru date reale.

Runnerul a verificat proiectul temporar `companywatch-check-5d717f1c7bf1de63`
și volumul separat `companywatch-check-5d717f1c7bf1de63_mysql_data` înainte de
migrări și teste de integrare. Credenițialele de test au fost generate în memorie.
Containerele, rețeaua și volumul de test au fost eliminate după verificare.
Testele ETL au folosit date sintetice și simulări de transfer.

## Probleme întâlnite și corectate

- Rulările din timpul remedierii au detectat formatarea Ruff a runnerului și o
  diferență de reprezentare în schema reflectată de MySQL. Compararea acceptă
  acum forma echivalentă în care MySQL precizează explicit charset-ul moștenit
  `utf8mb4`. Ambele verificări au trecut în rularea completă de mai sus.
- Cele **44 de teste trecute** aparțin verificării inițiale M2. Cele două cazuri
  noi de pierdere a lock-ului sunt incluse în totalul de 46.
- Primele 17 teste unitare ETL au eșuat cu `NotImplementedError` pe interfețele
  încă neimplementate; aceleași aserțiuni au trecut după implementare.
- Ruff a raportat `E501 Line too long` pe codul nou și teste. Au fost corectate
  formatarea/importurile, fără relaxarea verificărilor.
- Primele teste rulate cu bind mount au avertizat că nu pot scrie cache-ul pytest
  în directorul de lucru. Rulările de diagnostic au dezactivat cache-ul; verificarea
  finală în imaginile construite nu are această problemă.
- Writerul fixture-ului sintetic a fost ajustat mecanic să emită ghilimele literale,
  ca sursa aprobată, fără backslash introdus de serializer. Aserțiunile nu s-au schimbat.
- Testul de reproducere al importului abandonat a eșuat cu `ETLError: version_busy`.
  Recuperarea este acum protejată prin lock MySQL de sesiune; o încercare activă
  nu este preluată, iar una abandonată poate fi refăcută fără duplicate.
- Revizia a identificat retenția raw după omorârea forțată a unui container cu
  volum persistent. Serviciul ETL folosește acum tmpfs și CLI refuză raw persistent.
- A fost adăugat cazul EUID duplicat între un rând eligibil și unul exclus sau
  necunoscut: candidatul este carantinat, fără salvarea identificatorului exclus.

Testele M1 dependente de schemă au fost actualizate numai în limitele aprobării
explicite: baseline-ul este țintit ca `0001_baseline`, verificările istorice ale
reviziei și tabelei unice sunt păstrate, readiness refuză schema veche, apoi upgrade-ul
la `0002_etl` păstrează un marker sintetic creat în baza izolată. Smoke-ul verifică
noul head. Nu s-au schimbat aserțiuni pentru a masca defecte ale implementării.

În rularea reușită, codul 2 a confirmat refuzul migrării fără opt-in. Codul 17
injectat a confirmat blocarea API-ului până la o migrare reușită.

## Limite și pași neexecutați

- Rămân avertismentul Starlette/HTTPX privind TestClient și notificarea npm
  despre o versiune majoră disponibilă.
- Full-file ONRC, calitatea globală, minimum 100.000 PJ eligibile per ediție și
  diff-ul real nu au fost demonstrate. Nu există rezultate inventate.
- tmpfs-ul de 1 GiB și spațiul MySQL trebuie dimensionate înaintea importului real.
- Clasificarea este conservatoare: J + SRL/SA/SNC, fără sucursale. Nu acoperă toate
  formele juridice; extensiile sunt Q-008 și necesită dovezi/aprobare.
- Nu s-au modificat credențialele sau datele bazei existente. `.env` rămâne local,
  ignorat și cu mod 600. Nu s-au implementat UI, interviu sau deploy.

Ghidul pentru primul import real, care necesită autorizare separată, este
[M2-ETL.md](M2-ETL.md). Sursele sunt în [ONRC-SOURCE.md](ONRC-SOURCE.md).

## Fișiere

Noi: `backend/app/etl/__init__.py`, `source.py`, `errors.py`, `parser.py`,
`download.py`, `models.py`, `service.py`, `diff.py`, `cli.py` din același director;
`backend/migrations/versions/0002_etl.py`; `backend/tests/__init__.py`,
`conftest.py`, `etl_fixtures.py`, `test_etl_parser.py`, `test_etl_download.py`,
`test_etl_cli.py`, `test_etl_volume.py`, `test_etl_database.py` din `backend/tests/`;
`docs/ONRC-SOURCE.md`, `docs/M2-ETL.md`, `docs/M2-VERIFICATION.md`.

Actualizate: Dockerfile backend, `backend/.dockerignore`,
`frontend/.dockerignore`, `compose.yaml`, `scripts/verify.py`,
`backend/migrations/env.py`, `backend/tests/test_database.py`, workflow-ul CI,
ignore-urile rădăcinii, README, AGENTS, CONTEXT și documentația/registrul Graffino.
Aplicația frontend folosește aceleași surse și dependențe. API-ul păstrează
contractul health C-001.

În ledger: D-006–D-008/C-002 aprobate, Q-005 clarificată parțial, Q-008 deschisă,
PATTERN-002 candidat, fără promovare automată.
