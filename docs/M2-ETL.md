# CompanyWatch M2 — pipeline și primul import real

M2 este implementat și verificat inițial cu fixtures sintetice și MySQL izolat.
Ediția ONRC din 19.10.2026 a fost descărcată integral într-un tmpfs protejat pentru
o încercare autorizată, dar ingestia s-a oprit înainte de validarea completă;
ediția din 04.11.2026 nu a fost descărcată integral. Baza locală de dezvoltare M1
nu a fost migrată. Acest ghid nu autorizează o nouă descărcare sau publicarea.

## Surse și selecție

Sursele aprobate pentru dezvoltare sunt edițiile `2026-10-19` și `2026-11-04` ale
OD_FIRME.CSV. [ONRC-SOURCE.md](ONRC-SOURCE.md) documentează URL-urile, licența,
eșantioanele, dialectul și dovezile clasificării. Nici numărul total de rânduri,
nici minimum 100.000 de persoane juridice eligibile per export nu sunt presupuse.

Subsetul inițial admite doar formele exacte `SRL`, `SA`, `SNC` împreună cu seria
`J`. Seria `F` cu formele persoanelor fizice este exclusă. Sucursalele, țara firmei
mamă completată, formele necunoscute și contradicțiile sunt carantinate fără
păstrarea denumirii sau a adreselor lor. Este o selecție conservatoare, nu o
clasificare exhaustivă a tuturor persoanelor juridice din registru.

Se păstrează numai EUID, CUI, numărul de înmatriculare, denumirea, forma juridică,
județul, localitatea și data înmatriculării. Adresele detaliate și WEB nu intră în
staging sau snapshoturi. Golul CSV este reprezentat prin SQL NULL; textul literal
`NULL` nu este convertit. Nu se elimină spații, majuscule sau diacritice din valori.
Data sursă este validată ca dată sau dată cu oră și păstrată fără trunchiere.
EUID/registrația au limită tehnică de 255 caractere; CUI/data, de 64. Depășirile
sunt raportate, niciodată trunchiate silențios. Limita standard a parserului CSV
pentru un câmp foarte mare produce eroare de fișier, nu pierdere de conținut.

## Procesare și calitate

1. CLI cere `--allow-real-download` înainte de accesarea rețelei pentru date reale.
2. Downloaderul acceptă numai HTTPS pe data.gov.ro, verifică fiecare redirect,
   are timeout de 30 secunde și cel mult trei încercări pentru erori tranzitorii.
   Transferul este streaming, în blocuri de 64 KiB, cu maximum 1 GiB per fișier.
   Nu încearcă resume/append; un răspuns parțial 206 nu este tratat ca fișier complet.
3. SHA-256 este calculat incremental. Dimensiunea resursei aprobate și eventualul
   Content-Length trebuie să corespundă transferului. `--expected-sha256` permite
   verificarea unei amprente independente, dacă există. ONRC nu a publicat un hash
   în metadatele investigate; hash-ul local identifică bytes primiți, nu dovedește
   independent autenticitatea lor.
4. Parserul validează BOM, UTF-8 strict, antetul exact de 20 de coloane, separatorul
   `^`, ghilimelele literale și lățimea fiecărui rând. Erorile de schemă/decodare
   invalidează întregul import. Nu se face ALTER TABLE după antetul unui fișier.
5. Staging-ul primește loturi de maximum 1.000 de rânduri. Datele excluse nu sunt
   copiate în coloanele de companii. Pentru a detecta EUID repetat oriunde în sursă,
   inclusiv într-un rând exclus/necunoscut, staging-ul folosește HMAC-uri temporare
   cu o cheie aleatoare numai în memoria workerului. Identificatorii excluși nu
   sunt salvați; amprentele nu sunt reutilizabile între importuri.
6. EUID lipsă, nepotrivit cu înmatricularea sau duplicat este carantinat. Toți
   membrii unui grup duplicat sunt respinși; nu există last-write-wins. CUI `0`
   este păstrat și raportat ca problemă, fără utilizare ca identitate. Numele lipsă,
   datele calendaristice invalide și depășirile limitelor sunt raportate.
7. Raportul reconciliază `source_records = accepted_records + quarantined_records
   + excluded_records`, cu motive, câmpuri nule, CUI zero și grupuri duplicate.
   Numărul pe motiv poate suprapune alte motive; nu se însumează ca total de rânduri.
   Sunt păstrate maximum 20 de exemple cu ordinal/cod, fără chei sau valori brute.
