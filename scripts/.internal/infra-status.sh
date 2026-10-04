#!/usr/bin/env bash
# What of the container stack is running, on which ports, and where to open it. Behind `just status`.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"

cd "$ROOT"

# Every other script here needs only uv or pnpm, so a missing jq is worth naming rather
# than letting the queries below fail with something unreadable.
if ! command -v jq >/dev/null; then
    echo "jq is required by this script" >&2
    exit 1
fi

# The service list has to come from the file, not from `compose ps`: ps only reports
# containers that exist, so a service that never started would silently vanish from the
# report instead of showing up as down.
SERVICES="$(podman compose config --services 2>/dev/null | sort)"
if [ -z "$SERVICES" ]; then
    echo "no services defined in compose.yaml" >&2
    exit 1
fi

# compose prints one JSON object per line; some versions print a single array instead.
# Normalise both into one array so the queries below don't have to care which it was.
RUNNING="$(podman compose ps --format json 2>/dev/null \
    | jq -s 'if length == 1 and (.[0] | type) == "array" then .[0] else . end')"

printf '%-10s %-20s %-20s %s\n' "SERVICE" "STATE" "PORTS" "OPEN"

UP=0
for service in $SERVICES; do
    entry="$(printf '%s' "$RUNNING" | jq -c --arg s "$service" 'map(select(.Service == $s)) | first // empty')"

    if [ -z "$entry" ]; then
        printf '%-10s %-20s %-20s %s\n' "$service" "down" "-" "-"
        continue
    fi

    UP=$((UP + 1))

    state="$(printf '%s' "$entry" | jq -r '.State')"
    health="$(printf '%s' "$entry" | jq -r '.Health // ""')"
    [ -n "$health" ] && state="$state ($health)"

    # A published port is reachable from the host; an unpublished one only from inside the
    # compose network, which is exactly what the cluster will do with the API too.
    ports="$(printf '%s' "$entry" | jq -r '
        (.Publishers // [])
        | map(if .PublishedPort > 0 then "\(.PublishedPort)->\(.TargetPort)" else "\(.TargetPort) internal" end)
        | join(", ")')"
    [ -z "$ports" ] && ports="-"

    url="$(printf '%s' "$entry" | jq -r '
        (.Publishers // [])
        | map(select(.PublishedPort > 0))
        | first
        | if . == null then "-" else "http://localhost:\(.PublishedPort)" end')"

    printf '%-10s %-20s %-20s %s\n' "$service" "$state" "$ports" "$url"
done

if [ "$UP" -eq 0 ]; then
    echo
    echo "nothing is up — just up"
fi
