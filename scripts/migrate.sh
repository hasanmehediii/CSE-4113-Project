#!/usr/bin/env bash
# Apply database migrations using the API image; no host Python is required.
set -Eeuo pipefail
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
source "$SCRIPT_DIR/docker-common.sh"
helper_arguments migrate.sh 'Build the API image, start its data services and apply Alembic migrations.' "$@"
init_compose
run_compose build api
start_data_services
run_compose run --rm --no-deps -T api uv run --no-sync alembic upgrade head
printf 'Database migrations applied.\n'
