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

## 1. MVP — jedno narzędzie, cała Polska (Suwałki to punkt odniesienia)

- [x] PostGIS lokalnie, w CI i w `just up` (obraz `postgis/postgis`, migracja `001_postgis.sql`).
- [x] PostGIS na klastrze (obraz `shared` → `ghcr.io/cloudnative-pg/postgis`, rozszerzenie
      w zasobie `Database` bazy `grzyby`; 4.10.2026).
- [x] **Dane o lasach na żądanie, cała Polska** (4.10.2026): siatka kwadratów ok. 11 × 10 km
      (`lasy/tiles.py`) — kwadrat przychodzi z BDL (kolekcja jego RDLP) i GDOŚ przy pierwszym
      pytaniu o okolicę, równolegle (kilka sekund), potem z bazy. CronJob raz w miesiącu
      odświeża tylko kwadraty, o które pytano. Lokalnie `just import`: okolice Suwałk, Chełma,
      Gdańska i Ponikwi Wielkiej (styk trzech RDLP) — punkty odniesienia.
- [x] Zakazy wstępu (BDL) na żywo: cały kraj, pobierane przy zapytaniu, ważne 4 godziny
      (`lasy/zakazy.py`); gdy BDL nie odpowiada — stare zakazy i ostrzeżenie w odpowiedzi.
- [x] **Pogoda z Open-Meteo** (4.10.2026, `pogoda/`): dla każdego kwadratu siatki opady, temperatura
      i wilgotność gleby, 21 dni wstecz i 6 naprzód, odświeżane co 3 godziny, wszystkie kwadraty
      pytania jednym zapytaniem. Czynnik pogody dla grzyba (`scoring.weather_factor`): temperatura
      z 5 dni wokół optimum grzyba × wilgoć (deszcz sprzed 3–14 dni i gleba, z podłogą) × „gorąco
      i sucho” (powyżej 17,5 °C i poniżej 1 mm dziennie → zero) × przymrozek. Podstawa: dekada
      monitoringu borowika pod Bielefeld (Brejon Lamartinière & Hoffman 2025) — okno 5 dni,
      optimum 13,2 °C, reguła gorąco i sucho; reszta liczb szacunkowa, do korekty w etapie 2.
      Tryb mapy „Pogoda”: kwadraty w kolorach wilgoci.
- [x] **Data w `gdzie_na_grzyby`** (4.10.2026) — parametr `za_ile_dni`: od 3 dni wstecz do 5
      naprzód, domyślnie dziś; pogoda i sezon tego dnia, od 3. dnia uwaga, że to prognoza.
- [x] **Narzędzie `kiedy_na_grzyby`** (4.10.2026) — dziś i 5 dni naprzód: ocena okolicy na dzień
      (średnia z 10 najlepszych drzewostanów, na wszystkie grzyby i na każdy), pogoda w skrócie,
      najlepszy dzień (od 40/100). Bez mapy; okolica liczona raz, zmienia się tylko pogoda
      (`miejsca/best_day.py`). Chatbot potem woła `gdzie_na_grzyby` z `za_ile_dni`.
- [~] **Wynik punktowy** dla wydzielenia (`miejsca/scoring.py`): jest część stała — gatunek ×
      siedlisko × wiek × wielkość × odległość, każdy składnik z „dlaczego”. **Zostaje:** opady
      z ostatnich 2–3 tygodni, temperatura, wilgotność gleby, pora roku.
- [x] **Rodzaj grzyba** (4.10.2026) — wymagany parametr `grzyby` (borowik, podgrzybek, kurka,
      koźlarz, maślak, rydz; chatbot dopytuje albo proponuje, gdy użytkownik nie powiedział).
      Profile w `miejsca/grzyby.py`: drzewa, grupy siedlisk, klasy wieku, sezon po miesiącach;
      ocena dla każdego grzyba i średnia z listy. Widoki „wszystkie” (średnia) i każdy grzyb
      osobno — każdy z własnymi miejscami; okienko lasu z oceną każdego grzyba. Liczby w profilach to wiedza
      grzybiarza, nie pomiar — do korekty po wyjściach w teren (etap 2).
