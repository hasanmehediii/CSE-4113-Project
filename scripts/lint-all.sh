#!/usr/bin/env bash
# Run checks in disposable containers, using the projects' locked dependencies.
set -Eeuo pipefail
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
source "$SCRIPT_DIR/docker-common.sh"
helper_arguments lint-all.sh 'Run API/ML Ruff, frontend ESLint and TypeScript checks in Docker; no databases are started.' "$@"
init_compose
run_compose build api ml-service web
run_compose run --rm --no-deps -T \
    --volume "$REPO_ROOT/apps/api/tests:/workspace/apps/api/tests:ro" \
    api uv run --locked --group dev ruff check app tests
run_compose run --rm --no-deps -T \
    --volume "$REPO_ROOT/apps/ml-service/tests:/workspace/apps/ml-service/tests:ro" \
    ml-service uv run --locked --group dev ruff check app tests
run_compose run --rm --no-deps -T web pnpm lint
run_compose run --rm --no-deps -T web pnpm typecheck
printf 'All lint and type checks passed.\n'
