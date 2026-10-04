#!/usr/bin/env bash
# End-to-end tests (grzyby_web/src/**/*.e2e.ts): a real browser against the real server and
# database. Humans run `just e2e`, CI runs this script. Arguments go to Playwright, e.g.
#   e2e.sh --headed        watch the browser
#   e2e.sh -g "health"     only the tests whose name matches
#
# Every run starts from an empty database of its own (grzyby_e2e), next to the development
# one, and its own server and web app (playwright.config.ts) — what you run by hand is not
# touched. Locally it starts PostgreSQL (just db); CI provides it as a service. A service the
# app gains later (a converter, a cache) gets started here the same way.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"

if [ -z "${CI:-}" ]; then
    "$ROOT/scripts/.internal/db.sh" up >/dev/null
fi

# A fresh database for the run: the tests may then assume nothing but what they create.
(cd "$ROOT/grzyby_server" && unset VIRTUAL_ENV && uv run python - <<'PY'
import psycopg
from psycopg import sql

with psycopg.connect("postgresql://grzyby:grzyby@localhost:5443/postgres", autocommit=True) as admin:
    admin.execute("DROP DATABASE IF EXISTS grzyby_e2e WITH (FORCE)")
    admin.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier("grzyby_e2e")))
PY
)

cd "$ROOT/grzyby_web"
[ -d node_modules ] || pnpm install --frozen-lockfile --silent
exec pnpm exec playwright test -c e2e/playwright.config.ts "$@"
