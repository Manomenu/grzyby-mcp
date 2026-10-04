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
- [ ] **PostGIS na klastrze — przed najbliższym wdrożeniem grzyby.** Zmiana jest w roboczym
      drzewie suwalski-platform (obraz `shared` → `ghcr.io/cloudnative-pg/postgis`, rozszerzenie
      w zasobie `Database`); commit, push i synchronizacja Argo (`shared` restartuje się na
      chwilę), dopiero potem grzyby z `001_postgis.sql` — inaczej serwer nie wstanie.
- [ ] Import drzewostanów i zakazów z BDL do PostGIS dla okolicy pilotażowej (skrypt,
      powtarzalny, raz na jakiś czas).
- [ ] Pogoda z Open-Meteo: opady, temperatura i wilgotność gleby z ostatnich ~30 dni
      (`past_days`), raz dziennie albo przy zapytaniu z cache na dzień.
- [ ] **Wynik punktowy** dla wydzielenia: gatunek drzew × opady z ostatnich 2–3 tygodni ×
      temperatura × pora roku. Prosty, czytelny wzór — żadnego AI. Każdy składnik ma
      opis „dlaczego”, który trafia do odpowiedzi.
- [ ] Wyłączenie miejsc, gdzie nie wolno: zakazy wstępu, parki narodowe, rezerwaty.
- [ ] Narzędzie MCP `gdzie_na_grzyby(miejsce, promien_km)` → 3 najlepsze miejsca: mapka,
      uzasadnienie, link `https://www.google.com/maps/dir/?api=1&destination=<lat>,<lng>`.
- [ ] Geokodowanie „miejsca” (nazwa miejscowości → współrzędne).
- [ ] Testy: wzór punktowy na przykładowych danych; narzędzie MCP end-to-end na nagranych
      odpowiedziach BDL/IMGW.

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
- [ ] **Test widżetu mapy w przeglądarce** — gdy debugowanie widżetu zacznie zabierać czas
      (np. przy rysowaniu wielokątów drzewostanów): test Playwright, który podaje `mapa.html`
      z nagłówkiem CSP jak w piaskownicy Claude (`docs/mcp-apps.md`, punkt 2), wstrzykuje
      przykładowy wynik narzędzia jak host i sprawdza, że rysują się kształty i kafelki,
      a w konsoli nie ma naruszeń CSP. Wtedy „pusta mapa” wychodzi lokalnie, a nie dopiero
      w Claude.
