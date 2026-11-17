# CompanyWatch — ce lipsește pentru checkpoint

Acest document urmărește cerințele comunicate de utilizator. Nu reprezintă o
confirmare a întregii grile a profesorului; grila completă nu a fost furnizată.
M1 livrează fundația tehnică locală. Starea execuției verificărilor este în
[M1-VERIFICATION.md](M1-VERIFICATION.md).

| Livrabil | Stare după implementarea M1 | Dovezi necesare în etapa următoare |
|---|---|---|
| Structură React/FastAPI/MySQL și Docker | Implementată local | Verificările M1 și rularea reproductibilă |
| API documentat | Health și OpenAPI implementate | Endpointurile ETL și de analiză după aprobarea datelor |
| Dataset public real, minimum 100.000 de rânduri | Neimplementat; ONRC este doar candidat | URL sursă, licență, schema observată și număr măsurat de rânduri |
| Două versiuni reale | Neverificate | Resurse autentice, date de publicare și checksum-uri; nu copii modificate artificial |
| Ingestie idempotentă | Neimplementată | Cheie validată, regulă de deduplicare, teste de reingestie fără duplicări |
| Rapoarte de calitate | Neimplementate | Reguli aprobate și rapoarte calculate pe date reale |
| Diff calculat în SQL | Neimplementat | Interogări și teste pentru inserări, ștergeri și modificări între versiuni |
| Detectarea schimbărilor de schemă | Neimplementată | Compararea schemelor sursei și comportament aprobat la schimbări |
| Dashboard interactiv | Blocat de aprobarea designului | Cerințe, versiune Figma aprobată, mock-uri locale, tokens și screenshots |
| Interviu | Nerealizat în acest repository; fără rezultate furnizate | Cerința exactă, interviu real și concluzii bazate pe dovezi |
| Deploy pe URL public | Neimplementat și neautorizat | Hosting confirmat, configurație, aprobare explicită de deploy și URL verificabil |

## ONRC

Nu au fost verificate în M1 resurse ONRC, schema, licența, volumele sau versiunile.
Nu există tabele, importuri sau exemple prezentate ca date ONRC reale.
Selectarea sursei rămâne Q-005 în [registrul întrebărilor](agents/OPEN-QUESTIONS.md).
Validarea datelor precedă proiectarea schemei de domeniu.

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
2. Verificarea și aprobarea datasetului și a celor două versiuni reale.
3. Aprobarea schemei, regulilor ETL, calității și diff-ului SQL.
4. Aprobarea designului Figma și a procedurii de verificare UI.
5. Implementarea și verificarea fluxului complet.
6. Aprobarea și efectuarea unui deploy public.

Această ordine este o propunere de lucru viitor, nu autorizare de implementare.
