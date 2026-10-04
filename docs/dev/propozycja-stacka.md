# Propozycja stacka (plik roboczy)

Tymczasowy — do rozmowy i decyzji. Po ustaleniu wnioski idą do README / AGENTS.md, a ten
plik znika. Punkt wyjścia: **to samo, co już znamy z automat-operat i suwalski-platform**,
plus tylko to, czego wymaga mapa. Każdy nowy element ma powód obok.

## W skrócie

| Warstwa | Wybór | Dlaczego |
| --- | --- | --- |
| Serwer MCP | **Python + oficjalne SDK `mcp`** (`MCPServer` + rozszerzenie `Apps`), transport *streamable HTTP* pod `/mcp` | Python już znamy (automat-operat), SDK jest referencyjne, jeden proces obsłuży i MCP, i stronę. |
| Aplikacja HTTP | **FastAPI** (MCP zamontowany jako pod-aplikacja) + strona statyczna | Jak w automat-operat: `/healthz`, smoke test, ten sam szablon chartu. |
| Baza | **PostgreSQL + PostGIS** w CloudNativePG (`shared`) | Pytania „lasy w promieniu X km”, przecięcia z zakazami — to robota dla PostGIS, nie dla Pythona. CNPG ma obrazy z PostGIS. Lokalnie i w CI już jest (`postgis/postgis`, migracja `001_postgis.sql`). |
| Dostęp do bazy | **psycopg 3**, czyste SQL | Jak w automat-operat; zapytania przestrzenne i tak pisze się w SQL. |
| Import BDL | **GDAL `ogr2ogr`** z WFS do PostGIS, uruchamiany skryptem / Jobem | Standardowe narzędzie do WFS → PostGIS, zero własnego parsowania GML. |
| Pogoda | **httpx** → Open-Meteo (`past_days=30`, opady, temperatura, wilgotność gleby) | Bez kluczy i opłat przy użyciu niekomercyjnym; historia w jednym zapytaniu, więc bez własnego zbierania (`rozpoznanie-danych.md`). |
| Geokodowanie | **Nominatim** (OSM), z cache w bazie | Darmowe; polityka użycia wymaga niskiego ruchu i własnego User-Agenta — cache to załatwia. |
| Mapka w odpowiedzi | **MCP Apps**: zasób UI = jeden plik HTML z **Leaflet** | Interaktywny widżet w czacie. Bez Reacta — jedna mapa z kilkoma wielokątami nie potrzebuje frameworka. MapLibre (WebGL) odpada: piaskownica Claude blokuje jej worker `blob:` (`docs/mcp-apps.md`). |
| Podkład mapy | **Kafelki rastrowe OpenStreetMap**, ew. ortofoto z Geoportalu (WMS) | Darmowe, bez klucza; przy realnym ruchu zasady OSM wymagają własnego źródła kafelków. |
| Zapasowa odpowiedź | Statyczny obrazek mapy (PNG) + link do trasy | Dla klientów bez MCP Apps — odpowiedź musi mieć sens i bez widżetu. |
| Narzędzia | `uv`, `ruff`, `pyright` strict, `pytest`, `just`, podman | Jak w automat-operat — ta sama bramka jakości. |
| Wdrożenie | Projekt w `suwalski-platform`: Argo CD, chart Helm, tunel Cloudflare | Wszystko już stoi; nowy projekt = kopia wzorca automat-operat. |

## Otwarte pytania

1. ~~Licencja BDL~~ — rozstrzygnięte: CC BY 4.0 (`rozpoznanie-danych.md`); mail do BDL przed publicznym startem.
2. ~~MCP Apps~~ — rozstrzygnięte: działa w Claude (`docs/mcp-apps.md`); ChatGPT do sprawdzenia.
3. ~~Publiczne `/mcp`~~ — rozstrzygnięte: publiczne, bez Cloudflare Access, chronione wspólnym
   kluczem (`mcp_key.py`); limit zapytań w Cloudflare, gdy adres zacznie krążyć.
4. ~~Jedna baza `shared` czy osobny klaster CNPG~~ — rozstrzygnięte: obraz `shared` zmieniony
   na CNPG-owy z PostGIS (zero dodatkowej pamięci; automat-operat bez zmian, rozszerzenie
   tylko w bazie `grzyby`).
5. ~~Gdzie liczyć wynik~~ — rozstrzygnięte: **Python** (wzór będzie zmieniany po wyjściach
   w teren, testy prostsze).

## Czego świadomie nie bierzemy (na razie)

- **Modelu językowego po stronie serwera** — myśli chatbot użytkownika; my dajemy dane i mapę.
- **Reacta / Mantine** — dopóki strona to instrukcja instalacji, a widżet to jedna mapa.
- **Kolejki, cache Redis, workerów** — jeden CronJob dziennie i tabela z wynikami wystarczą.
- **Uczenia maszynowego** — bez danych „gdzie były grzyby” nie ma na czym uczyć.
