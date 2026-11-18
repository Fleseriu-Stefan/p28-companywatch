# CompanyWatch M2 — surse ONRC și filtrarea persoanelor juridice

Data verificării: 2026-11-17. Sursele sunt aprobate de utilizator pentru dezvoltarea
M2; validarea integrală rămâne obligatorie înainte de publicare. Implementarea și
testele inițiale folosesc exclusiv fixtures sintetice și MySQL izolat.

## Cele două ediții aprobate

| Ediție | Publicarea resursei | Package ID | Resource ID OD_FIRME.CSV | Dimensiune declarată |
|---|---|---|---|---:|
| 19.10.2026 | 20.10.2026 | `1962670f-acda-41b5-b52c-c430d7a1ef5e` | `361e52e3-4590-40af-ae0f-8a15089fc927` | 695.782.068 bytes |
| 04.11.2026 | 06.11.2026 | `c2c88c9d-4824-45f1-90ec-656f1c0d8785` | `869eac01-8480-4ac6-a18d-d0f044b0db80` | 696.515.538 bytes |

- [Metadate oficiale 19.10.2026](https://data.gov.ro/api/3/action/package_show?id=firme-19-10-2026)
- [Metadate oficiale 04.11.2026](https://data.gov.ro/api/3/action/package_show?id=firme-04-11-2026)
- [CSV 19.10.2026](https://data.gov.ro/dataset/1962670f-acda-41b5-b52c-c430d7a1ef5e/resource/361e52e3-4590-40af-ae0f-8a15089fc927/download/od_firme.csv)
- [CSV 04.11.2026](https://data.gov.ro/dataset/c2c88c9d-4824-45f1-90ec-656f1c0d8785/resource/869eac01-8480-4ac6-a18d-d0f044b0db80/download/od_firme.csv)

Publicatorul declarat este Oficiul Național al Registrului Comerțului. Catalogul
declară licența [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/); manifestul
trebuie să păstreze atribuirea, URL-urile, ediția și transformările. Hash-ul oficial
al resursei este necompletat în metadatele verificate. SHA-256 calculat local
identifică fișierul primit; nu este un checksum independent publicat de ONRC.

Verificarea inițială a confirmat HTTP 200, `text/csv`, URL-uri finale pe
`data.gov.ro` și dimensiunile în `Content-Range`. `Content-Length` a lipsit.
Serverul a răspuns 200 și cu intervalul întregului fișier chiar la cereri `Range`;
reluarea prin append nu poate fi presupusă sigură. URL-urile, dimensiunile și
metadatele trebuie reverificate înaintea importului autorizat.

## Profilul observat, fără extrapolare la întregul fișier

Investigația M2 a procesat câte 100.000 de înregistrări din prefixul fiecărui
fișier, fără descărcare integrală și fără salvarea sau afișarea rândurilor.
Proba de 100.000 de rânduri a citit 16.457.728 bytes per ediție. În această
implementare, verificarea suplimentară a clasificării a citit numai 2 MiB per
ediție, exclusiv în memorie; au fost raportate doar agregate de forme juridice.

- UTF-8 cu BOM; separator `^`; CRLF în prefixele inspectate.
- Același antet de 20 de coloane și 20 de câmpuri pentru fiecare dintre cele
  100.000 de rânduri procesate cu ghilimelele păstrate literal.
- Parsarea CSV standard strictă se oprește cu `'^' expected after '"'` la linia
  fizică 9.658 în octombrie și 9.893 în noiembrie. Profilul aprobat pentru M2
  tratează ghilimelele ca valori literale (`QUOTE_NONE`), fără eliminarea lor.
- Data înmatriculării apare atât ca dată, cât și ca dată cu oră. Nu se trunchiază
  silențios ora și nu se ascund formatele neacceptate.
- În fiecare prefix de 100.000 de înregistrări: EUID și numărul de înmatriculare
  au câte o valoare lipsă și câte o apariție duplicată peste prima. CUI are 2.106
  valori `0` și 2.156 de apariții duplicate peste prima.

Aceste constatări demonstrează minimum 100.000 de înregistrări sursă parsabile,
nu 100.000 de persoane juridice valide și unice după filtrare. Nu sunt cunoscute
încă numărul total de rânduri, unicitatea globală, toate formele juridice sau toate
anomaliile. Primul import integral trebuie să producă aceste dovezi.

Antetul sursei:

```text
DENUMIRE^CUI^COD_INMATRICULARE^DATA_INMATRICULARE^EUID^FORMA_JURIDICA^ADR_TARA^ADR_JUDET^ADR_LOCALITATE^ADR_DEN_STRADA^ADR_NR_STRADA^ADR_BLOC^ADR_SCARA^ADR_ETAJ^ADR_APARTAMENT^ADR_COD_POSTAL^ADR_SECTOR^ADR_COMPLETARE^WEB^TARA_FIRMA_MAMA
```

## Identificarea persoanelor juridice

[Legea societăților, publicată de ONRC](https://www.onrc.ro/documente/legislatie/LG%2031.pdf),
art. 1–2, delimitează societățile cu personalitate juridică și formele lor. Art. 41
leagă personalitatea de înmatriculare; art. 43 distinge sucursalele, care nu au
personalitate juridică proprie. Această sursă susține categoria societăților;
nu este un nomenclator complet al codurilor din exportul CSV.

Verificarea directă a celor două prefixe oficiale de 2 MiB a găsit următoarele
combinații relevante. Sunt numărători ale unor prefixe, nu totaluri naționale:

| Prefix COD_INMATRICULARE | FORMA_JURIDICA | Rânduri octombrie | Rânduri noiembrie |
|---|---|---:|---:|
| J | SRL | 8.080 | 8.181 |
| J | SA | 99 | 97 |
| J | SNC | 67 | 67 |
| F | PFA | 2.453 | 2.402 |
| F | II | 810 | 786 |
| F | PF | 599 | 589 |
| F | AF | 398 | 390 |
| F | IF | 167 | 167 |
| C | CA | 6 | 6 |
| C | SC | 5 | 5 |

Prefixul `J` apare și cu `N/A`, `OCC`, `OCM`, `OCR`, `RA`, `OC` și `ALT`.
Prin urmare, nu tratăm automat orice prefix `J` sau `C` ca dovadă suficientă.
Nu deducem semnificația codurilor necunoscute numai din inițiale.

Pentru subsetul inițial, recomandarea conservatoare este:

1. Admitere numai pentru `FORMA_JURIDICA` exact `SRL`, `SA` sau `SNC`, împreună
   cu număr de înmatriculare din seria `J` și EUID concordant cu identificatorul
   sursă. Formele sunt documentate juridic și codurile sunt observate în CSV.
2. Excludere pentru seria `F` și formele `PFA`, `II`, `IF`, `PF`, `AF`.
3. Excludere/carantină pentru sucursale sau indicii de sucursală, inclusiv
   `TARA_FIRMA_MAMA` completată ori marcaj `SUCURSAL` în denumire. Aceste verificări
   sunt un filtru conservator, nu un mecanism complet de certificare juridică.
4. Formele absente din allowlist, prefixele necunoscute și contradicțiile sunt
   raportate și nu intră automat în stocarea persistentă a companiilor.

Această selecție este un subset intenționat al persoanelor juridice, nu o
clasificare completă a tuturor entităților ONRC. SCS/SCA și alte categorii pot fi
extinse ulterior pe bază de dovezi ale codificării din sursă și aprobare. Simpla
neapartenență la F nu este criteriu de admitere. O filială cu personalitate
juridică nu trebuie confundată automat cu o sucursală; cazurile ambigue rămân
nepublicate până la clarificare.

## Minimizarea datelor și prima încărcare reală

Utilizatorul a autorizat pentru persistență numai identificatori, denumire, formă
juridică, județ, localitate și data înmatriculării persoanelor juridice. Câmpurile
de adresă detaliată, WEB și datele altor persoane nu trebuie copiate în staging-ul
persistent al companiilor, rapoarte, loguri sau fixtures reale. Raportarea
respingerilor poate păstra ordinalul și codul problemei, nu rândul brut.

Fișierele brute pot fi folosite numai temporar, în stocare locală protejată,
exclusă din Git și din publicare. Nu sunt artefacte permanente. Transferurile
incomplete și artefactele de ingestie trebuie curățate conform ciclului pipeline-ului;
versiunile persistente conțin numai proiecția minimă autorizată.

Înainte de primul import real sunt necesare autorizarea descărcării integrale,
verificarea spațiului, reverificarea resurselor și testele complete pe MySQL izolat.
Importul trebuie să măsoare distribuția tuturor formelor juridice, motivele de
excludere, cheile lipsă/duplicate și numărul final de persoane juridice valide.
Aprobarea manuală referă exact versiunea, SHA-256 și raportul. Identificatorii
lipsă/duplicați nu se publică automat, iar un rezultat sub pragul aprobat de
100.000 de rânduri eligibile nu este prezentat ca îndeplinire a cerinței P28.
