# grzyby-mcp

Serwer MCP dla chatbotów (Claude, ChatGPT): pytasz „gdzie w okolicy X są teraz grzyby?”, a w
odpowiedzi dostajesz **mapkę** z zaznaczonym kawałkiem lasu, krótkie uzasadnienie (drzewa,
opady, temperatura) i link do trasy w Google Maps. Dane: Bank Danych o Lasach (drzewostany,
zakazy wstępu) i pogoda z IMGW.

**Stan:** szkielet. Działa pusty serwer z bazą, aplikacja webowa i cała bramka jakości;
narzędzia MCP jeszcze nie ma. Plan i kolejne etapy: [TODO.md](TODO.md), propozycja stacka:
[docs/dev/propozycja-stacka.md](docs/dev/propozycja-stacka.md).

Projekt hobbystyczny, bez części komercyjnej.

## Stack

- **Serwer:** Python 3.14, FastAPI, PostgreSQL (psycopg, czyste SQL, migracje w
  `grzyby_server/grzyby_server/migrations/`).
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
just up              # cały stack w kontenerach na :8091 — bez klastra
just check           # bramka jakości, dokładnie to, co odpala CI
just e2e             # testy w przeglądarce na prawdziwym serwerze i bazie
just secrets backup  # kopia lokalnych plików .env w Bitwardenie (restore na nowej maszynie)
```

Jak repo jest zorganizowane i co musi przynieść każda zmiana: [AGENTS.md](AGENTS.md).
