#!/usr/bin/env bash
# Seed catalogs and the configured mayor through the existing idempotent bootstrap.
set -Eeuo pipefail
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
source "$SCRIPT_DIR/docker-common.sh"
helper_arguments seed.sh 'Apply migrations and seed catalogs plus the mayor configured in .env. Existing passwords are preserved.' "$@"
init_compose
run_compose build api
start_data_services
run_compose run --rm --no-deps -T api sh -c \
    'uv run --no-sync alembic upgrade head && uv run --no-sync python -m app.workers.bootstrap'
printf 'Catalog/admin bootstrap complete.\n'
