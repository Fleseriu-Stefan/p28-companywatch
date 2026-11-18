# CompanyWatch — ce lipsește pentru checkpoint

Acest document urmărește cerințele comunicate de utilizator. Nu reprezintă o
confirmare a întregii grile a profesorului; grila completă nu a fost furnizată.
M1 este integrat în `main`, la `c5c0b71`. Baza M1 a rămas la revizia
`0001_baseline` pe volumul original la verificarea M2. M2 este integrat în
`main`, la `b8a2b6f`. Verificările CI pe `main` au trecut pentru ambele
milestone-uri. Rularea locală completă M2 a trecut 46 de teste cu date sintetice
și MySQL izolat. Vezi [M1-VERIFICATION.md](M1-VERIFICATION.md) și
[M2-VERIFICATION.md](M2-VERIFICATION.md).

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
| Dashboard interactiv | Blocat de aprobarea designului | Cerințe, versiune Figma aprobată, mock-uri locale, tokens și screenshots |
| Interviu | Nerealizat în acest repository; fără rezultate furnizate | Cerința exactă, interviu real și concluzii bazate pe dovezi |
| Deploy pe URL public | Neimplementat și neautorizat | Hosting confirmat, configurație, aprobare explicită de deploy și URL verificabil |

## ONRC

În M2 au fost verificate metadatele oficiale, URL-urile și eșantioane limitate,
inclusiv 100.000 de rânduri parsabile per ediție. [ONRC-SOURCE.md](ONRC-SOURCE.md)
descrie dovezile și limitele. Numărul de persoane juridice eligibile după filtrare
rămâne necunoscut. Q-005 blochează publicarea până la validarea integrală.
Nu există rezultate de import real, checksum-uri integrale sau diff real inventate.

## Interviu

Nu există răspunsuri sau rezultate de interviu. Trebuie confirmate formatul și
cerința profesorului, apoi realizat și documentat interviul real (Q-006).
Nu se introduc date personale în repository; forma dovezilor trebuie să respecte
regulile proiectului.

## Publicare

Adresa locală din README nu este un URL public. CI verifică aplicația și nu o
publică. Alegerea hostingului și aprobarea deploy-ului rămân Q-007. Orice server
folosit ulterior trebuie să respecte D-001.

## Ordine propusă pentru etapele viitoare

1. Confirmarea grilei profesorului și a livrabilului de interviu.
2. Autorizarea importului integral și validarea celor două ediții ONRC.
3. Verificarea rapoartelor de calitate și a diff-ului SQL pe edițiile reale,
   după aprobarea publicării lor.
4. Aprobarea designului Figma și a procedurii de verificare UI.
5. Implementarea și verificarea fluxului complet.
6. Aprobarea și efectuarea unui deploy public.

Această ordine este o propunere de lucru viitor, nu autorizare de implementare.
