# Entry point for humans: `just` lists every recipe, grouped. Logic longer than a line or
# two lives in scripts/.internal/, which is also what CI and agents call directly.

set shell := ["bash", "-euo", "pipefail", "-c"]

# The local PostgreSQL — `just db` lists its recipes (.just/db.just)
mod db '.just/db.just'

# A copy of the local .env files in Bitwarden — `just secrets backup|restore` (.just/secrets.just)
mod secrets '.just/secrets.just'

[private]
default:
    @just --list --unsorted

# ---------------------------------------------------------------------------------------
# run — development servers on the host
# ---------------------------------------------------------------------------------------

# HTTP API on :6210 (Swagger UI at /docs) — needs `just db up`
[group('run')]
server *args:
    cd grzyby_server && env -u VIRTUAL_ENV uv run python -m grzyby_server {{ args }}

# Web UI on :3210 — proxies /api to the server, so run `just server` alongside
[group('run')]
web *args:
    cd grzyby_web && { [ -d node_modules ] || pnpm install; } && pnpm dev {{ args }}

# ---------------------------------------------------------------------------------------
# dev — code generation and other chores while developing
# ---------------------------------------------------------------------------------------

# Regenerate the web app's TypeScript types from the server's API (after changing a pydantic model)
[group('dev')]
api-types:
    @./scripts/.internal/api-types.sh

# Fetch forest data around the benchmark areas (Suwałki, Chełm, Gdańsk, Ponikiew Wielka) into the local database — needs `just db up`
[group('dev')]
import:
    cd grzyby_server && env -u VIRTUAL_ENV uv run python -m grzyby_server.lasy.importer --benchmark

# What to type into Claude's "Add custom connector" for the production /mcp (prints the key)
[group('dev')]
claude-connector:
    @./scripts/.internal/claude-connector.sh

# ---------------------------------------------------------------------------------------
# infra — the containerised stack: the same images the cluster runs, wired the same way
# ---------------------------------------------------------------------------------------

# Build and start the stack on http://localhost:8091
[group('infra')]
up:
    podman compose up -d --build
    @echo "web   http://localhost:8091"
    @# The database lives in a volume; forest data comes in with questions and stays there.
    @podman compose exec -T postgres psql -U grzyby -d grzyby -tAc "SELECT count(*) FROM wydzielenia" 2>/dev/null | grep -qv '^0$' \
        || echo "no forest data yet — it comes in with the first question, or now: just import-up"

# Rebuild the images without the layer cache, then start (slow, on purpose)
[group('infra')]
rebuild:
    podman compose build --no-cache
    @just up

# The same for the stack's database
[group('infra')]
import-up:
    podman compose run --rm server python -m grzyby_server.lasy.importer --benchmark

# Stop the stack (images and the database volume stay)
[group('infra')]
down:
    podman compose down --remove-orphans

# What is running, on which ports, and where to open it
[group('infra')]
status:
    @./scripts/.internal/infra-status.sh

# Follow the logs of one service, or of all of them
[group('infra')]
logs service="":
    podman compose logs -f {{ service }}

# ---------------------------------------------------------------------------------------
# maintenance — quality gate and housekeeping
# ---------------------------------------------------------------------------------------

# Browser tests of the whole app against a real server and database (also run by CI)
[group('maintenance')]
e2e *args:
    @./scripts/.internal/e2e.sh {{ args }}

# Lint, types, tests, import contracts, dead code, the chart and compose — the same gate CI runs
[group('maintenance')]
check:
    @./scripts/.internal/check.sh

# Apply autofixes and formatting: ruff for Python, eslint and prettier for the web app
[group('maintenance')]
fmt:
    uvx ruff check --fix .
    uvx ruff format .
    cd grzyby_web && pnpm exec eslint --fix . && pnpm exec prettier --write --log-level warn .

# Install/refresh Python and web dependencies from the lockfiles, and enable the git hooks
[group('maintenance')]
sync:
    git config core.hooksPath .githooks
    uv sync
    cd grzyby_web && pnpm install --frozen-lockfile
