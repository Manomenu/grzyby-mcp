# TODO — grzyby-mcp

Serwer MCP podpinany do chatbota (Claude, ChatGPT): pytasz „gdzie w okolicy X są teraz
grzyby?”, dostajesz **mapkę** z zaznaczonym kawałkiem lasu, krótkie „dlaczego” i link do
trasy w Google Maps. Później strona `gdzie-na-grzyby.pl` z instrukcją instalacji, MCP pod
`/mcp`.

Tło, konkurencja, koszty i ocena danych: notatka w Obsidianie „Aplikacja dla grzybiarza
(mcp)”. Proponowany stack: [`docs/dev/propozycja-stacka.md`](docs/dev/propozycja-stacka.md)
(plik roboczy — po decyzjach znika, a ustalenia trafiają do README / AGENTS.md).

Zasada przewodnia: **hobby, nie biznes** — koszt ≈ domena; nic komercyjnego, dopóki nie
sprawdzimy licencji danych.

---

## 0. Rozpoznanie, zanim powstanie kod — zrobione (4.10.2026)

- [x] **Licencja Banku Danych o Lasach** — CC BY 4.0 + obowiązki z regulaminu (`docs/dev/rozpoznanie-danych.md`); zostaje mail do BDL przed publicznym startem.
- [x] **Warstwy BDL** — OGC API Features: gatunek, wiek, siedlisko; zakazy przez ArcGIS REST; próbka w `.artifacts/dane/`.
- [x] **IMGW** — tylko bieżący pomiar (stacja Suwałki); historia z Open-Meteo albo własne zbieranie.
- [x] **Open-Meteo** — jedno zapytanie daje 30 dni opadów, temperatury i wilgotności gleby
      w siatce co kilka km, zgodne z pomiarem IMGW. **Na MVP tylko Open-Meteo**, bez IMGW
      i bez własnego zbierania (`docs/dev/rozpoznanie-danych.md`, punkt 3).
- [x] **MCP Apps** — „hello world” działa w Claude: `/mcp` (SDK `mcp` 2.3, stateless JSON) na
      `grzyby.gugnowski.com`, narzędzie `gdzie_na_grzyby` z mapką (Leaflet + kafelki OSM — WebGL
      odpada przez CSP piaskownicy). Wnioski i pułapki: [`docs/mcp-apps.md`](docs/mcp-apps.md).
- [x] **Wybór okolicy pilotażowej** — Suwałki / Wigierski Park Narodowy (park sam w sobie: zbiór zakazany, do potwierdzenia).

## 1. MVP — jedna okolica, jedno narzędzie

- [x] PostGIS lokalnie, w CI i w `just up` (obraz `postgis/postgis`, migracja `001_postgis.sql`).
- [x] PostGIS na klastrze (obraz `shared` → `ghcr.io/cloudnative-pg/postgis`, rozszerzenie
      w zasobie `Database` bazy `grzyby`; 4.10.2026).
- [x] Import drzewostanów (BDL), parków i rezerwatów (GDOŚ) do PostGIS — `lasy/importer.py`,
      CronJob raz w miesiącu, lokalnie `just import`. **Po pierwszym wdrożeniu** odpalić raz
      ręcznie: `kubectl -n grzyby create job --from=cronjob/grzyby-importer grzyby-importer-now`.
- [x] Zakazy wstępu (BDL) na żywo: cały kraj, pobierane przy zapytaniu, ważne 4 godziny
      (`lasy/zakazy.py`); gdy BDL nie odpowiada — stare zakazy i ostrzeżenie w odpowiedzi.
- [ ] Pogoda z Open-Meteo: opady, temperatura i wilgotność gleby z ostatnich ~30 dni
      (`past_days`), raz dziennie albo przy zapytaniu z cache na dzień.
- [~] **Wynik punktowy** dla wydzielenia (`miejsca/scoring.py`): jest część stała — gatunek ×
      siedlisko × wiek × wielkość × odległość, każdy składnik z „dlaczego”. **Zostaje:** opady
      z ostatnich 2–3 tygodni, temperatura, wilgotność gleby, pora roku.
- [x] Wyłączenie miejsc, gdzie nie wolno: zakazy wstępu, parki narodowe, rezerwaty (GDOŚ
      i `forest_fun = REZ` w BDL); drzewostan stykający się z takim obszarem też odpada.
- [x] Narzędzie MCP `gdzie_na_grzyby(miejscowosc, promien_km)` → 3 najlepsze miejsca, co
      najmniej 1 km od siebie: mapka, uzasadnienie, link do trasy, uwagi, źródła.
- [x] Geokodowanie nazwy miejscowości — Nominatim, odpowiedzi zapamiętane w bazie na stałe
      (`miejsca/geocoding.py`).
- [x] Testy: wzór punktowy, import, zakazy, geokodowanie i wyszukiwanie na prawdziwym
      PostgreSQL, z udawanymi odpowiedziami usług (`tests/fake_web.py`).
