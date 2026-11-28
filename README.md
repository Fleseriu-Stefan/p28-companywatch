# P28 — CompanyWatch

Proiect Tehnologii Web II: ETL + API + Dashboard pentru consultarea și compararea
datelor publice ONRC din ediții succesive. Contabilul intervievat a descris o
problemă recurentă: verificarea unui posibil partener cere consultarea mai multor
surse și compararea manuală a informațiilor. Nu există un caz verificat pentru o
companie sau o tranzacție anume. Vezi [interviul documentat](INTERVIEW.md).

În demonstrația propusă de proprietarul proiectului, vizitatorul caută o firmă
după denumire sau CUI, unde câmpul este verificat, alege rezultatul corect și vede
profilul public și comparația dintre două ediții pe aceeași pagină. Comparația
arată sursa și data fiecărei ediții, tipul modificării și valorile anterioare și
curente. Interfața distinge informațiile neschimbate, valorile indisponibile și
absența firmei dintr-o ediție. Contabilul va valida acest flux după implementare.

[Cerințele obligatorii P28 și generale](docs/P28-REQUIREMENTS.md) cuprind matricea
de trasabilitate, criteriile de acceptare și etapele rămase. Exporturile CSV/XLSX,
accesul API, autentificarea și istoricul sunt în scop. Analiza financiară
multianuală din surse suplimentare, verificările fiscale sau TVA, notificările
automate și integrarea cu programe de contabilitate comerciale sunt excluse.

M1, M2 și M2.1 sunt integrate în `main`. M1 asigură fundația Docker, FastAPI,
MySQL, Alembic, React/TypeScript/Vite, teste și CI. M2 adaugă ETL versionat,
publicare cu aprobare și diff SQL, verificate cu date sintetice. M2.1 adaugă
comparații consultative ale rapoartelor de calitate și acoperire pentru deriva
schemei. Importul integral de date reale și dashboard-ul rămân de realizat.
Vezi [verificarea M1](docs/M1-VERIFICATION.md) și
[verificarea M2](docs/M2-VERIFICATION.md).

Cele două ediții ONRC sunt aprobate pentru dezvoltare, cu validare integrală
obligatorie înainte de publicare. Interfața vizuală necesită
aprobarea unei versiuni Figma înainte de implementare. Lista separată a
livrabilelor rămase este în [docs/CHECKPOINT.md](docs/CHECKPOINT.md).
Ghidul M2, limitele și pașii pentru un import real viitor sunt în
[docs/M2-ETL.md](docs/M2-ETL.md). [DATA.md](DATA.md) rezumă proveniența,
eșantioanele verificate și limitele datelor. Protocolul de măsurare pe date
sintetice este în [docs/M2.1-BENCHMARK.md](docs/M2.1-BENCHMARK.md).

## Stack și arhitectură

- **Frontend** — React, TypeScript și Vite.
- **Backend** — Python și FastAPI.
- **Persistență** — MySQL, SQLAlchemy și PyMySQL, cu migrări Alembic.
- **Servicii locale** — Docker Compose.

