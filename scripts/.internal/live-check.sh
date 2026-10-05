#!/usr/bin/env bash
# The tests against the real outside services (grzyby_server/tests/live): BDL, GDOŚ, Open-Meteo,
# Nominatim. Not part of the gate — they need the internet and are slow; CI runs them daily
# (.github/workflows/live.yml). Locally it starts PostgreSQL (just db); CI provides it.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"

if [ -z "${CI:-}" ]; then
    "$ROOT/scripts/.internal/db.sh" up >/dev/null
fi
cd "$ROOT"
exec uv run pytest grzyby_server/tests/live -m live -q "$@"
