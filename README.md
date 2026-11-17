# P28 — CompanyWatch

Proiect Tehnologii Web II: ETL + API + Dashboard. M1 implementează fundația
tehnică: FastAPI, MySQL, migrări Alembic, Docker Compose, structură React cu
TypeScript/Vite, teste și CI. Nu există încă ETL, date de domeniu sau dashboard.

ONRC este doar o sursă candidată, neverificată. Interfața vizuală necesită
aprobarea unei versiuni Figma înainte de implementare. Lista separată a
livrabilelor rămase este în [docs/CHECKPOINT.md](docs/CHECKPOINT.md).

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

Cu parolele din `.env` privat sau cu variabilele exportate în terminal:

```bash
docker compose build api frontend
docker compose up -d --wait --wait-timeout 180 api
docker compose ps -a
```

Ordinea este `db` sănătos → `migrate` terminat cu succes → `api` disponibil.
Prima pornire creează baza și volumul persistent. Migrarea inițială creează doar
evidența Alembic; nu există tabele de companii sau schema presupusă a unui dataset.
MySQL nu are port publicat pe host. API-ul ascultă numai pe loopback, implicit pe
portul 8000; `API_PORT` din `.env` poate selecta un alt port local.

```bash
curl --fail http://127.0.0.1:8000/health/live
curl --fail http://127.0.0.1:8000/health/ready
```

Contractul endpointurilor este definit în
[C-001](docs/agents/CONTRACTS.md#c-001--health-and-api-documentation).
Documentația interactivă este la [localhost:8000/docs](http://127.0.0.1:8000/docs),
iar OpenAPI la [localhost:8000/openapi.json](http://127.0.0.1:8000/openapi.json).
Acestea sunt documentația tehnică FastAPI; dashboard-ul nu este implementat.

## Frontend fără interfață vizuală

```bash
docker compose run --rm --no-deps frontend
```

Comanda rulează ESLint, TypeScript și build-ul Vite într-un container. Intrarea
React randă `null`: nu există componente demonstrative, CSS, grafice sau pagini.
Serviciul este o unealtă de build și nu expune un server web. Artefactele build-ului
din acest container temporar nu sunt publicate sau exportate pe host.

## Migrări

```bash
docker compose run --rm migrate
docker compose run --rm --no-deps tests alembic current
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
folosește un proiect Compose cu nume aleator și port API dinamic, apoi șterge doar
containerele, rețeaua și volumul acelui proiect în blocul de cleanup. Nu utilizează
baza de dezvoltare. Imaginile și cache-ul de build rămân disponibile local.

Verificările includ ledger, Docker build, Ruff, teste API/configurare, MySQL real,
migrări repetate, schemă incompatibilă, oprire/revenire DB, persistență după
recrearea containerelor și blocarea API la eșecul migrării. Eșecul cu codul 17 din
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
Nu conține deploy și nu necesită secrete de repository. Execuția pe GitHub va fi
disponibilă după o publicare autorizată; un rezultat local nu este un rezultat CI
executat pe GitHub.

## Oprire și diagnostic

```bash
docker compose logs --tail 100 api migrate
docker compose stop
docker compose up -d --wait --wait-timeout 180 api
docker compose down
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
| `docs/agents/` | Decizii, contracte, patterns și întrebări |
| `docs/design/` | Reguli și viitoare designuri aprobate |
| `docs/CHECKPOINT.md` | Livrabilele încă lipsă |

Nu s-a autorizat commit, merge, push sau deploy prin implementarea M1.