- [x] **Mapa z plamami i trybami**: widżet koloruje wszystkie drzewostany w promieniu według
      oceny, z przyciskami trybów (wynik / drzewa / wiek / siedlisko), szarymi obszarami, gdzie
      nie wolno, okienkiem z rozbiciem oceny i pełnym ekranem, gdy host go oferuje. Kształty
      w zwięzłym kodowaniu (polyline), budżet ~120 000 znaków (`miejsca/map_data.py`) — przy
      większym promieniu odpadają najsłabsze drzewostany. **Zostaje:** obejrzeć w Claude
      (wielkość, telefon, czy pełny ekran działa).
- [ ] **Lasy niepaństwowe** — BDL opisuje tylko Lasy Państwowe; prywatne i gminne lasy są na
      mapie puste (np. na północ od Suwałk). Sprawdzić, czy BDL ma je w innej kolekcji
      (uproszczone plany urządzenia lasu).
- [ ] **Gdy dane mapy przestaną się mieścić** (województwo, kraj) — pomysły, od najlepszego:
      1. widżet sam dociąga dane narzędziem widocznym tylko dla niego (`visibility: ["app"]`
         w specyfikacji MCP Apps) — bez chatbota i bez tokenów, w kawałkach według obszaru
         lub przybliżenia (np. kafelki wektorowe z PostGIS, `ST_AsMVT`);
      2. pierwsza odpowiedź daje ocenę ogólną i listę dostępnych widoków, a o konkretny widok
         użytkownik prosi chatbota (kolejne wywołanie narzędzia z parametrem widoku). Uwaga:
         każdy widok i tak niesie wszystkie kształty (~70 % danych), więc oszczędza mało,
         a przełączanie przez czat trwa sekundy zamiast kliknięcia. Za to dobre dla klientów
         bez widżetu (Claude Code): tekst wymienia widoki, użytkownik prosi o opis wybranego.

## 2. Sprawdzian w terenie

- [ ] Kilka wyjść do lasu według wskazań, zapis: gdzie, kiedy, co znalezione / nic.
- [ ] Porównanie z mapą, korekta wag wzoru. Dopiero gdy wskazania mają sens — dalej.

## 3. Wdrożenie i strona

- [x] Projekt w `suwalski-platform` (Argo, baza `grzyby` we wspólnym klastrze CloudNativePG,
      tunel Cloudflare — **publiczny**, bez Cloudflare Access; `/mcp` chroni wspólny klucz).
- [ ] Cache wyników na dzień (ochrona przed nadużyciem; limit zapytań — „Przed publicznym startem”).
- [ ] Domena `gdzie-na-grzyby.pl` (sprawdzić cenę **odnowienia**, nie tylko pierwszego roku).
- [ ] Strona: czym to jest, instrukcja „Ustawienia → Konektory → Dodaj własny” dla Claude
      i ChatGPT, przypisanie źródeł danych (BDL, Open-Meteo, GDOŚ, mapa).

## Przed publicznym startem

Dopóki adresu używa tylko właściciel — nie blokuje. Zanim adres trafi do innych ludzi:

- [ ] **Mail do BDL** (`bdl@bdl.lasy.gov.pl`) — informacja o przetwarzaniu danych, wymagana
      regulaminem portalu; w przypisaniu: źródło, czas wytworzenia i pozyskania.
- [ ] **Wigierski Park Narodowy** — czy wyznacza miejsca, gdzie wolno zbierać grzyby
      (wigpn.gov.pl / telefon). Do odpowiedzi: park = nie wolno.
- [ ] **Licencja danych GDOŚ** (parki, rezerwaty) — warunki przypisania.
- [ ] **Open-Meteo** — darmowe tylko niekomercyjnie, z przypisaniem (CC BY 4.0); sprawdzić
      aktualne warunki i limit zapytań przed większym ruchem.
- [ ] **Kafelki OSM** — przy realnym ruchu własne źródło kafelków (zasady OSM).
- [ ] **Limit zapytań w Cloudflare** na `/mcp` (TODO suwalski-platform).
- [ ] **MCP Apps w ChatGPT** — czy pokazuje mapkę i czy jego konektor umie wysłać nagłówek
      z kluczem (jeśli nie: `?key=`).

## Później / może

- [ ] Prognoza na kilka dni naprzód (Open-Meteo forecast).
- [ ] Gatunki grzybów: borowik / podgrzybek / kurka — każdy z własnymi drzewami i progiem.
- [ ] Zgłoszenia „byłem, były / nie było” od użytkowników — jedyna droga do sprawdzania trafności.
- [ ] Rozszerzenie z okolicy pilotażowej na województwo / kraj.
- [x] **Test widżetu mapy w przeglądarce** — `grzyby_web/src/miejsca/mapa.e2e.ts` (w `just e2e`
      i w CI): widżet z prawdziwego serwera przez MCP, pod CSP z jego `_meta.ui.csp`, w piaskownicy
      bez wyskakujących okien, z udawanym hostem; dane `mapa.answer.json` pilnowane modelem `Answer`.