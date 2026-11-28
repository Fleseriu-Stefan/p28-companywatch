# Datele CompanyWatch

Această fișă rezumă dovezile ONRC înregistrate la 17 noiembrie 2026. Detaliile
investigației, antetul complet și legăturile către catalog sunt în
[ONRC-SOURCE.md](docs/ONRC-SOURCE.md).

## Proveniență și atribuire

Sursa este exportul `OD_FIRME.CSV` al **Oficiului Național al Registrului Comerțului
(ONRC)**, publicat prin data.gov.ro sub licența [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/).
D-006 aprobă aceste două ediții pentru dezvoltare.

| Ediție | Publicată | Package ID | Resource ID | Dimensiune declarată |
|---|---|---|---|---:|
| [19 octombrie 2026](https://data.gov.ro/dataset/1962670f-acda-41b5-b52c-c430d7a1ef5e/resource/361e52e3-4590-40af-ae0f-8a15089fc927/download/od_firme.csv) | 20 octombrie 2026 | `1962670f-acda-41b5-b52c-c430d7a1ef5e` | `361e52e3-4590-40af-ae0f-8a15089fc927` | 695.782.068 bytes |
| [4 noiembrie 2026](https://data.gov.ro/dataset/c2c88c9d-4824-45f1-90ec-656f1c0d8785/resource/869eac01-8480-4ac6-a18d-d0f044b0db80/download/od_firme.csv) | 6 noiembrie 2026 | `c2c88c9d-4824-45f1-90ec-656f1c0d8785` | `869eac01-8480-4ac6-a18d-d0f044b0db80` | 696.515.538 bytes |

## Observații din eșantioane

- Au fost parsate primele 100.000 de rânduri din fiecare ediție, folosind
  16.457.728 bytes per fișier. Antetul și numărul de 20 de câmpuri pe rând
  au coincis în porțiunile inspectate.
- Profilul candidat folosește UTF-8 cu BOM, separatorul `^` și ghilimele
  literale. Prefixele inspectate folosesc CRLF. Data apare atât cu oră,
  cât și fără oră.
- În fiecare prefix s-au observat câte un EUID lipsă și câte o apariție
  duplicată peste prima. Separat, verificarea clasificării a folosit
  eșantioane de 2 MiB per ediție.

## Proiecția M2

Subsetul aprobat folosește seria `J` și formele `SRL`, `SA`, `SNC`, cu
verificări pentru EUID și indicii de sucursală. EUID rămâne cheia naturală
candidată. Se păstrează doar EUID, CUI, număr de înmatriculare, denumire,
formă juridică, județ, localitate și data înmatriculării. Profilul exclude
persoanele fizice și carantinează cheile lipsă sau duplicate. Strada,
celelalte detalii de adresă și câmpul WEB sunt în afara proiecției.

## Subsetul reproductibil D-018

Se calculează SHA-256 din octeții UTF-8 ai EUID-ului exact și se interpretează
rezultatul ca întreg fără semn, big-endian. Sunt selectate valorile strict sub
același prag pentru ambele ediții. Se păstrează toate aparițiile EUID-urilor
selectate la intrarea în staging pentru a detecta duplicatele între clasificări.
Rândurile valide din afara subsetului sunt numărate separat de carantină și de
excluderile de politică.

Calibrarea citește integral fiecare ediție în Python, cu hash-urile EUID în
memorie. Pragul este cu o unitate peste valoarea cea mai mare dintre hash-urile
de rang 120.000 ale EUID-urilor eligibile, valide și unice la nivelul sursei.
Pragul comun este `0ad50bf4b6dbdc006cb5c647df5bd26933e99ca6016ec57309909de4d26e07d2` (hexazecimal).
[Statisticile de calibrare](docs/evidence/onrc-calibration.json) acoperă ambele ediții.
Manifestul fiecărei versiuni conține regula, pragul hexazecimal, amprentele fișierelor integrale
și statisticile agregate pentru ambele ediții.

## Calitatea edițiilor publicate

Ambele ediții au fost citite integral și publicate local cu profilul D-018,
în ordine cronologică. Ediția curentă este 2026-11-04.

| Indicator | 2026-10-19 | 2026-11-04 |
|---|---:|---:|
| Rânduri sursă | 4.229.451 | 4.233.074 |
| Acceptate | 120.000 | 120.163 |
| Carantinate distinct | 28.996 | 29.013 |
| Excluse prin politică | 1.357.708 | 1.359.250 |
| Valide în afara subsetului | 2.722.747 | 2.724.648 |
| `branch_quarantined` | 16.894 | 16.901 |
| `classification_unknown` | 11.705 | 11.715 |
| `euid_duplicate` | 416 | 416 |
| `euid_registration_mismatch` | 1 | 1 |

Numărătorile pe motiv sunt neaditivi. `euid_duplicate` include toate aparițiile
pentru EUID-urile duplicate selectate, inclusiv rânduri deja semnalate sau
excluse prin politică. Fiecare ediție are 208 grupuri duplicate în subset;
calibrarea a detectat 4.713 grupuri (9.426 rânduri) în fiecare sursă completă.

| Ediție | Candidați persoane juridice | Județ lipsă (candidați) | Localitate lipsă (candidați) | Județ lipsă (acceptate) | Localitate lipsă (acceptate) |
|---|---:|---:|---:|---:|---:|
| 2026-10-19 | 2.843.144 | 144 | 159 | 7 | 7 |
| 2026-11-04 | 2.845.208 | 144 | 159 | 7 | 7 |

## Diff SQL real · octombrie → noiembrie

913 adăugate, 750 eliminate, 20 modificate și 119.230 neschimbate.
Modificări pe câmp: denumire 2, județ 6, localitate 18, CUI 0, număr de
înmatriculare 0, formă juridică 0, dată de înmatriculare 0.

După încălzire, timpii SQL au fost 1,624 s, 1,679 s și 1,690 s, fiecare sub
ținta de 30 s. Consumul complet în Python a durat 1,625 s, 1,681 s și 1,692 s.
[Rezultatele Q-010 și planul de execuție](docs/M2.1-BENCHMARK.md#rezultate-q-010--2026-10-19--2026-11-04).
