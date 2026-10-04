# `just db <recipe>` — the local PostgreSQL for development and tests.
# The logic is in scripts/.internal/db.sh, which check.sh also calls.

set shell := ["bash", "-euo", "pipefail", "-c"]
# Recipes run from the repo root, like the ones in the main justfile.
set working-directory := ".."

[private]
default:
    @just --list db --unsorted

# Start the database on localhost:5443 (created on first run; data survives `down`)
up:
    @./scripts/.internal/db.sh up

# Stop the database; the data stays
down:
    @./scripts/.internal/db.sh down

# Delete the database with all its data (asks first)
reset:
    @./scripts/.internal/db.sh reset

# Open psql in the database, e.g. `just db psql -c "select now()"`
[positional-arguments]
psql *args:
    @./scripts/.internal/db.sh psql "$@"

# Follow the database's log
logs:
    @./scripts/.internal/db.sh logs

# Is it running, and on which port
status:
    @./scripts/.internal/db.sh status
