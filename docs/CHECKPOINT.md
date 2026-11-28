# CompanyWatch — ce lipsește pentru checkpoint

Acest document păstrează stadiul inițial M1 și M2. Cerințele obligatorii confirmate
de proprietarul proiectului, matricea și etapele actuale sunt în
[P28-REQUIREMENTS.md](P28-REQUIREMENTS.md).
M1 este integrat în `main`, la `c5c0b71`. Baza M1 a rămas la revizia
`0001_baseline` pe volumul original la verificarea M2. M2 este integrat în
`main`, la `b8a2b6f`. Verificările CI pe `main` au trecut pentru ambele
milestone-uri. Rularea locală completă M2 a trecut 46 de teste cu date sintetice
și MySQL izolat. Vezi [M1-VERIFICATION.md](M1-VERIFICATION.md) și
[M2-VERIFICATION.md](M2-VERIFICATION.md).

Pentru stadiul ulterior acestui checkpoint, vezi [edițiile publicate](../DATA.md)
și [procedura de deploy pe Azure](DEPLOY.md).

| Livrabil | Stare curentă M1 și M2 | Dovezi necesare în etapa următoare |
|---|---|---|
| Structură React/FastAPI/MySQL și Docker | Integrată în M1 și verificată local | Configurare pentru mediul public după aprobarea lui |
| API documentat | Health și OpenAPI implementate | Endpointurile ETL și de analiză după aprobarea datelor |
| Dataset public real, minimum 100.000 de rânduri | Surse verificate și aprobate pentru dezvoltare; fără import integral | Număr complet măsurat și minimum 100.000 de persoane juridice eligibile per ediție |
| Două versiuni reale | Edițiile 19.10.2026 și 04.11.2026 identificate oficial | Descărcare autorizată, hash-uri integrale și rapoarte reale |
| Ingestie idempotentă | Implementată și testată sintetic | Reingestie reală și confirmarea calității globale EUID |
| Rapoarte de calitate | Implementate; rezultate sintetice | Rapoarte complete pe cele două exporturi reale |
| Diff calculat în SQL | Implementat și testat pe MySQL izolat | Rezultatul pentru versiunile reale publicate manual |
| Detectarea schimbărilor de schemă | Profil strict și blocare implementate | Validarea profilului pe întregul export și review la schimbări |
| Dashboard interactiv | Etapa D încheiată cu aprobarea celor nouă ecrane Draft 1, conform D-002 | Plan de implementare aprobat, dashboard funcțional și verificare vizuală față de [designul aprobat](design/DESIGN.md#etapa-d--registrul-onrc) |
| Interviu | Rezumatul interviului real este în [INTERVIEW.md](../INTERVIEW.md). Auditul Secțiunii C este aprobat. | Feedback real după demonstrația funcțională |
| Deploy pe URL public | Neimplementat și neautorizat | Hosting confirmat, configurație, aprobare explicită de deploy și URL verificabil |

## ONRC

În M2 au fost verificate metadatele oficiale, URL-urile și eșantioane limitate,
inclusiv 100.000 de rânduri parsabile per ediție. [ONRC-SOURCE.md](ONRC-SOURCE.md)
descrie dovezile și limitele. Numărul de persoane juridice eligibile după filtrare
rămâne necunoscut. Q-005 blochează publicarea până la validarea integrală.
Nu există rezultate de import real, checksum-uri integrale sau diff real inventate.

## Interviu

[INTERVIEW.md](../INTERVIEW.md) documentează problema recurentă descrisă de
contabil. Proprietarul proiectului a confirmat scopul și scenariul propus pentru
demonstrație. Validarea scenariului de către contabil și feedbackul său rămân
deschise în [Q-006](agents/OPEN-QUESTIONS.md#q-006--what-interview-evidence-and-checkpoint-rubric-must-be-delivered).

## Publicare

CI verifică aplicația. Q-007 consemnează aprobarea VM-ului Azure și a adresei
publice. Procedura de deploy folosește Docker, conform D-001.

## Etape următoare

Vezi [etapele și dependențele](P28-REQUIREMENTS.md#roadmap) și aprobările
necesare pentru implementare, validarea reală și deploy.