Serviciul de migrare pregătește baza MySQL înainte de pornirea API-ului. ETL-ul
validează datele și pregătește snapshoturile în MySQL, apoi le publică numai
după aprobare explicită. Frontendul are deocamdată infrastructura de build.
Vezi [stackul aprobat în D-003](docs/agents/DECISIONS.md#d-003--companywatch-technical-stack),
[diagrama serviciilor Docker](docs/agents/ARCHITECTURE.md#m1-runtime-and-m2-components)
și [diagrama fluxului de import și publicare](docs/agents/ARCHITECTURE.md#m2-ingest-and-publication).

## Cerințe de instalare

- Git pentru clonare.
- Docker Engine sau Docker Desktop pornit, cu Docker Compose v2 sau ulterior și
  suport pentru `docker compose up --wait`.
- Acces la registrul imaginilor Docker și la registrele Python/npm la primul build.
- Python 3.11 sau ulterior pe host doar pentru scriptul complet de verificare.
- Bash și curl pentru exemplele de mai jos.

Nu trebuie instalate local Node, MySQL sau serverul Python. Serverele rulează
exclusiv în Docker. Imaginile sunt fixate prin digest, iar dependențele prin
`backend/requirements.lock` și `frontend/package-lock.json`.

## Instalare și configurare

```bash
git clone https://github.com/Fleseriu-Stefan/p28-companywatch.git
cd p28-companywatch
test -e .env || cp .env.example .env
chmod 600 .env
```

`.env.example` conține doar configurația fără secrete. Pentru dezvoltarea locală,
utilizatorul a autorizat păstrarea parolelor MySQL în `.env`, generat o singură
dată, ignorat de Git și cu permisiuni `600`. Instalarea locală curentă folosește
această variantă; Compose citește fișierul automat. Nu suprascrie un `.env`
existent și nu regenera parolele unei baze deja inițializate.

Pentru o instalare nouă fără parole configurate în `.env`, poți furniza
credențialele prin variabile exportate, folosind două valori distincte:

```bash
read -rsp 'Parola utilizatorului MySQL: ' MYSQL_PASSWORD
echo
export MYSQL_PASSWORD
read -rsp 'Parola root MySQL: ' MYSQL_ROOT_PASSWORD
echo
export MYSQL_ROOT_PASSWORD
```

Nu afișa parolele și nu le salva în fișiere versionate, loguri sau istoricul
comenzilor. `.env` local privat este excepția autorizată. Compose refuză pornirea
dacă lipsesc credențialele. API-ul și migrările folosesc utilizatorul aplicației, nu root.
Root este folosit de imaginea MySQL la inițializare. La repornirea cu un volum
existent trebuie furnizate aceleași credențiale; schimbarea variabilelor nu schimbă
automat parolele salvate de MySQL.

## Build și pornire

Cu parolele din `.env` privat sau cu variabilele exportate în terminal, folosește
proiectul M2 separat. Portul 8001 din exemplu permite rularea alături de M1.

```bash
docker compose -p companywatch-m2 build api frontend
API_PORT=8001 COMPANYWATCH_M2_MIGRATE=1 docker compose -p companywatch-m2 up -d --wait --wait-timeout 180 api
docker compose -p companywatch-m2 ps -a
```

Ordinea este `db` sănătos → `migrate` terminat cu succes → `api` disponibil.
Proiectul `companywatch-m2` are propriul volum persistent, `companywatch-m2_mysql_data`.
Volumul `companywatch_mysql_data` aparține proiectului M1 `companywatch`.
Serviciul de migrare cere `COMPANYWATCH_M2_MIGRATE=1` și refuză proiectul M1.
MySQL folosește rețeaua internă Compose. API-ul ascultă pe loopback cu portul
configurat prin `API_PORT`.

```bash
curl --fail http://127.0.0.1:8001/health/live
curl --fail http://127.0.0.1:8001/health/ready
```

Contractul endpointurilor este definit în
[C-001](docs/agents/CONTRACTS.md#c-001--health-and-api-documentation).
Documentația interactivă este la [localhost:8001/docs](http://127.0.0.1:8001/docs),
iar OpenAPI la [localhost:8001/openapi.json](http://127.0.0.1:8001/openapi.json).
Acestea sunt documentația tehnică FastAPI; dashboard-ul nu este implementat.

## Frontend fără interfață vizuală

```bash
docker compose run --rm --no-deps frontend
```

Comanda rulează ESLint, TypeScript și build-ul Vite într-un container. Intrarea
React randă `null`: nu există componente demonstrative, CSS, grafice sau pagini.
Serviciul este o unealtă de build și nu expune un server web. Artefactele build-ului
din acest container temporar nu sunt publicate sau exportate pe host.

## Acces la API

Dashboardul poate folosi `/api/web/v1` fără cheie. Clienții externi folosesc
aceleași operații de citire sub `/api/v1` și trimit cheia în `X-API-Key`.
Swagger UI la `/docs` permite autorizarea cu o cheie. Pentru conturile de
administrator și curator, sesiunea este disponibilă prin HTTPS. Vezi
[contractul C-004](docs/agents/CONTRACTS.md#c-004--operator-sessions-and-api-access)
și [procedura de bootstrap](docs/DEPLOY.md#6-bootstrap-the-first-administrator).

## Migrări

```bash
COMPANYWATCH_M2_MIGRATE=1 docker compose -p companywatch-m2 run --rm migrate
docker compose -p companywatch-m2 run --rm --no-deps tests alembic current
```

Migrările nu rulează în fiecare worker API. Serviciul `migrate` este responsabil
de aplicarea lor; un eșec blochează pornirea API. Readiness verifică accesul SQL
și corespondența dintre revizia bazei și revizia aplicației.

După aprobarea unei schimbări viitoare de schemă, o nouă revizie se adaugă în
`backend/migrations/versions/`, este verificată pe MySQL și intră în imagine prin
rebuild. Nu se folosește `create_all()` pentru a ocoli migrările.

## Teste și verificări

Verificarea completă, recomandată atât local cât și în CI:

```bash
python3 scripts/verify.py
```

Nu necesită parolele tale: scriptul generează credențiale temporare în memorie,
folosește un proiect Compose cu nume aleator și port API dinamic. Verifică
numele proiectului, volumul și mount-ul MySQL înainte de testele cu baza de date.
La final curăță resursele proiectului verificat și tagurile de imagini generate
pentru rulare. Cache-ul de build rămâne disponibil local.

Verificările includ ledger, Docker build, Ruff, teste API/configurare/ETL, MySQL real,
migrări repetate, schemă incompatibilă, oprire/revenire DB, persistență după
recrearea containerelor și blocarea API la eșecul migrării. Sunt incluse verificarea
istorică `0001_baseline`, upgrade-ul M2 fără pierdere de date și 100.001 rânduri
sintetice, fără rețea ONRC în teste. Eșecul cu codul 17 din
scenariul de migrare este injectat intenționat și trebuie urmat de recuperare.

Verificări individuale, pe configurația locală:

```bash
python3 docs/agents/tools/ledger-lint.py
docker compose run --rm --no-deps tests ruff check .
docker compose run --rm --no-deps tests ruff format --check .
docker compose run --rm --no-deps tests pytest -q -m 'not integration'
docker compose run --rm --no-deps frontend
```

Testele marcate `integration` modifică revizia Alembic pentru scenarii negative.
Rulează-le prin `scripts/verify.py`, care asigură o bază izolată. Reaplicarea unei
migrări nu constituie dovadă de ingestie ETL idempotentă.

Workflow-ul [.github/workflows/ci.yml](.github/workflows/ci.yml) execută aceeași
verificare la pull request și push pe `main`, cu permisiune `contents: read`.
Workflow-ul verifică aplicația fără deploy și folosește credențiale generate pentru
baza izolată de test.

## Oprire și diagnostic

```bash
docker compose -p companywatch-m2 logs --tail 100 api migrate
docker compose -p companywatch-m2 stop
API_PORT=8001 COMPANYWATCH_M2_MIGRATE=1 docker compose -p companywatch-m2 up -d --wait --wait-timeout 180 api
docker compose -p companywatch-m2 down
```

Oprirea și `down` păstrează volumul MySQL. Nu adăuga opțiunea de eliminare a
volumelor pentru baza de dezvoltare dacă vrei să păstrezi datele. Nu distribui
configurația Compose expandată sau ieșirea `docker inspect`, deoarece pot include
valorile mediului. Endpointurile de health nu returnează detalii SQL sau parole.

Dacă readiness nu revine, verifică starea `db`, rezultatul `migrate`, credențialele
folosite la inițializarea volumului și portul local. Remediază migrarea înainte de
a reporni API-ul; nu modifica manual revizia ca să maschezi eroarea.

## Structură

| Cale | Rol |
|---|---|
| `backend/app/` | FastAPI, configurare, conectare SQL și health |
| `backend/migrations/` | Istoricul Alembic |
| `backend/tests/` | Teste unitare și integrare |
| `frontend/` | React/TypeScript/Vite, fără UI |
| `compose.yaml` | Servicii și unelte Docker |
| `scripts/verify.py` | Verificare izolată completă |
| `docs/agents/` | [Arhitectura M1 și M2](docs/agents/ARCHITECTURE.md), decizii, contracte, patterns și întrebări |
| `docs/design/` | Reguli și viitoare designuri aprobate |
| `docs/CHECKPOINT.md` | Livrabilele încă lipsă |
