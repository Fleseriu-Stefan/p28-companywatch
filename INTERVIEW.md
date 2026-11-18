# INTERVIEW — P28 CompanyWatch

**Proiect:** P28 — Pipeline de date: ETL + API + Dashboard  
**Scop:** identificarea unei probleme reale a unui utilizator și transformarea răspunsurilor sale în cerințe verificabile pentru CompanyWatch.

## 1. Datele interviului

| Câmp | Informație |
|---|---|
| Persoană intervievată | **Fleșeriu Cosmin** |
| Rol profesional | Contabil; utilizator potențial al CompanyWatch |
| Persoană care a realizat interviul | **Fleșeriu Claudiu-Stefan** |
| Data interviului | **13.11.2026** |
| Modalitatea interviului | **Față în față** |
| Materialul-sursă | Documentul `interview proiect.docx`, cu opt întrebări și răspunsurile oferite de respondent |
| Data redactării acestui rezumat | 18.11.2026 |

## 2. Context și obiectiv

CompanyWatch urmărește să reunească informații publice despre societăți comerciale, să permită consultarea lor printr-un API și să le prezinte într-un dashboard. Interviul a fost realizat cu un profesionist din contabilitate pentru a identifica informațiile utilizate în practică, dificultățile verificării manuale și o întrebare concretă la care aplicația ar trebui să răspundă.

Interviul documentează **nevoile respondentului**, nu dovedește că toate funcționalitățile sunt deja implementate ori că toate datele sunt disponibile în sursa ONRC folosită de proiect.

## 3. Întrebări și răspunsuri

### Q1. Ce informații despre o firmă cauți cel mai des în activitatea de contabilitate?

**Răspuns (redactat pe baza notițelor):** Cele mai frecvente verificări privesc:

- identificarea firmei: denumire, CUI și număr de înregistrare la Registrul Comerțului;
- starea juridică: activă, suspendată, radiată sau în insolvență;
- codurile CAEN și domeniul de activitate;
- sediul social și punctele de lucru;
- situațiile financiare anuale: cifra de afaceri, profitul sau pierderea, datoriile și numărul de salariați;
- informațiile despre TVA și statutul fiscal.

### Q2. Ce dificultăți întâmpini când verifici informațiile publice despre firme?

**Răspuns:** Informațiile sunt distribuite pe mai multe site-uri și nu sunt întotdeauna actualizate. Verificarea și corelarea lor consumă timp, în special când trebuie stabilită situația fiscală a unei societăți sau comparate mai multe firme.

### Q3. Ce informații despre mai multe firme ai vrea să poți compara rapid?

**Răspuns:** Aș dori să compar cifra de afaceri, profitul net sau pierderea, datoriile totale, capitalurile proprii și numărul de angajați. Ar fi utilă și urmărirea evoluției acestor indicatori pe ultimii **3–5 ani**, alături de domeniul de activitate și statutul juridic al fiecărei societăți.

### Q4. Te-ar ajuta să vezi când o firmă își schimbă denumirea, sediul, starea sau domeniul de activitate?

**Răspuns:** Da. Este important să cunosc modificările intervenite la firmele cu care colaborez. Mi-ar fi utile notificări privind schimbarea denumirii, sediului social, administratorului, domeniului de activitate sau statutului juridic. Astfel, aș putea actualiza corect evidențele contabile și reduce riscul unor erori în documentele întocmite.

### Q5. Ce filtre ai folosi pentru a căuta firme?

**Răspuns:** Aș folosi filtre după județ și localitate, domeniu de activitate și cod CAEN, stare juridică, interval al cifrei de afaceri, profit sau pierdere, număr de angajați și anul înființării.

### Q6. Ce întrebare concretă ai vrea să poți rezolva imediat folosind CompanyWatch?

**Răspuns:** Aș vrea să verific rapid, înaintea unei colaborări comerciale, dacă firma este activă, care este situația ei financiară, ce datorii are și dacă există aspecte care ar putea indica riscuri pentru colaborare.

### Q7. Ai avea nevoie să exporți rezultatele în Excel sau CSV? În ce scop?

**Răspuns:** Da. Exportul în Excel sau CSV ar fi util pentru analize comparative între firme, urmărirea evoluției indicatorilor financiari, întocmirea rapoartelor pentru administratorii societăților, verificarea partenerilor comerciali și centralizarea datelor pentru analize contabile și financiare.

### Q8. Ai utiliza doar un dashboard sau și un API pentru a prelua automat informații într-un alt program?

**Răspuns:** Aș utiliza ambele variante. Dashboard-ul ar facilita verificarea rapidă a firmelor, compararea datelor și urmărirea modificărilor. Un API ar fi util pentru preluarea automată a informațiilor într-un program de contabilitate, reducând munca manuală și riscul erorilor de introducere a datelor.

## 4. Problema principală identificată

**Situația actuală:** contabilul consultă mai multe surse publice pentru a verifica situația unei firme, a compara societăți și a detecta schimbări relevante. Informațiile dispersate, diferențele de actualizare și verificările manuale îngreunează procesul.

**Întrebarea centrală pentru CompanyWatch:**

> **„Înainte de a începe o colaborare comercială, cum pot verifica rapid dacă o firmă este activă, ce modificări relevante a înregistrat și ce informații publice există despre situația sa financiară?”**

