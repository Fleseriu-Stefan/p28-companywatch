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

## De verificat înainte de publicare

- Numărul total de rânduri, calitatea întregului export și unicitatea globală
  a EUID, separat pentru fiecare ediție.
- Minimum 100.000 de persoane juridice acceptate per ediție după validare și
  carantină. Numărul de rânduri din prefix descrie doar eșantionul.
- SHA-256 pentru fiecare fișier complet și rezultatul diff-ului real.
  Catalogul consultat nu furniza hash-ul. Hash-ul calculat la transfer va
  identifica fișierul primit.

Importul integral și publicarea datelor reale rămân în așteptare sub Q-005.
