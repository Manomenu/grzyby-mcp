#!/usr/bin/env bash
# Local PostgreSQL for development and tests: one podman container whose data lives in a
# named volume, so it survives `down` and only `reset` wipes it. Humans call this through
# `just db <command>`; check.sh calls `up` before the tests.
set -euo pipefail

NAME=grzyby-postgres
VOLUME=grzyby-postgres
# The major version the cluster runs (CloudNativePG); the minor is pinned like every image here.
IMAGE=docker.io/library/postgres:17.11
PORT=5443
USER=grzyby
DB=grzyby

wait_ready() {
    for _ in $(seq 1 30); do
        podman exec "$NAME" pg_isready -q -U "$USER" -d "$DB" && return 0
        sleep 1
    done
    echo "postgres did not become ready in 30 s — see: just db logs" >&2
    return 1
}

case "${1:-}" in
    up)
        if podman container exists "$NAME"; then
            podman start "$NAME" >/dev/null
        else
            # Published on the loopback only: the password is a development one.
            podman run -d --name "$NAME" \
                -p "127.0.0.1:$PORT:5432" \
                -v "$VOLUME:/var/lib/postgresql/data" \
                -e POSTGRES_USER="$USER" -e POSTGRES_PASSWORD="$USER" -e POSTGRES_DB="$DB" \
                "$IMAGE" >/dev/null
        fi
        wait_ready
        echo "postgresql://$USER:$USER@localhost:$PORT/$DB"
        ;;
    down)
        podman stop "$NAME" >/dev/null && echo "stopped (data kept in volume $VOLUME)"
        ;;
    reset)
        read -r -p "Delete the local database with all its data? [y/N] " answer
        [ "$answer" = "y" ] || { echo "nothing deleted"; exit 1; }
        podman rm -f "$NAME" >/dev/null 2>&1 || true
        podman volume rm "$VOLUME" >/dev/null 2>&1 || true
        echo "deleted; \`just db up\` starts an empty one"
        ;;
    psql)
        shift
        # A terminal only when there is one, so `just db psql -c …` also works from scripts.
        tty=(); [ -t 0 ] && tty=(-t)
        podman exec -i "${tty[@]}" "$NAME" psql -U "$USER" -d "$DB" "$@"
        ;;
    logs)
        podman logs -f "$NAME"
        ;;
    status)
        if podman container exists "$NAME"; then
            podman ps -a --filter "name=^$NAME\$" --format "{{.Names}}  {{.Status}}  {{.Ports}}"
        else
            echo "no local database — \`just db up\` creates it"
        fi
        ;;
    *)
        echo "usage: $0 up|down|reset|psql|logs|status" >&2
        exit 2
        ;;
esac