- [ ] **Zdjęcia widżetu** — gdy będą pogoda i rodzaj grzyba (do README i na stronę), na dwóch
      przykładach:
      1. Suwałki, 15 km, 10 miejsc, kurki;
      2. Płociczno-Osiedle, 2 km, 4 miejsca, wszystkie grzyby.
      Laptop: oba przykłady jeden pod drugim — jeden na pełnym ekranie, drugi w czacie.
      Telefon: dwa ładne przykłady obok siebie. Narzędzie już jest: udawany host z
      `grzyby_web/src/miejsca/mapa.e2e.ts` i projekty `laptop` / `phone` w Playwright.
      Przy okazji **README dla użytkownika, nie dla programisty**: czym to jest, zdjęcia, jak
      podłączyć w Claude, skąd dane. Wszystko techniczne, co dziś jest tylko w README (stack,
      komendy `just`, klucz i jego zmiana, Claude Code, praca lokalna), przenieść do `docs/`
      (np. `docs/dev/README.md`), a z README zostawić jeden link „dla programistów”.
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
- [ ] Domena `gdzie-na-grzyby.pl` (sprawdzić cenę **odnowienia**, nie tylko pierwszego roku).
- [ ] Strona: czym to jest, przypisanie źródeł danych (BDL, Open-Meteo, GDOŚ, mapa) i
      **instrukcja instalacji konektora** — najpierw Claude (claude.ai i Claude Code), potem przełącznik
      instrukcji Claude / ChatGPT. Treść zależy od sposobu dostępu (niżej): dziś to wspólny klucz
      w nagłówku (`just claude-connector`), dla innych ludzi będzie inaczej.
- [ ] **Konta / klucze na osobę — na później.** Na start publicznie bez kont („Przed publicznym
      startem”); wrócić, gdy będą potrzebne (zgłoszenia, płatny dostęp, nadużycia). Warianty,
      od najmniejszego tarcia dla użytkownika:
      1. **OAuth z MCP** — Claude i ChatGPT przy dodawaniu konektora same otwierają okno
         logowania serwera (specyfikacja MCP, autoryzacja OAuth 2.1): użytkownik klika
         „Połącz”, loguje się raz, niczego nie kopiuje. Logowanie jest **nasze** (Claude/OpenAI
         nie udostępniają swoich kont cudzym serwerom), ale może przekazać dalej: Google,
         GitHub, kod na maila. Kto to obsłuży — sprawdzić Cloudflare Access (ochrona MCP przez
         OAuth, pasuje do AGENTS.md §8) albo gotowego dostawcę; własny serwer autoryzacji
         to sporo kodu.
      2. **Rejestracja mailem i osobisty klucz** — formularz na stronie, klucz przychodzi
         mailem, użytkownik wkleja go w nagłówek konektora jak dziś. Prostsze do zbudowania,
         ale więcej kroków i klucz do pilnowania; wymaga wysyłki maili i tabeli kluczy.
      Przy obu: limit zapytań na osobę, możliwość odcięcia jednej osoby, RODO (mail to dana
      osobowa — polityka prywatności).

## Przed publicznym startem

Dopóki adresu używa tylko właściciel — nie blokuje. Zanim adres trafi do innych ludzi.
Na start **publicznie, bez kont i bez klucza** (ustalone 4.10.2026).

**Ważne dla limitów:** zapytania wszystkich użytkowników Claude przychodzą z serwerów Anthropic
(ChatGPT — z serwerów OpenAI), nie z ich komputerów. Limit na IP w Cloudflare nie odróżni więc
użytkowników — to tylko hojny bezpiecznik przed kimś, kto wali w `/mcp` wprost. Prawdziwa
ochrona jest w aplikacji, przy tym, co kosztuje.

Zabezpieczenia w aplikacji (to repo):

- [x] **Dzienny limit nowych kwadratów** dla całego serwisu: 300 na dzień kalendarzowy w czasie
      polskim, od północy — więc „spróbuj jutro” jest prawdą (`lasy/tiles.py`, 4–5.10.2026). Dla skali: cztery okolice wzorcowe to 53 kwadraty przy 15 km
      i 176 przy największym promieniu (30 km). Okolica wchodzi cała albo wcale; po przekroczeniu
      nowa okolica dostaje uwagę „spróbuj jutro”, znane działają dalej; miesięczne odświeżanie
      się nie liczy. Limit miękki — pytania o nowe okolice w tej samej chwili nie widzą się nawzajem.
- [x] **Kolejka do Nominatim: 1 zapytanie na sekundę** dla całego serwera (`miejsca/geocoding.py`,
      w procesie — wystarcza przy jednej replice). Wątek rezerwuje termin pod blokadą i czeka poza
      nią; gdy kolejka jest dłuższa niż 10 s, odpada od razu („spróbuj za chwilę”) — czeka, trzymając
      połączenie z bazą, a pula ma 5. Po odczekaniu ponownie sprawdza cache. Przy większym ruchu —
      własna instancja albo inne geokodowanie.
- [x] **Cache gotowych odpowiedzi** na godzinę (`miejsca/cache.py`, w bazie, nie w pamięci): ta sama
      miejscowość, lista grzybów, promień, liczba miejsc i dzień. Tylko pełne odpowiedzi — z uwagą
      o niedziałającej usłudze nie są zapamiętywane.
