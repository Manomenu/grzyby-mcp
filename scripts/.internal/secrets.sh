#!/usr/bin/env bash
# A copy of this repo's local .env files in Bitwarden, and back — the development values
# (a test API key, a local password) that a lost laptop would otherwise take with it.
# Cluster secrets are not here: the platform repo owns them and backs them up the same way
# (its `just secrets`). AGENTS.md, "Secrets".
#
#   secrets.sh backup              .env and <project>/.env → Secure Notes in folder "Homelab"
#   secrets.sh restore [--force]   those notes → the files (a differing file is kept unless --force)
#
# One note per file, named "grzyby/<path>". Values travel through pipes and files only —
# never as arguments, never on screen.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
FOLDER_NAME="Homelab"
PREFIX="grzyby/"
SERVER="https://vault.bitwarden.eu"

for tool in bw jq; do
    command -v "$tool" >/dev/null || {
        echo "$tool not found — install the Bitwarden CLI (bw) and jq" >&2
        exit 1
    }
done

# The files this covers: .env at the root and in each project directory. Nothing else.
env_files() {
    (cd "$ROOT" && for f in .env */.env; do [ -f "$f" ] && printf '%s\n' "$f"; done) || true
}

# ── session ───────────────────────────────────────────────────────────────────
# Logging in is the owner's (master password, 2FA); unlocking asks for the master password
# here, and the session lives only in this process.
case "$(bw status | jq -r .status)" in
    unauthenticated)
        echo "not logged in to Bitwarden — once, in a terminal:" >&2
        echo "  bw config server $SERVER && bw login" >&2
        exit 1
        ;;
    locked)
        echo "unlocking the vault (master password):"
        BW_SESSION="$(bw unlock --raw </dev/tty)"
        export BW_SESSION
        ;;
esac
bw sync >/dev/null

folder_id() {
    local id
    id="$(bw list folders --search "$FOLDER_NAME" | jq -r --arg n "$FOLDER_NAME" '[.[] | select(.name == $n)][0].id // empty')"
    if [ -z "$id" ] && [ "${1:-}" = create ]; then
        id="$(bw get template folder | jq --arg n "$FOLDER_NAME" '.name = $n' | bw encode | bw create folder | jq -r .id)"
        echo "  folder $FOLDER_NAME: created" >&2
    fi
    printf '%s' "$id"
}

backup() {
    local folder path name id
    folder="$(folder_id create)"
    while read -r path; do
        name="$PREFIX$path"
        id="$(bw list items --folderid "$folder" --search "$name" | jq -r --arg n "$name" '[.[] | select(.name == $n)][0].id // empty')"
        if [ -z "$id" ]; then
            bw get template item |
                jq --rawfile notes "$ROOT/$path" --arg n "$name" --arg f "$folder" \
                    '.type = 2 | .secureNote = {type: 0} | .login = null | .name = $n | .notes = $notes | .folderId = $f' |
                bw encode | bw create item >/dev/null
            echo "  $name: created"
        elif diff -q <(bw get item "$id" | jq -j .notes) "$ROOT/$path" >/dev/null; then
            echo "  $name: unchanged"
        else
            bw get item "$id" | jq --rawfile notes "$ROOT/$path" '.notes = $notes' | bw encode | bw edit item "$id" >/dev/null
            echo "  $name: updated"
        fi
    done < <(env_files)
}

restore() {
    local force="${1:-}" folder id name path target kept=0
    folder="$(folder_id)"
    [ -n "$folder" ] || {
        echo "no folder $FOLDER_NAME in the vault — nothing was backed up yet (just secrets backup)" >&2
        exit 1
    }
    while IFS=$'\t' read -r id name; do
        path="${name#"$PREFIX"}"
        # Only .env or <existing directory>/.env: a note name must not steer a write elsewhere.
        if ! [[ "$path" == .env || ("$path" =~ ^[A-Za-z0-9_-]+/\.env$ && -d "$ROOT/${path%/.env}") ]]; then
            echo "  $name: skipped (not a .env of this repo)" >&2
            continue
        fi
        target="$ROOT/$path"
        if [ -f "$target" ] && diff -q <(bw get item "$id" | jq -j .notes) "$target" >/dev/null; then
            echo "  $path: unchanged"
        elif [ -f "$target" ] && [ "$force" != --force ]; then
            echo "  $path: differs from the vault — kept (restore --force to overwrite)"
            kept=1
        else
            (
                umask 077
                bw get item "$id" | jq -j .notes >"$target"
            )
            echo "  $path: restored"
        fi
    done < <(bw list items --folderid "$folder" | jq -r --arg p "$PREFIX" '.[] | select(.name | startswith($p)) | [.id, .name] | @tsv')
    return "$kept"
}

case "${1:-}" in
    backup) backup ;;
    restore) restore "${2:-}" ;;
    *)
        echo "usage: secrets.sh backup | restore [--force]" >&2
        exit 2
        ;;
esac
