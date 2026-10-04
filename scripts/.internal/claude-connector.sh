#!/usr/bin/env bash
# What to type into Claude's "Add custom connector" for the production /mcp — name, URL and the
# Authorization header — plus the same as a Claude Code command. README.md, "Podłączenie do
# chatbota".
#
# The key comes from the platform repo, which owns it (AGENTS.md, "Secrets"): its
# .secrets/grzyby.env when that repo is checked out next to this one, otherwise its copy in
# Bitwarden (note "suwalski-platform/.secrets/grzyby.env"; asks for the master password).
#
# Prints the key on purpose — it is what you paste. Not for agents.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
NAME=grzyby
URL=https://grzyby.gugnowski.com/mcp
LOCAL_SOURCE="$ROOT/../suwalski-platform/.secrets/grzyby.env"
NOTE="suwalski-platform/.secrets/grzyby.env"

# MCP_KEY's value from a .env text on stdin, without the quotes the platform's save_source adds.
mcp_key() {
    sed -n 's/^MCP_KEY=//p' | tail -n 1 | sed "s/^[\"']//; s/[\"']\$//"
}

if [ -f "$LOCAL_SOURCE" ]; then
    key="$(mcp_key <"$LOCAL_SOURCE")"
    from="${LOCAL_SOURCE#"$ROOT/../"}"
else
    for tool in bw jq; do
        command -v "$tool" >/dev/null || {
            echo "no $LOCAL_SOURCE and no $tool to read Bitwarden" >&2
            exit 1
        }
    done
    case "$(bw status | jq -r .status)" in
        unauthenticated)
            echo "not logged in to Bitwarden — once: bw config server https://vault.bitwarden.eu && bw login" >&2
            exit 1
            ;;
        locked)
            echo "unlocking the vault (master password):" >&2
            BW_SESSION="$(bw unlock --raw </dev/tty)"
            export BW_SESSION
            ;;
    esac
    bw sync >/dev/null
    id="$(bw list items --search "$NOTE" | jq -r --arg n "$NOTE" '[.[] | select(.name == $n)][0].id // empty')"
    [ -n "$id" ] || {
        echo "no note \"$NOTE\" in Bitwarden — run \`just secrets backup\` in suwalski-platform" >&2
        exit 1
    }
    key="$(bw get item "$id" | jq -r .notes | mcp_key)"
    from="Bitwarden: $NOTE"
fi
[ -n "$key" ] || {
    echo "no MCP_KEY in $from" >&2
    exit 1
}

cat <<OUT
Claude → Settings → Connectors → Add custom connector   (key from $from)

  Name             $NAME
  URL              $URL
  Authentication   No sign-in
  Request header   Authorization
  Header value     Bearer $key

Claude Code:

  claude mcp add --transport http $NAME $URL --header "Authorization: Bearer $key"

After a change to the tool (name, description, _meta): disconnect and reconnect the connector,
or Claude keeps the old tool list (docs/mcp-apps.md, point 4).
OUT
