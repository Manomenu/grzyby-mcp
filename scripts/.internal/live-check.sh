#!/usr/bin/env bash
# The tests against the real outside services (grzyby_server/tests/live): BDL, GDOŚ, Open-Meteo,
# Nominatim — the same check the cluster runs daily (miejsca/live.py), against the test database.
# Not part of the gate: they need the internet and are slow. Starts PostgreSQL (just db) first.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"

if [ -z "${CI:-}" ]; then
    "$ROOT/scripts/.internal/db.sh" up >/dev/null
fi
cd "$ROOT"
exec uv run pytest grzyby_server/tests/live -m live -q "$@"
