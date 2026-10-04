#!/usr/bin/env bash
# Lint, type-check and test the whole solution and print a summary report.
# Exit code is non-zero if any step failed. CI runs exactly this script; humans run `just check`.
# What each step guards, and what a new feature adds to it: AGENTS.md, "The quality gate".
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"

PYTHON_PROJECTS=(grzyby_server)

declare -a REPORT
FAILED=0

run_step() {
    local name="$1"; shift
    echo
    echo "==> $name"
    if "$@"; then
        REPORT+=("PASS  $name")
    else
        REPORT+=("FAIL  $name")
        FAILED=1
    fi
}

lint() {
    (cd "$ROOT" && uvx ruff check .)
}

format_check() {
    # Does not rewrite anything — `just fmt` does.
    (cd "$ROOT" && uvx ruff format --check .)
}

import_contracts() {
    # [tool.importlinter] in pyproject.toml. Runs from the project, where grzyby_server imports.
    (cd "$ROOT/grzyby_server" && unset VIRTUAL_ENV && uv run lint-imports --config "$ROOT/pyproject.toml")
}

typecheck_python() {
    (cd "$ROOT" && unset VIRTUAL_ENV && uv run pyright)
}

pytest_project() {
    local project="$1"
    if [ ! -d "$ROOT/$project/tests" ]; then
        echo "(no tests)"
        return 0
    fi
    (cd "$ROOT/$project" && unset VIRTUAL_ENV && uv run pytest)
}

web() {
    # Same order of concerns as the Python side: types, lint, format, tests.
    cd "$ROOT/grzyby_web"
    [ -d node_modules ] || pnpm install --frozen-lockfile --silent
    pnpm exec "$@"
}

helm_chart() {
    # `lint` catches syntax, but passes a template that never renders; `template` actually
    # renders it. The tag is made up: this checks the shape, not whether the image exists.
    cd "$ROOT"
    helm lint deploy/chart --set image.tag=sha-lint --quiet
    helm template lint-check deploy/chart --set image.tag=sha-lint >/dev/null
}

compose_file() {
    # The local stack (compose.yaml) must at least parse and resolve; `just up` builds it.
    # podman on the laptop, docker on the CI runner — the same file either way.
    (cd "$ROOT" && "${COMPOSE[@]}" config --quiet)
}

shell_scripts() {
    # Warnings and up: the info level flags every function run_step calls by name.
    (cd "$ROOT" && { find scripts -name "*.sh"; echo .githooks/pre-commit; } | xargs shellcheck -S warning)
}

secrets_in_git() {
    # The whole history (a secret deleted in a later commit is still published), then what is
    # changed but not committed yet. The pre-commit hook (.githooks/) checks each commit too.
    (cd "$ROOT" && gitleaks git . --no-banner --redact --log-level warn &&
        gitleaks git . --pre-commit --no-banner --redact --log-level warn)
}

local_database() {
    # The tests need PostgreSQL. CI provides it as a service; here it is the container
    # `just db up` manages, started if it is not running yet.
    "$ROOT/scripts/.internal/db.sh" up >/dev/null
}

run_step "lint (ruff)" lint
run_step "format (ruff format --check)" format_check
run_step "typecheck python (pyright strict)" typecheck_python
run_step "import contracts python (import-linter)" import_contracts
if [ -z "${CI:-}" ]; then
    run_step "postgres for tests (just db up)" local_database
fi
for project in "${PYTHON_PROJECTS[@]}"; do
    # Includes tests/test_contracts.py: every server module has a layer in pyproject.toml.
    run_step "pytest $project (incl. every module in the contracts)" pytest_project "$project"
done
# Two TypeScript projects: the app (browser) and the code that runs in Node (vite config, e2e
# tests). This checks the types of both; it does not run the e2e tests (that is `just e2e`).
web_typecheck() { web tsc --noEmit -p tsconfig.app.json && web tsc --noEmit -p tsconfig.node.json; }
run_step "typecheck grzyby_web (tsc: app, e2e tests, config)" web_typecheck
run_step "lint grzyby_web (eslint strict + import contracts)" web eslint .
run_step "format grzyby_web (prettier --check)" web prettier --check .
run_step "test grzyby_web (vitest)" web vitest run
# Unused files, exports and dependencies. knip.json leaves out the generated API types and
# openapi-typescript, which only scripts/.internal/api-types.sh uses (knip reads no shell).
run_step "dead code grzyby_web (knip)" web knip
run_step "API types up to date (just api-types)" "$ROOT/scripts/.internal/api-types.sh" --check

# Tools a fresh machine may lack are skipped with a visible note instead of a PASS — a
# silently skipped step is worse than no step. CI installs helm, so there it always runs.
if command -v helm >/dev/null 2>&1; then
    run_step "helm chart (lint + template)" helm_chart
else
    REPORT+=("SKIP  helm chart — helm not installed")
fi
if command -v shellcheck >/dev/null 2>&1; then
    run_step "shell scripts (shellcheck)" shell_scripts
else
    REPORT+=("SKIP  shell scripts — shellcheck not installed")
fi
if command -v gitleaks >/dev/null 2>&1; then
    run_step "secrets in git (gitleaks)" secrets_in_git
else
    REPORT+=("SKIP  secrets in git — gitleaks not installed (CI always runs it)")
fi
COMPOSE=()
if command -v podman >/dev/null 2>&1 && podman compose version >/dev/null 2>&1; then
    COMPOSE=(podman compose)
elif command -v docker >/dev/null 2>&1 && docker compose version >/dev/null 2>&1; then
    COMPOSE=(docker compose)
fi
if [ ${#COMPOSE[@]} -gt 0 ]; then
    run_step "compose stack (compose config)" compose_file
else
    REPORT+=("SKIP  compose stack — neither podman compose nor docker compose")
fi

echo
echo "==================== check report ===================="
for line in "${REPORT[@]}"; do
    echo "  $line"
done
echo "======================================================"
exit "$FAILED"
