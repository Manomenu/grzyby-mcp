# grzyby-mcp

Serwer MCP dla chatbotów (Claude, ChatGPT): pytasz „gdzie w okolicy X są teraz grzyby?”, a w
odpowiedzi dostajesz **mapkę** z zaznaczonym kawałkiem lasu, krótkie uzasadnienie (drzewa,
opady, temperatura) i link do trasy w Google Maps. Dane: Bank Danych o Lasach (drzewostany,
zakazy wstępu) i pogoda z Open-Meteo.

**Stan:** etap 1 w toku. Narzędzie `gdzie_na_grzyby` pod `/mcp` (z mapką, MCP Apps) wskazuje
trzy najbardziej obiecujące prawdziwe drzewostany wokół miejscowości — według gatunku, wieku
i siedliska, z pominięciem parków narodowych, rezerwatów i lasów z zakazem wstępu. Mapa koloruje
wszystkie drzewostany w promieniu (tryby: wynik, drzewa, wiek, siedlisko). Działa w całej Polsce
(tylko Lasy Państwowe); pogody jeszcze nie bierze pod uwagę. Plan: [TODO.md](TODO.md),
propozycja stacka: [docs/dev/propozycja-stacka.md](docs/dev/propozycja-stacka.md).

Skąd dane: drzewostany (BDL), parki i rezerwaty (GDOŚ) trafiają do PostGIS przy pierwszym pytaniu
o daną okolicę (kwadratami ok. 11 × 10 km, `grzyby_server/lasy/tiles.py`), a CronJob raz
w miesiącu odświeża te, o które już pytano; zakazy wstępu (BDL) serwer
pobiera sam przy zapytaniu i trzyma 4 godziny; nazwę miejscowości zamienia na współrzędne
Nominatim (OpenStreetMap), z zapamiętaniem w bazie.

Projekt hobbystyczny, bez części komercyjnej.

## Stack

- **Serwer:** Python 3.14, FastAPI, SDK `mcp` (MCP Apps), PostgreSQL z PostGIS (psycopg, czyste
  SQL, migracje w `grzyby_server/grzyby_server/migrations/`).
- **Web:** React, Mantine, Vite, TypeScript strict.
- **Uruchamianie:** na hoście (`just server`, `just web`), cały stack w kontenerach
  (`just up`) albo na klastrze k3s przez Argo CD (`deploy/chart/`).
- Założony z szablonu [solid-app-tpl](https://github.com/Manomenu/solid-app-tpl).

## Wymagania

`uv`, `pnpm` (przez corepack), `just`, `podman` z `podman compose`; do pełnej bramki także
`helm`, `shellcheck` i `gitleaks`. Po sklonowaniu: `just sync` (zależności i hook gitleaks).
Do testów w przeglądarce raz: `cd grzyby_web && pnpm exec playwright install chromium`.

## Na co dzień

```sh
just                 # wszystkie komendy, w grupach
just db up           # lokalny PostgreSQL na :5443
just server          # API na :6210 (Swagger pod /docs)
just web             # aplikacja na :3210, /api przekazuje do serwera
just import          # dane o lasach wokół Suwałk, Chełma i Gdańska do lokalnej bazy (reszta dociąga się przy pytaniu)
just up              # cały stack w kontenerach na :8091 — bez klastra
just import-up       # to samo dla bazy stacku w kontenerach
just check           # bramka jakości, dokładnie to, co odpala CI
just e2e             # testy w przeglądarce na prawdziwym serwerze i bazie
just secrets backup  # kopia lokalnych plików .env w Bitwardenie (restore na nowej maszynie)
```

## Podłączenie do chatbota

Serwer działa pod **`https://grzyby.gugnowski.com/mcp`** i wymaga klucza. Serwer przyjmuje go na
dwa sposoby: nagłówkiem `Authorization: Bearer <MCP_KEY>` (zalecane) albo `?key=<MCP_KEY>` w
adresie (tylko awaryjnie, dla klientów, które nie umieją wysłać nagłówka).

Klucz jest w Bitwardenie (notatka `suwalski-platform/.secrets/grzyby.env`, wartość `MCP_KEY`);
na laptopie właściciela także w `suwalski-platform/.secrets/grzyby.env`. Nigdy nie wklejaj go
do repo, zgłoszeń ani rozmów. **`just claude-connector`** wypisuje wszystko, co trzeba wpisać
w konektorze (nazwa, URL, nagłówek z kluczem) i gotową komendę dla Claude Code — klucz bierze
z pliku obok albo z Bitwardena.

**Claude (claude.ai, aplikacja na komputer i telefon):**

1. Ustawienia → **Konektory** (Connectors) → **„Dodaj własny konektor”** (Add custom connector).
2. Nazwa: `grzyby`, URL: `https://grzyby.gugnowski.com/mcp` — **bez** `?key=`.
3. Authentication: **„No sign-in”** (Claude wykrywa to sam).
4. Request headers: nazwa `Authorization`, wartość `Bearer <MCP_KEY>` (Claude zapisuje wartość
   nagłówka i już jej nie pokazuje).
5. Zapisz; w nowej rozmowie włącz konektor (ikona narzędzi pod polem wiadomości) i zapytaj np.
   „Gdzie teraz na grzyby koło Suwałk?” — odpowiedź przyjdzie z mapką.

Klucz w nagłówku, a nie w adresie, bo wtedy nie trafia do adresu, logów ani historii.

**Klient bez nagłówków** (np. jeśli konektor ChatGPT nie umie ich wysłać): adres
`https://grzyby.gugnowski.com/mcp?key=<MCP_KEY>`. Kto ma ten adres, ma dostęp.

**Claude Code** (klucz w nagłówku, nie w adresie):

```sh
claude mcp add --transport http grzyby https://grzyby.gugnowski.com/mcp --header "Authorization: Bearer <MCP_KEY>"
```

**Lokalnie** (`just server`, bez klucza):

```sh
claude mcp add --transport http grzyby-local http://localhost:6210/mcp
```

**Zmiana klucza:** `scripts/projects/grzyby/setup.sh` w suwalski-platform (podaj nową wartość),
potem restart serwera (`kubectl -n grzyby rollout restart deployment/grzyby-server`) i nowy
nagłówek w każdym konektorze — stary klucz przestaje działać.

Mapa w odpowiedzi (MCP Apps): jak działa, czego wymaga Claude i co sprawdzać, gdy jej nie
widać — [docs/mcp-apps.md](docs/mcp-apps.md).

Jak repo jest zorganizowane i co musi przynieść każda zmiana: [AGENTS.md](AGENTS.md).
