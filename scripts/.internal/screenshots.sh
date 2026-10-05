#!/usr/bin/env bash
# The README's pictures of the map widget (grzyby_web/src/**/*.shots.ts) into docs/img/: real
# answers of the production server, shown by a stand-in host on a laptop and a phone. Humans run
# `just screenshots`; nothing runs it on its own. Arguments go to Playwright, e.g.
#   screenshots.sh -g phone     only the phone pictures
#   SHOTS_MCP=http://localhost:6210/mcp screenshots.sh     a local server instead
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"

mkdir -p "$ROOT/docs/img"
cd "$ROOT/grzyby_web"
[ -d node_modules ] || pnpm install --frozen-lockfile --silent
exec pnpm exec playwright test -c e2e/screenshots.config.ts "$@"
