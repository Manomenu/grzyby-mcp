#!/usr/bin/env bash
# TypeScript types for the web app, generated from the server's OpenAPI schema. The pydantic
# models are the single source of truth; this file is never edited by hand.
#
#   api-types.sh           regenerate grzyby_web/src/api/openapi.d.ts
#   api-types.sh --check   fail if the committed file is out of date (the gate runs this)
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
TARGET="$ROOT/grzyby_web/src/api/openapi.d.ts"

TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

(cd "$ROOT/grzyby_server" && env -u VIRTUAL_ENV uv run --quiet python -c \
    "import json; from grzyby_server.app import app; print(json.dumps(app.openapi(), ensure_ascii=False, indent=2))") \
    > "$TMP/openapi.json"

cd "$ROOT/grzyby_web"
[ -d node_modules ] || pnpm install --frozen-lockfile --silent
pnpm exec openapi-typescript "$TMP/openapi.json" --output "$TMP/schema.d.ts" >/dev/null

if [ "${1:-}" = "--check" ]; then
    if ! diff -q "$TMP/schema.d.ts" "$TARGET" >/dev/null 2>&1; then
        echo "grzyby_web/src/api/openapi.d.ts is out of date with the server's API — run: just api-types" >&2
        exit 1
    fi
    echo "API types up to date"
else
    cp "$TMP/schema.d.ts" "$TARGET"
    echo "${TARGET#"$ROOT"/}"
fi