Aceasta este o **sinteză formulată pentru proiect** din răspunsul la Q6, nu o transcriere literală. Evaluarea riscului comercial rămâne o decizie a utilizatorului; aplicația nu trebuie să pretindă că stabilește singură solvabilitatea sau siguranța unei colaborări.

## 5. Cerințe rezultate din interviu

Tabelul de mai jos exprimă **nevoi ale utilizatorului**. Prioritizarea și implementarea sunt decizii ulterioare de proiectare, nu funcționalități deja demonstrate.

| ID | Nevoie exprimată / direcție de implementare | Bază în interviu | Observație de fezabilitate |
|---|---|---|---|
| R-01 | Căutarea și identificarea unei firme după denumire sau CUI | Q1, Q6 | De corelat cu câmpurile disponibile în setul de date |
| R-02 | Afișarea profilului public: înregistrare, stare, CAEN și sediu | Q1 | Unele câmpuri pot lipsi din anumite ediții ori surse |
| R-03 | Compararea versiunilor succesive și evidențierea modificărilor relevante | Q4 | Se pot detecta doar schimbările din câmpurile publicate și din edițiile comparate |
| R-04 | Filtrarea firmelor după localizare, CAEN și stare | Q5 | Filtrele financiare depind de date suplimentare |
| R-05 | Compararea indicatorilor financiari și a evoluției pe 3–5 ani | Q3, Q6 | Necesită identificarea și integrarea unei surse publice de date financiare |
| R-06 | Exportul rezultatelor în CSV/Excel | Q7 | Cerință de utilizare pentru analize și rapoarte |
| R-07 | Acces programatic printr-un API documentat | Q8 | Integrarea efectivă cu un program contabil depinde de compatibilitatea acelui program |
| R-08 | Notificări la schimbarea datelor importante | Q4 | Funcționalitate dorită; nu este confirmată ca implementată |
| R-09 | Acces la statutul TVA și alte date fiscale | Q1, Q2 | Necesită verificarea unei surse fiscale distincte |
| R-10 | Urmărirea schimbării administratorului | Q4 | Disponibilitatea și condițiile de reutilizare trebuie verificate separat |

## 6. Implicații pentru implementarea proiectului

Interviul oferă punctul de plecare pentru planificarea aplicației CompanyWatch. Cerințele vor fi abordate etapizat, în funcție de datele publice disponibile și de complexitatea tehnică.

- **M1 — Fundamentul aplicației:** definirea structurii proiectului, a bazei de date și a componentelor necesare pentru stocarea și consultarea informațiilor despre firme. Modelul de date va urmări, pe cât posibil, câmpurile relevante din Q1 și Q6.
- **M2 — Pipeline ETL și istoricul datelor:** identificarea surselor publice, importul, curățarea, validarea și actualizarea datelor despre firme. Dacă sunt disponibile ediții succesive ale aceleiași surse, vor fi analizate posibilitățile de detectare a modificărilor cerute la Q4.
- **API:** proiectarea unor endpoint-uri pentru căutarea firmelor, consultarea profilului public și accesarea informațiilor disponibile. Posibilitatea integrării cu un program de contabilitate va fi evaluată separat, deoarece răspunsul la Q8 nu confirmă compatibilitatea tehnică a unui anumit program.
- **Dashboard:** proiectarea unei interfețe care să răspundă scenariului din Q6: căutarea unei firme, verificarea stării cunoscute, afișarea datei sursei și, acolo unde datele permit, prezentarea schimbărilor și a comparațiilor. Filtrele și exportul vor fi prioritizate în funcție de utilitatea lor și de disponibilitatea datelor.
- **Extinderi posibile:** notificările automate, comparațiile financiare pe 3–5 ani și verificarea statutului fiscal/TVA sunt cerințe identificate în interviu, dar pot necesita surse suplimentare și dezvoltare ulterioară. Nu se presupune că un set de date ONRC acoperă aceste informații sau că oferă actualizări în timp real.
- **Validare cu utilizatorul:** după realizarea unei versiuni demonstrabile, respondentul va putea testa scenariul din Q6. Feedback-ul efectiv va fi consemnat la punctul 8.

## 7. Aspecte de clarificat cu respondentul

- **Frecvența verificărilor:** cât de des caută informații despre firme și ce verificare consumă cel mai mult timp.
- **Prioritatea reală:** dintre stare/istoric, comparații financiare, export, notificări și API, ce ar vrea să funcționeze mai întâi.
- **Datele de validare:** un exemplu de societate pentru demonstrație, ales doar din date publice și fără documente confidențiale ale clienților.
- **Integrarea tehnică:** dacă programul de contabilitate folosit permite import prin API sau doar prin fișiere; răspunsul la Q8 exprimă o preferință, nu confirmă existența integrării.

## 8. Feedback după demonstrația aplicației

**Stadiu: nu a fost colectat încă feedback pe o versiune demonstrată.**

## 9. Concluzie

Interviul arată interes pentru o aplicație care **centralizează verificarea firmelor, permite compararea datelor publice și evidențiază modificările relevante**. Pentru respondent, valoarea practică principală este reducerea timpului necesar verificării unui posibil partener comercial. O implementare corectă trebuie să distingă între informațiile disponibile în sursele ONRC ale proiectului și datele financiare sau fiscale care ar necesita integrarea unor surse suplimentare.
