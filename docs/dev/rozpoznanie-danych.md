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

### Open-Meteo — sprawdzone 4.10.2026, decyzja: tylko Open-Meteo

- `https://api.open-meteo.com/v1/forecast?latitude=…&longitude=…&past_days=30&daily=precipitation_sum,temperature_2m_min,temperature_2m_max&hourly=soil_moisture_0_to_1cm,soil_moisture_3_to_9cm,soil_moisture_9_to_27cm,soil_temperature_6cm&timezone=Europe/Warsaw`
  — **jedno zapytanie** (0,25 s, 35 KB, bez klucza): dzienne opady i temperatury z 30 dni
  wstecz (`past_days` do 92) plus prognoza, godzinowa wilgotność gleby [m³/m³] na trzech
  głębokościach i temperatura gleby.
- **Zgodne z IMGW:** 4.10 o 7:00 Suwałki — IMGW 12,8 °C / 91,7 % wilgotności, Open-Meteo
  12,0 °C / 95 %. Opady z 14 dni: 32 mm, z 30 dni: 66 mm.
- **Siatka co kilka km, nie jedna stacja:** trzy punkty okolicy (Suwałki, okolice Wigier,
  ~20 km na SE) różnią się o 1,5 °C i 29–32 mm opadu w 14 dni — wartość per obszar, a nie
  jedna liczba dla całego rejonu.
- Wilgotność gleby (0–1 cm: 0,10–0,24 w ciągu 30 dni) — sygnał „po deszczu / sucho” wprost,
  zamiast zgadywać z sumy opadów.
- Archiwum (`archive-api.open-meteo.com`, reanaliza) jest dzień do tyłu — gdyby kiedyś
  potrzebna była dłuższa historia.
- **Wniosek:** IMGW nic nie dodaje poza jednym prawdziwym pomiarem, a własne zbieranie nie
  jest potrzebne, skoro `past_days` daje historię. Na MVP tylko Open-Meteo; IMGW odpada.
  Warunki: darmowe niekomercyjnie, CC BY 4.0 (przypisanie „Weather data by Open-Meteo.com”) —
  sprawdzić przed publicznym startem (TODO).

## Otwarte pytania

1. Mail do BDL o przetwarzaniu danych (właściciel) — przed publicznym startem, nie przed MVP.
2. WPN: czy są miejsca, gdzie wolno zbierać grzyby — zapytać park.
3. Licencja / przypisanie danych GDOŚ.
4. ~~Open-Meteo vs zbieranie IMGW~~ — rozstrzygnięte: tylko Open-Meteo (punkt 3).

## Licencje i przypisanie — sprawdzone 5.10.2026

Co każde źródło wymaga obok swoich danych i gdzie to spełniamy (przypisanie: `search.attribution`
— w odpowiedzi obu narzędzi i pod mapą; atrybucja kafelków: w rogu mapy).

| Źródło | Licencja / warunki | Wymaga | U nas |
| --- | --- | --- | --- |
| Bank Danych o Lasach (drzewostany, zakazy wstępu) | CC BY 4.0 + regulamin portalu | źródło, czas wytworzenia i pozyskania, link do licencji, informacja o przetworzeniu; **mail do DGLP/BDL o przetwarzaniu** | wszystko w przypisaniu; mail — TODO, właściciel |
| Open-Meteo (pogoda) | CC BY 4.0, darmowe niekomercyjnie (< 10 tys. zapytań/dzień) | link do open-meteo.com przy danych, link do licencji, informacja o zmianach | w przypisaniu; płatny plan przy zarabianiu (`docs/monetyzacja.md`) |
| GDOŚ (parki, rezerwaty) | usługa WFS: opłaty „brak”, ograniczenia dostępu „brak” | nic poza dobrą praktyką podania źródła | w przypisaniu, z adresem usługi |
| Nominatim / OpenStreetMap (położenie miejscowości) | ODbL; wytyczne OSMF o geokodowaniu | „© OpenStreetMap contributors” z linkiem do openstreetmap.org/copyright; pojedyncze wyniki wolno trzymać (nieistotne wyciągi) — share-alike tylko przy zbieraniu znacznej części bazy | w przypisaniu; cache trzyma tylko pytane miejscowości |
| Kafelki CARTO (podkład mapy, dane OpenStreetMap; od 5.10.2026 zamiast kafelków OSM, które blokują Codex na Windows i duży ruch) | warunki CARTO Basemaps: własny klucz, za darmo do 5 mln kafli/miesiąc niekomercyjnie, 1 mln komercyjnie | widoczne „© OpenStreetMap” i „© CARTO” z linkami | atrybucja w rogu mapy; klucz w Application platformy (`server.cartoKey`) |
| Leaflet (BSD-2), `@modelcontextprotocol/ext-apps` (MIT) | licencje open source | zachowanie informacji o licencji | ładowane z CDN z nagłówkami licencji; Leaflet sam pokazuje się w rogu mapy |

Źródła: [warunki Open-Meteo](https://open-meteo.com/en/terms), [licencja Open-Meteo](https://open-meteo.com/en/licence),
[wytyczne OSMF o geokodowaniu](https://osmfoundation.org/wiki/Licence/Community_Guidelines/Geocoding_-_Guideline),
[FAQ licencji OSM](https://osmfoundation.org/wiki/Licence_and_Legal_FAQ), [zasady kafelków OSM](https://operations.osmfoundation.org/policies/tiles/), [warunki CARTO Basemaps](https://carto.com/legal/basemap-terms/),
opis usługi WFS GDOŚ (`sdi.gdos.gov.pl/wfs?request=GetCapabilities`: Fees, AccessConstraints).