- [x] **Najwyżej 3 nowe okolice pobierane naraz** (`tiles.AREAS_AT_ONCE`); czwarta dostaje uwagę
      „spróbuj za minutę”, znane okolice działają dalej. 3, nie 5: każde pobranie trzyma jedno
      z pięciu połączeń puli (`db.py`), a reszta pytań też ich potrzebuje.
- [ ] **Zmierzyć pamięć przy 3 pobraniach naraz** — skok zużycia RAM serwera nie powinien
      przekroczyć ~200 MB (limit poda 384 Mi); jedno pobranie to szczyt ~100 MB (okno 8 kwadratów).
- [ ] **Cache dla `kiedy_na_grzyby`** — dziś liczy okolicę za każdym razem (1–3 s); gdy ruch urośnie,
      ten sam mechanizm co dla `gdzie_na_grzyby`.
- [ ] **Open-Meteo** — dziś cache 3 h na kwadrat; przy umiarkowanym ruchu mieści się w darmowym
      limicie (~10 tys. zapytań dziennie), przy dużym — dłuższy cache albo płatny plan.

Platforma (suwalski-platform):

- [ ] **Reguła rate limiting w Cloudflare na `/mcp`** — hojna (propozycja: 300 zapytań na
      minutę z IP; darmowy plan ma jedną regułę), zapisana też w TODO suwalski-platform.
- [x] **Włączyć dostęp publiczny** — `server.allowPublic: true` w Application platformy (flaga
      jest w charcie od 5.10.2026). **Klucz zostaje** (`server.mcpKeySecret`, `just
      claude-connector`): wyłączenie flagi przywraca blokadę bez nowego klucza i bez zmian
      w konektorach, które go wysyłają. Potem instrukcja na stronie to sam adres konektora.
- [ ] **Bez limitów dla zapytań z kluczem** (pomysł) — kto wysyła klucz (właściciel, znajomi), nie
      podlega dziennemu limitowi nowych kwadratów ani kolejce „spróbuj za minutę”. `RequireKey`
      musiałby przekazać dalej, czy zapytanie miało klucz (np. w `scope["state"]`), a narzędzia —
      sprawdzić to przed `tiles.ensure`.

Formalności i dane:

- [ ] **Mail do BDL** (`bdl@bdl.lasy.gov.pl`) — informacja o przetwarzaniu danych, wymagana
      regulaminem portalu; w przypisaniu: źródło, czas wytworzenia i pozyskania.
- [ ] **Wigierski Park Narodowy** — czy wyznacza miejsca, gdzie wolno zbierać grzyby
      (wigpn.gov.pl / telefon). Do odpowiedzi: park = nie wolno.
- [x] **Licencje wszystkich źródeł** (5.10.2026) — GDOŚ bez warunków (opis usługi: opłaty i ograniczenia
      „brak”); przypisanie uzupełnione o linki do licencji CC BY 4.0, do Open-Meteo i do
      openstreetmap.org/copyright oraz o informację o przetworzeniu. Tabela:
      `docs/dev/rozpoznanie-danych.md`, „Licencje i przypisanie”. Zostaje mail do BDL (wyżej).
- [ ] **Open-Meteo** — darmowe tylko niekomercyjnie, z przypisaniem (CC BY 4.0); sprawdzić
      aktualne warunki i limit zapytań przed większym ruchem.
- [x] **Kafelki mapy** (5.10.2026) — CARTO Voyager z naszym kluczem zamiast kafelków OSM, które
      blokowały mapę w Codexie na Windows (brak nagłówka Referer) i nie pozwalają na duży ruch.
      Darmowo do 5 mln kafli/miesiąc, przy zarabianiu 1 mln (`docs/monetyzacja.md`). Gdyby
      grzybiarzom brakowało ścieżek leśnych — styl outdoorowy (MapTiler, Thunderforest) jako przełącznik.
- [ ] **Prywatność** — nie zbieramy danych osobowych (w logach nginx adresy IP serwerów Anthropic
      i OpenAI, w bazie nazwy miejscowości); krótka notka na stronie.
- [ ] **MCP Apps w ChatGPT** — czy pokazuje mapkę (bez klucza odpada pytanie o nagłówek).
- [ ] **Kolejność** (propozycja): zabezpieczenia w aplikacji (zrobione poza pomiarem pamięci) → licencja GDOŚ i przypisanie →
      reguła Cloudflare i zdjęcie klucza → mail do BDL (właściciel) → strona z instrukcją.

## Później / może

- [ ] Zgłoszenia „byłem, były / nie było” od użytkowników — jedyna droga do sprawdzania trafności.
- [x] **Test widżetu mapy w przeglądarce** — `grzyby_web/src/miejsca/mapa.e2e.ts` (w `just e2e`
      i w CI): widżet z prawdziwego serwera przez MCP, pod CSP z jego `_meta.ui.csp`, w piaskownicy
      bez wyskakujących okien, z udawanym hostem; dane `mapa.answer.json` pilnowane modelem `Answer`.