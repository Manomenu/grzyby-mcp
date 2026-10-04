# `just secrets <recipe>` — a copy of this repo's local .env files in Bitwarden.
# The logic is in scripts/.internal/secrets.sh. Cluster secrets live in the platform repo.

set shell := ["bash", "-euo", "pipefail", "-c"]
# Recipes run from the repo root, like the ones in the main justfile.
set working-directory := ".."
set positional-arguments

[private]
default:
    @just --list secrets --unsorted

# Copy .env and <project>/.env into Bitwarden (folder Homelab), after changing one
backup:
    @./scripts/.internal/secrets.sh backup

# New machine: Bitwarden → the .env files. --force overwrites files that differ
restore *args:
    @./scripts/.internal/secrets.sh restore "$@"
