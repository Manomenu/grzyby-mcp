# Rozpoznanie danych — okolica pilotażowa Suwałki / Wigry (4.10.2026)

Plik roboczy: wyniki etapu 0 z TODO. Po decyzjach wnioski idą do README / AGENTS.md / kodu
importu, a ten plik znika. Próbki danych leżą w `.artifacts/dane/` (poza gitem); obszar próbki:
bbox `22.85,53.95,23.35,54.20` (WGS84) — Suwałki, Wigry, okolice.

## Werdykt

**Dane są, są darmowe i wolno ich użyć.** Drzewostany z gatunkiem, wiekiem i typem siedliska
przychodzą jako GeoJSON z publicznego API na licencji CC BY 4.0; zakazy wstępu, parki i rezerwaty
też są dostępne jako dane wektorowe. Jedyna dziura: **sam Wigierski Park Narodowy nie ma opisu
drzewostanów w BDL** (to nie lasy Lasów Państwowych) — i tam zbieranie grzybów i tak jest
co do zasady zakazane.

## 1. Drzewostany — Bank Danych o Lasach, OGC API Features

- Adres: `https://ogcapi.bdl.lasy.gov.pl/collections/RDLP_Bialystok_wydzielenia/items?f=json&bbox=…&limit=1000&offset=…`
  (kolekcja na każdą RDLP; Suwalszczyzna to RDLP Białystok). Bez klucza, GeoJSON w WGS84,
  stronicowanie `limit`/`offset` (maks. 1000 na stronę), odpowiedź ~2,5 s.
- **Licencja: CC BY 4.0** (deklaracja usługi OGC API). Regulamin portalu BDL (od 1.02.2013)
  dodaje przy ponownym wykorzystaniu: podać źródło, czas wytworzenia i pozyskania informacji,
  udostępniać ją w pierwotnej formie (my pokazujemy wyliczenia na jej podstawie — opisać to
  w przypisaniu) i **poinformować DGLP i operatora BDL o przetwarzaniu**: mail na
  `bdl@bdl.lasy.gov.pl`. → zadanie dla właściciela przed publicznym startem.
- Próbka: **6624 obiekty**, z czego **5674 drzewostany** (`area_type = D-STAN`) w pięciu
  nadleśnictwach: Suwałki (2943), Głęboki Bród (2532), Szczebra (899), Pomorze (203), Płaska (47).
  Dane z 2026 r. (`a_year`). 17 MB GeoJSON na ten obszar.
- Pola, które nas interesują:

  | Pole | Znaczenie | W próbce |
  | --- | --- | --- |
  | `species_cd` | gatunek panujący | SO (sosna) 16 583 ha, ŚW (świerk) 1596, BRZ 536, OL (olsza) 525, DB (dąb) 462 |
  | `spec_age` | wiek gatunku panującego | szczyt 40–100 lat; 772 młodniki (0–19) |
  | `site_type` | typ siedliskowy lasu | BMŚW (bór mieszany świeży) 3280, LMŚW 966, LMB 344, LŚW 307, BŚW 158 |
  | `forest_fun` | funkcja | GOSP (gospodarczy), **REZ (rezerwat) — 48 wydzieleń** |
  | `prot_categ` | kategoria ochronności | OCH CENNE, OCH MIAST, OCH WOD… (nie zakazuje wstępu) |
  | `sub_area` | powierzchnia [ha] | |
  | `adr_for` | adres leśny wydzielenia | do linku / identyfikatora |

  Na pierwszy rzut oka idealne pod grzyby: przewaga sosny i świerka w wieku 40–100 lat na borach
  mieszanych świeżych (borowik, podgrzybek, kurka). Młodniki (wiek < 20) i `area_type` inne niż
  `D-STAN` (bagna, zręby, łąki…) odpadają od razu.

## 2. Gdzie nie wolno

- **Okresowe zakazy wstępu (BDL):** usługa ArcGIS REST z zapytaniami, nie tylko obrazek WMS —
  `https://mapserver.bdl.lasy.gov.pl/ArcGIS/rest/services/WMS_zakazy_wstepu_do_lasu/MapServer/0/query?…&f=geojson`.
  W całym kraju 782 obiekty; w okolicy pilotażowej dziś **0**. Pola m.in. `opis`, `data`,
  `data_koncowa`, `nazwa_nadl` — zakazy są czasowe, więc trzeba je pobierać codziennie.
- **Parki narodowe i rezerwaty (GDOŚ):** WFS `https://sdi.gdos.gov.pl/wfs`, warstwy
  `GDOS:ParkiNarodowe`, `GDOS:Rezerwaty` (GeoJSON). W okolicy: Wigierski Park Narodowy i jego
  otulina oraz rezerwaty Ostoja bobrów Marycha, Bobruczek, Cmentarzysko Jaćwingów. Otulina nie
  jest parkiem — tam zbierać wolno. Licencja GDOŚ — **do potwierdzenia** (dane publiczne, ale
  warunek przypisania sprawdzić).
- **Wigierski Park Narodowy:** w parkach narodowych zbieranie grzybów jest zakazane, chyba że
  park wyznaczy miejsca, gdzie wolno. Czy WPN takie wyznacza — **nie znalazłem w oficjalnych
  źródłach**. Do czasu potwierdzenia u parku (wigpn.gov.pl / telefon): **park = nie wolno**,
  w odpowiedzi narzędzia wprost „to park narodowy, tu nie zbieramy”.

## 3. Pogoda — IMGW

- `https://danepubliczne.imgw.pl/api/data/synop/station/suwalki` — stacja synoptyczna Suwałki
  (12195): temperatura, wilgotność, **suma opadu**, ale **tylko ostatni pomiar**. Historii
  z ostatnich tygodni API nie daje (archiwum to paczki CSV publikowane z opóźnieniem).
- Wniosek: albo **sami zbieramy** pomiar codziennie (CronJob → tabela; po 2–3 tygodniach mamy
  własną historię), albo historia z **Open-Meteo** (`past_days`, wilgotność gleby w siatce;
  darmowe niekomercyjnie). Na start: Open-Meteo dla historii + IMGW jako punkt kontrolny.
- Jedna stacja na całą okolicę — przy obszarze ~30 × 25 km to wystarczy na „rejon tak/nie”.

## Otwarte pytania

1. Mail do BDL o przetwarzaniu danych (właściciel) — przed publicznym startem, nie przed MVP.
2. WPN: czy są miejsca, gdzie wolno zbierać grzyby — zapytać park.
3. Licencja / przypisanie danych GDOŚ.
4. Open-Meteo vs zbieranie IMGW — decyzja przy pierwszej wersji wzoru punktowego.
