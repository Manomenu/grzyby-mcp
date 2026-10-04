# grzyby


## Requirements

`uv`, `pnpm` (via corepack), `just`, `podman` with `podman compose`; for the full gate also
`helm`, `shellcheck` and `gitleaks`. After cloning: `just sync` (dependencies and the git hooks).

## Everyday commands

```sh
just                 # every recipe, grouped
just db up           # local PostgreSQL on :5443
just server          # API on :6210 (Swagger at /docs)
just web             # web app on :3210, proxies /api to the server
just up              # the whole stack in containers on :8091 — no cluster needed
just check           # the quality gate, exactly what CI runs
just e2e             # browser tests against a real server and database
just secrets backup  # copy the local .env files into Bitwarden (restore on a new machine)
```

How the repo is organised and what every change must bring along: [AGENTS.md](AGENTS.md).
