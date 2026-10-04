# Propozycja stacka (plik roboczy)

Tymczasowy — do rozmowy i decyzji. Po ustaleniu wnioski idą do README / AGENTS.md, a ten
plik znika. Punkt wyjścia: **to samo, co już znamy z automat-operat i suwalski-platform**,
plus tylko to, czego wymaga mapa. Każdy nowy element ma powód obok.

## W skrócie

| Warstwa | Wybór | Dlaczego |
| --- | --- | --- |
| Serwer MCP | **Python + oficjalne SDK `mcp`** (FastMCP), transport *streamable HTTP* pod `/mcp` | Python już znamy (automat-operat), SDK jest referencyjne, jeden proces obsłuży i MCP, i stronę. |
| Aplikacja HTTP | **FastAPI** (MCP zamontowany jako pod-aplikacja) + strona statyczna | Jak w automat-operat: `/healthz`, smoke test, ten sam szablon chartu. |
| Baza | **PostgreSQL + PostGIS** w CloudNativePG (`shared`) | Pytania „lasy w promieniu X km”, przecięcia z zakazami — to robota dla PostGIS, nie dla Pythona. CNPG ma obrazy z PostGIS. |
| Dostęp do bazy | **psycopg 3**, czyste SQL | Jak w automat-operat; zapytania przestrzenne i tak pisze się w SQL. |
| Import BDL | **GDAL `ogr2ogr`** z WFS do PostGIS, uruchamiany skryptem / Jobem | Standardowe narzędzie do WFS → PostGIS, zero własnego parsowania GML. |
| Pogoda | **httpx** → IMGW (dane publiczne), opcjonalnie Open-Meteo; **CronJob** raz dziennie | Bez kluczy i opłat przy użyciu niekomercyjnym. |
| Geokodowanie | **Nominatim** (OSM), z cache w bazie | Darmowe; polityka użycia wymaga niskiego ruchu i własnego User-Agenta — cache to załatwia. |
| Mapka w odpowiedzi | **MCP Apps**: zasób UI = jeden plik HTML z **MapLibre GL JS** | Interaktywny widżet w czacie. Bez Reacta — jedna mapa z kilkoma wielokątami nie potrzebuje frameworka. |
| Podkład mapy | **OpenFreeMap** (kafelki wektorowe), ew. ortofoto z Geoportalu (WMS) | Darmowe, bez klucza; kafelek OSM wprost łamie ich zasady przy realnym ruchu. |
| Zapasowa odpowiedź | Statyczny obrazek mapy (PNG) + link do trasy | Dla klientów bez MCP Apps — odpowiedź musi mieć sens i bez widżetu. |
| Narzędzia | `uv`, `ruff`, `mypy` strict, `pytest`, `just`, Docker | Jak w automat-operat — ta sama bramka jakości. |
| Wdrożenie | Projekt w `suwalski-platform`: Argo CD, chart Helm, tunel Cloudflare | Wszystko już stoi; nowy projekt = kopia wzorca automat-operat. |

## Otwarte pytania

1. **Licencja BDL** — blokuje wszystko, patrz TODO punkt 0.
2. **MCP Apps** — rozszerzenie jest młode; zanim zbudujemy na nim mapę, zrobić „hello world”
   w Claude i ChatGPT. Jeśli któryś klient go nie pokazuje — zapasowy PNG wystarcza na MVP.
3. **Publiczne `/mcp` bez logowania** — na MVP tak (dane tylko do odczytu, nic osobistego),
   z limitem zapytań w Cloudflare. OAuth dopiero, gdyby pojawiły się konta / zgłoszenia.
4. **Jedna baza `shared` czy osobny klaster CNPG** — PostGIS to rozszerzenie; jeśli obraz
   `shared` go nie ma, trzeba zmienić obraz (dotyka automat-operat) albo postawić osobny
   klaster. Do sprawdzenia przy wdrożeniu.
5. **Gdzie liczyć wynik** — SQL (widok / funkcja w PostGIS) czy Python. Skłaniam się do
   Pythona: wzór będzie zmieniany po wyjściach w teren, a testy w Pythonie są prostsze.

## Czego świadomie nie bierzemy (na razie)

- **Modelu językowego po stronie serwera** — myśli chatbot użytkownika; my dajemy dane i mapę.
- **Reacta / Mantine** — dopóki strona to instrukcja instalacji, a widżet to jedna mapa.
- **Kolejki, cache Redis, workerów** — jeden CronJob dziennie i tabela z wynikami wystarczą.
- **Uczenia maszynowego** — bez danych „gdzie były grzyby” nie ma na czym uczyć.