8. Rapoartele noi, cu `quality_format: 1`, includ distribuțiile
   `source_legal_forms` și `accepted_legal_forms`. Prima cuprinde toate
   rândurile parsate în categoriile SRL, SA, SNC, `missing` și `other`.
   Valorile necunoscute nu apar în raport. A doua numără SRL, SA și SNC după
   validare și carantinarea duplicatelor. Totalurile corespund cu
   `source_records`, respectiv `accepted_records`.
9. La succes, rândurile pregătite rămân private în starea `loading` cât timp
   staging-ul este șters în loturi. Raportul complet, amprentele și stările
   `review` și `ready` devin vizibile împreună. La un eșec recunoscut în
   parsare, validare sau calculul amprentei, workerul poate înregistra stările
   `failed` numai dacă sesiunea MySQL rămâne validă și deține lock-ul de
   ingestie până la tranzacția finală. O deconectare sau pierderea lock-ului
   poate întrerupe curățarea înainte de înregistrarea raportului de eroare și
   poate lăsa încercarea în `loading` pentru recuperarea M2.3B.
   Vezi [finalizarea M2.3C](#m23c--finalizare-și-curățare-la-eșec).

Cele cinci tabele M2 sunt `etl_versions` (inclusiv manifest și raport),
`etl_attempts`, `etl_staging_rows`, `company_version_rows`, `dataset_publications`.
Nu există un tabel suplimentar pentru raportul care aparține unei singure versiuni.

## Stocare temporară și recuperare

Serviciul `etl` folosește `/etl-private` ca tmpfs de 1 GiB, mod 0700, proprietarul
utilizatorului containerului. Fișierele au mod 0600. CLI refuză ingestia reală dacă
mount-ul nu este tmpfs protejat. Artefactele se șterg după procesare, inclusiv la
excepții; la oprirea forțată a containerului mount-ul dispare. Nu se folosește
volum persistent pentru raw și nu se exportă bytes sursă pe host.

Primul import real necesită bugetul de memorie pentru aproximativ 697 MB raw în
tmpfs, plus memoria procesului/MySQL. Spațiul MySQL pentru staging, snapshoturi și
indexuri se dimensionează separat; 1,39 GB este numai suma celor două fișiere raw,
care sunt procesate pe rând. Dacă resursa depășește dimensiunea aprobată, importul
se oprește, fără schimbarea automată a limitelor sau profilului.

Un lock MySQL de sesiune pe identitatea inputului serializează ingestia aceluiași
conținut. Aceeași conexiune verifică lock-ul și execută fiecare tranzacție de
ingestie. Un concurent primește `version_busy` cât timp lock-ul este deținut.
Dacă sesiunea pierde lock-ul, workerul se oprește cu `ingest_lock_lost`. La
reingestia aceluiași conținut, noul deținător marchează încercarea `loading`
ca `abandoned` și reface staging-ul.

Identitatea este resource ID + tip real/sintetic + SHA-256 complet + versiunea
transformării. Schimbarea regulilor de transformare cere un nou `PROFILE_VERSION`.
Reingestia identică în `review`/`approved`/`published` reutilizează versiunea și
înregistrează încercarea; nu dublează companiile.

### M2.2 — timeout de citire și încercare întreruptă

În încercarea izolată pentru ediția din 19.10.2026, toate cele 4.229.451 de rânduri
sursă au ajuns în staging. Operația `count_duplicate_groups` a pierdut conexiunea
după 2005,2 ms (cod MySQL 2013), iar CLI a raportat `ingest_lock_lost`. MySQL a
rămas sănătos, fără restart sau OOM. Versiunea și încercarea au rămas în `loading`,
fără rânduri pregătite și fără schimbarea pointerului de publicare. Nu există încă
raport complet de calitate sau număr verificat de persoane juridice acceptate.

Diagnosticarea separată, doar în baza izolată, a verificat schema `0002_etl` și
indexul `(version_id, key_digest)`. `EXPLAIN FORMAT=JSON` a arătat o scanare de
interval acoperită de index, urmată de materializarea grupurilor într-un tabel
temporar, fără filesort. Interogarea exactă a numărului de grupuri duplicate a
returnat 4.713 grupuri în 23,16 s timp de perete, incluzând pornirea clientului,
cu limită MySQL de 120 s numai pentru sesiunea de diagnostic și termen client de
135 s. Această durată depășește timeoutul de citire PyMySQL de 2 s folosit inițial
de ETL și explică pierderea conexiunii. Nu este un benchmark al diff-ului SQL și
nu dovedește validarea completă a fișierului.

M2.2 păstrează timeoutul implicit de citire de 2 s pentru API și comenzile CLI
altele decât `ingest`. Numai `etl ingest` folosește 120 s; timeouturile de
conectare/scriere, cel al pool-ului și verificarea lock-ului rămân neschimbate.
Limita de 120 s este finită. Dacă o operație atinge această limită într-o nouă
încercare autorizată, oprește importul și reexaminează planul, fără creșteri
automate ale timeoutului.

Rândurile păstrate în staging nu se reiau din mijloc. Cheia HMAC a încercării și
contoarele parserului erau numai în memoria workerului. La o reingestie autorizată
a aceluiași conținut, noul deținător al lock-ului marchează încercarea veche
`abandoned`, șterge staging-ul incomplet și reface parsarea, validarea și raportul
integral sub aceeași identitate de versiune. Nu rula această recuperare pe volumul
de dezvoltare și nu aproba sau publica versiunea rămasă în `loading`.

### M2.3A — starea după a doua încercare

A doua încercare a ajuns la `prepare_attempt` și a pierdut conexiunea după
120.067 ms (cod 2013). Docker a trimis SIGKILL la aproximativ 3,02 s după
SIGTERM. Diagnosticul autorizat ulterior a pornit doar MySQL din proiectul
izolat și a verificat starea după recuperarea InnoDB. Versiunea de octombrie
și singura sa încercare erau încă `loading`, cu 4.229.451 de rânduri în staging,
zero rânduri pregătite, fără sigilii și cu pointerul de publicare nul.
Valoarea JSON a raportului nu a fost inspectată. Nicio schimbare comisă de a
doua pregătire nu era vizibilă. Ștergerea staging-ului într-o singură
tranzacție rămâne ipoteza principală. Logul acelei încercări nu identifică
instrucțiunea SQL exactă.

### M2.3B — curățare la reluarea ingestiei

O tranzacție scurtă actualizează încercările abandonate și înregistrează
noua încercare în starea `loading`. Urmează tranzacții separate pentru loturi
de cel mult 1.000 de rânduri din staging sau din snapshotul nepregătit pentru
review. Aceeași sesiune MySQL păstrează lock-ul de ingestie. Fiecare
tranzacție verifică lock-ul, starea versiunii și pointerul de publicare
înainte de ștergere. Versiunile `review`, `approved`, `published` și
sigiliile lor sunt păstrate. Parsarea reîncepe după ce ambele selecții
limitate nu mai returnează rânduri pentru versiunea în lucru.

La întrerupere, loturile comise rămân șterse. Următorul worker care obține
lock-ul continuă cu rândurile rămase. Pierderea lock-ului sau a conexiunii
oprește workerul. Erorile înainte de parsare nu intră în curățarea folosită
după un eșec al ingestiei. Logurile disting selecția, ștergerea și erorile
de commit sau rollback și păstrează doar eticheta, rezultatul, durata și
codul numeric al driverului, când există. Limita de citire rămâne 120 s
pentru ingestie.

În MySQL 8.4.13, un test sintetic cu trei versiuni intercalate a șters
60.001 de rânduri de staging și 8.001 rânduri pregătite în 70 de loturi
comise. Curățarea a durat 1.879 ms, dintre care aproximativ 27 ms pentru
capturarea planurilor. Selecțiile au folosit indexul
`ix_etl_staging_version_key` și cheia primară a snapshoturilor. Celelalte
versiuni și pointerul au trecut comparația de conținut înainte și după.
Rezultatul susține limita de 1.000 de rânduri pe configurația măsurată.

### M2.3C — finalizare și curățare la eșec

Finalizarea comite validarea și copierea rândurilor pregătite în timp ce
versiunea și încercarea sunt încă `loading`. Șterge numai staging-ul, în
tranzacții de cel mult 1.000 de rânduri. Workerul calculează amprenta rândurilor
pregătite și verifică numărul lor față de raport fără să țină lock-ul
pointerului de publicare pe durata citirii. Rândurile și raportul complet
devin eligibile pentru revizuire abia când raportul, amprentele și stările
`review` și `ready` sunt comise împreună.

La eșec, workerul capturează raportul agregat înainte de ștergerea în loturi a
staging-ului și a rândurilor pregătite. După golirea ambelor tabele pentru
versiunea vizată, raportul de eroare și stările `failed` sunt comise împreună,
cu o sesiune MySQL validă care încă deține lock-ul de ingestie.
Fiecare lot și tranziția finală folosesc sesiunea care deține lock-ul de
ingestie. Ele verifică pointerul canonic înaintea versiunii și verifică
încercarea activă. Tranziția verifică și prezența sau absența rândurilor
așteptate în cele două tabele. Aprobarea, publicarea, comparația rapoartelor
și citirea snapshoturilor verifică starea versiunii.

O deconectare sau pierderea lock-ului poate opri workerul înainte ca raportul
de eroare să fie înregistrat. Loturile comise rămân șterse, iar o încercare
rămasă în `loading` este reluată prin
[recuperarea M2.3B](#m23b--curățare-la-reluarea-ingestiei).
La o confirmare incertă a commitului final, workerul oprește
scrierile și închide sesiunea. Workerul următor decide pe baza stării
comise dacă reutilizează versiunea sau o reface prin recuperarea M2.3B.

Cele 12 cazuri MySQL au trecut după implementare, după 12 eșecuri așteptate
pe versiunea de bază. Verificarea completă a trecut în proiecte sintetice
izolate, cu oprire grațioasă MySQL și verificarea eliminării resurselor de
test. [Rezultate și condiții de izolare](../AI_LOG.md#m23c-gate-1--bounded-finalization-build).

Limita de citire pentru ingestie este de 120 s. Agregările de duplicate,
actualizarea carantinei, agregările de calitate, copierea rândurilor și
calculul amprentei pot genera încă operații mari. Q-013 și Q-014 rămân
în investigare. Verificarea sintetică la 4.229.451 de rânduri, scalabilitatea
aprobării și publicării și performanța diff-ului real au verificări separate.

Gate 2 (Q-013) va măsura întârzierea purge-ului InnoDB la curățarea de
reluare, la finalizarea cu succes, la curățarea după eșec și la verificarea
finală că staging-ul este gol. Gate 4 va măsura spațiul simultan ocupat de
staging și rândurile pregătite, spațiul pentru undo și rezerva necesară
pentru recuperare după întrerupere.

## Aprobare, publicare și diff

`approve` cere amprenta exactă a raportului, verifică rezultatul complet și minimum
100.000 de rânduri acceptate pentru date reale. Aprobarea leagă manifestul,
SHA-256, profilul/sche­ma, raportul și amprenta rândurilor pregătite. `publish`
cere acea aprobare și reverifică integritatea înainte de a lua lock-ul publicației.
Tranzacția scurtă InnoDB reverifică sigiliul și actualizează pointerul și starea
împreună; nu conține DDL sau încărcarea masivă a rândurilor. Codul nu permite
modificarea rândurilor pregătite după intrarea în review. Accesul administrativ
direct la MySQL rămâne o limită de încredere, nu o API publică.

Versiunile publicate rămân disponibile. Un consumator rezolvă o singură dată
`current_version_id` și folosește acel ID pentru toate interogările operațiunii.
Diff-ul face toate join-urile și numărătorile în SQL: adăugate, dispărute,
modificate, neschimbate și modificări pe câmp. Comparațiile sunt NULL-safe (`<=>`)
și folosesc collation binară `utf8mb4_0900_bin`. Dispariția este relativă la
exportul și subsetul selectat, nu dovadă de radiere. Schimbarea EUID apare ca
dispariție/adăugare; nu există reconciliere automată prin CUI.

Datele sintetice sunt marcate distinct. Publicarea lor și praguri reduse sunt
posibile numai în codul de test care optează explicit pentru aceasta; CLI real nu
oferă opțiuni pentru ocolirea pragului sau publicare sintetică.

### Diff detaliat intern

`with pipeline.diff_details(old_id, new_id) as rows:` permite consumul
incremental al unui rezultat pentru fiecare EUID din reuniunea a două versiuni
publicate. Fiecare rezultat are `euid`, `change_type`, `previous`, `current` și
`changed_fields`. Categoriile sunt `added`, `removed`, `modified` și `unchanged`.
O parte prezentă conține cele opt câmpuri păstrate. Valoarea `None` pentru
întreaga parte indică absența firmei. Un câmp cu `None` indică o valoare SQL NULL.
Numai rândurile modificate au nume de câmpuri schimbate, în ordinea
`RETAINED`. Ordinea rândurilor este nespecificată.

Argumentele stabilesc direcția comparației. Aceeași versiune produce rânduri
neschimbate. Inversarea argumentelor schimbă valorile anterioare/curente și
inversează adăugările și eliminările. Cursorul și conexiunea sunt folosite în
interiorul blocului `with`. Comanda `etl diff` continuă să returneze totalurile.

### Pornirea unui MySQL izolat pentru verificări

Rulează din rădăcina proiectului într-un shell Bash dedicat, cu Python 3,
Docker activ și Compose. Alege `CHECK_KIND=volume` pentru date sintetice sau
`CHECK_KIND=benchmark` pentru un proiect dedicat benchmarkului real, după
autorizarea Q-005. Comenzile generează credențiale numai în mediul shellului.
Păstrează același shell cât timp lucrezi cu volumul.

```bash
set -euo pipefail
set +x
docker version
docker compose version
CHECK_KIND=volume
case "$CHECK_KIND" in
  volume) PROJECT_PREFIX=companywatch-check ;;
  benchmark) PROJECT_PREFIX=companywatch-bench ;;
  *) exit 2 ;;
esac
BENCHMARK_PROJECT="$PROJECT_PREFIX-$(python3 -c 'import secrets; print(secrets.token_hex(8))')"
export COMPOSE_PROJECT_NAME="$BENCHMARK_PROJECT"
export MYSQL_DATABASE=companywatch_test MYSQL_USER=companywatch_test
export MYSQL_PASSWORD="$(python3 -c 'import secrets; print(secrets.token_urlsafe(32))')"
export MYSQL_ROOT_PASSWORD="$(python3 -c 'import secrets; print(secrets.token_urlsafe(32))')"
export COMPANYWATCH_M2_MIGRATE=1
CHECK_VOLUME="${BENCHMARK_PROJECT}_mysql_data"
compose_check() {
  docker compose --env-file .env.example -f compose.yaml -p "$BENCHMARK_PROJECT" "$@"
}
existing_containers=$(docker ps -aq --filter "label=com.docker.compose.project=$BENCHMARK_PROJECT")
existing_volumes=$(docker volume ls --format '{{.Name}}')
existing_networks=$(docker network ls --format '{{.Name}}')
if [[ -n "$existing_containers" ]] ||
   grep -Fxq "$CHECK_VOLUME" <<<"$existing_volumes" ||
   grep -Fxq "${BENCHMARK_PROJECT}_default" <<<"$existing_networks"; then
  echo "Proiectul, volumul sau rețeaua există deja." >&2
  exit 1
fi
verify_check_mount() {
  local container mount owner
  container=$(compose_check ps -q db) || return 1
  test -n "$container" || return 1
  mount=$(docker inspect --format '{{index .Config.Labels "com.docker.compose.project"}} {{range .Mounts}}{{if eq .Destination "/var/lib/mysql"}}{{.Type}} {{.Name}}{{end}}{{end}}' "$container") || return 1
  owner=$(docker volume inspect --format '{{index .Labels "com.docker.compose.project"}} {{index .Labels "com.docker.compose.volume"}}' "$CHECK_VOLUME") || return 1
  test "$mount" = "$BENCHMARK_PROJECT volume $CHECK_VOLUME" &&
    test "$owner" = "$BENCHMARK_PROJECT mysql_data"
}
compose_check config --quiet
compose_check build api
compose_check up -d --wait --wait-timeout 180 db
verify_check_mount
compose_check run --rm --no-deps migrate
```

Serviciul `tests` se conectează la `db:3306` prin rețeaua proiectului, cu
utilizatorul aplicației. Păstrează verificarea de izolare înainte de test,
benchmark și curățare. La final, elimină volumul temporar numai dacă
`verify_check_mount` reușește, apoi rulează
`compose_check down --volumes --timeout 5`. Reține volumul dedicat cât timp
ai nevoie de edițiile autorizate. Volumele de dezvoltare și cel M1 sunt în
afara acestei proceduri.

### Verificarea sintetică de volum

În proiectul `companywatch-check-*` pregătit mai sus, rulează testul separat de
`python3 scripts/verify.py` și de CI obișnuit:

```bash
verify_check_mount
compose_check run --rm --no-deps -e COMPANYWATCH_DIFF_VOLUME=1 tests pytest -q -s \
  tests/test_etl_database.py::test_diff_details_two_large_published_editions
```

Testul generează și publică două ediții sintetice de câte 100.001 rânduri
acceptate. Verifică toate totalurile și reingestia identică, afișează durata
consumului complet cu timeoutul aplicației, vârful alocărilor Python măsurat
separat cu `tracemalloc` și planul integral `EXPLAIN ANALYZE`. Alocările
Python măsurate exclud RSS-ul și memoria MySQL. CI păstrează verificarea
existentă pentru o singură ediție și testele de diff cu seturi mici.

### Benchmark pe ediții reale publicate

Folosește proiectul `companywatch-bench-*` pregătit mai sus numai după
autorizarea separată a validării și publicării. Confirmă două ediții reale
distincte publicate cu cel puțin 100.000 de rânduri acceptate fiecare și
setează `OLD_VERSION` și `NEW_VERSION` la ID-urile lor. Activează
instrumentarea pe instanța izolată și permite citirea datelor de măsurare
utilizatorului proiectului:

```bash
verify_check_mount
compose_check exec -T db sh -c 'MYSQL_PWD="$MYSQL_ROOT_PASSWORD" exec mysql --user=root' <<'SQL'
UPDATE performance_schema.setup_consumers SET ENABLED = 'YES'
WHERE NAME IN ('global_instrumentation', 'thread_instrumentation',
               'events_statements_current', 'events_statements_history');
UPDATE performance_schema.setup_instruments SET ENABLED = 'YES', TIMED = 'YES'
WHERE NAME = 'statement/sql/select';
GRANT SELECT ON performance_schema.threads TO 'companywatch_test'@'%';
GRANT SELECT ON performance_schema.events_statements_history TO 'companywatch_test'@'%';
SQL
compose_check run --rm --no-deps tests \
  python -m tests.benchmark_etl_diff "$OLD_VERSION" "$NEW_VERSION"
```

Performance Schema trebuie să fie pornit, cu istoric per fir disponibil.
Runnerul verifică existența unui eveniment complet și temporizat pentru
instrucțiunea de detaliu la fiecare rulare. Derulează o încălzire și trei
rulări complete. Raportează separat timpul instrucțiunii MySQL și timpul
monotonic până la ultimul rând mapat în Python. Un timeout de citire de 120 s
se aplică numai conexiunilor runnerului. Raportul include volumele, totalurile
reconciliate, rulările care ating sau depășesc 30 s și `EXPLAIN ANALYZE`.
Consemnează și comanda, revizia și starea codului, digestul imaginii MySQL,
versiunile Docker/Compose, resursele hostului și limitele containerelor,
împreună cu setările instrumentării. Păstrează doar rezultate agregate și
metadate. Durata reală rămâne de verificat conform
[protocolului Q-010](M2.1-BENCHMARK.md#protocol-aprobat-pentru-diff-ul-sql-pe-date-reale).

## Compararea rapoartelor de calitate

`etl quality-compare OLD_VERSION NEW_VERSION` citește două versiuni alese
explicit. Acceptă rapoarte complete și sigilate din stările `review`,
`approved` și `published`. Comparația cere același tip de input, profil,
amprentă de schemă și format de raport. Dacă un raport vechi nu are noii
indicatori, rezultatul este `unavailable`, cu motivul `legacy_report`.
Reingestia identică păstrează raportul existent și sigiliile lui.

Rezultatul include diferențe semnate între numărători și diferențe de rată în
puncte procentuale. Ratele de acceptare, excludere, carantină și duplicate
folosesc totalul rândurilor sursă din fiecare ediție. Distribuțiile folosesc
totalul rândurilor sursă, respectiv acceptate. Rezultatul include ambii
numitori, iar diferența de rată este `null` dacă un numitor este zero.

Comparația poate semnala apariția duplicatelor de la zero, scăderea numărului
de rânduri acceptate la zero sau o scădere de cel puțin 40% față de un număr
anterior pozitiv, când numărul curent rămâne pozitiv. Pragul relativ de 40%
este o regulă ilustrativă inițială inspirată de cerințele P28 și nu a fost
validat statistic. Semnalele sunt consultative. Comanda citește rapoartele
fără a aproba, respinge sau publica versiuni ori a modifica pointerul.

## Deriva schemei și revizuirea propusă a mapării

Antetul aprobat, separatorul și codificarea sunt verificate înainte de
publicare. O diferență oprește importul. Raportul de eșec consemnează codul
problemei și identificatorii versiunii, fără a afișa valorile sursă.

Flux propus pentru o etapă ulterioară, cu rolul și autoritatea curatorului
încă de confirmat (Q-001 și Q-006):

1. Un operator identifică ediția și amprenta antetului ordonat. Anexează
   dovezi pentru sensul coloanelor schimbate și teste sintetice.
2. Curatorul verifică maparea explicită către câmpurile canonice. Respinge
   mapările ambigue, duplicatele de antet, inventarea EUID și eliminarea
   câmpurilor necesare identificării sau clasificării.
3. O mapare aprobată urmează poarta Graffino pentru schimbarea parserului.
   Implementarea ulterioară folosește un profil nou, revalidează intrarea
   integrală și pregătește o versiune nouă. Aprobarea raportului și publicarea
   rămân două acțiuni manuale distincte.

M2.1 documentează fluxul și testează blocarea derivei cu profilul actual.
Mapările la rulare și validarea datelor reale rămân deschise.

## Verificări fără import real

```bash
python3 scripts/verify.py
docker compose run --rm etl sources
docker compose run --rm etl --help
```

Prima comandă creează baze/volume izolate cu prefix aleator și curăță numai
proiectul propriu. Nu folosește baza de dezvoltare și nu descarcă ONRC. Testele
de integrare refuză baze care nu au nume de test și contextul proiectului izolat.
Baseline-ul `0001_baseline` este verificat înainte de `0002_etl`; un marker creat
numai în baza de test demonstrează păstrarea datelor la upgrade. Downgrade-ul M2
este refuzat, deoarece ar șterge snapshoturi și necesită un plan aprobat separat.

După o întrerupere DDL, reia migrarea online numai în proiectul M2 autorizat.
Revizia verifică obiectele deja create și aplică pașii lipsă dacă structura
corespunde. O diferență de schemă oprește migrarea și indică obiectul pentru
investigare. Păstrează volumul pentru diagnostic. SQL-ul Alembic offline este
pentru o instalare nouă și nu poate valida starea unei migrări parțiale.

## O nouă încercare de import real — pași care cer autorizare separată

1. Obține aprobarea explicită pentru descărcările integrale și pentru baza țintă.
2. Reverifică metadatele oficiale, URL-urile, licența și dimensiunile; verifică
   memoria tmpfs și spațiul MySQL. Dacă sursa s-a schimbat, revizuiește profilul.
3. Pentru prima probă folosește un proiect nou, separat de `companywatch`, și
   păstrează `.env` existent privat. De exemplu, după autorizare:

   ```bash
   export COMPOSE_PROJECT_NAME=companywatch-m2-import
   export MYSQL_DATABASE=companywatch_m2
   export API_PORT=8001
   docker compose build api
   COMPANYWATCH_M2_MIGRATE=1 docker compose up -d --wait --wait-timeout 180 api
   docker compose run --rm --no-deps etl ingest --edition 2026-10-19 --allow-real-download
   ```

4. Din JSON-ul întors, preia ID-ul versiunii și amprenta raportului în variabilele
   `VERSION_ID` și `REPORT_HASH`. Inspectează raportul și toate motivele de
   carantină/excludere. Aceste amprente nu sunt parole sau credențiale.

   ```bash
   docker compose run --rm --no-deps etl report "$VERSION_ID"
   docker compose run --rm --no-deps etl approve "$VERSION_ID" --report-hash "$REPORT_HASH"
   ```

5. Numai după decizia manuală de publicare, preia amprenta returnată în
   `APPROVAL` și execută `etl publish "$VERSION_ID" --approval "$APPROVAL"` prin
   același `docker compose run --rm --no-deps`. Repetă fluxul pentru `2026-11-04`.
6. Compară cele două ID-uri publicate prin `etl diff "$OLD_VERSION" "$NEW_VERSION"`
   și păstrează rapoartele agregate. Nu publica fișierele brute.
7. Upgrade-ul bazei existente, dacă va fi dorit ulterior, necesită autorizare și
   backup/plan de revenire confirmat. Nu se șterge sau reinițializează volumul M1.

Executarea importului nu aprobă automat publicarea. Nu există UI nou, endpointuri
de date, interviu sau deploy în acest milestone.
