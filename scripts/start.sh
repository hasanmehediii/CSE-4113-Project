#!/usr/bin/env bash
# Linux equivalent of the root start.ps1; works from any current directory.
set -Eeuo pipefail
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
source "$SCRIPT_DIR/docker-common.sh"

usage() {
    cat <<'HELP'
Usage: bash scripts/start.sh [options]

Start the complete DubsiBhai stack in Docker (builds images by default).

  --stop          Stop the stack; keep database and model volumes
  --logs          Follow logs; Ctrl+C exits the log viewer only
  --status        Show all project containers
  --no-build      Start using existing images; do not build missing images
  --data-only     Target PostgreSQL, MongoDB, Redis and Mailpit only
  --timeout SEC   Startup timeout in seconds, 30..1800 (default: 600)
  -h, --help      Show this help without requiring Docker

Choose at most one of --stop, --logs and --status.
HELP
}

action=start
build=true
data_only=false
timeout=600
while (($#)); do
    case "$1" in
        --stop|--logs|--status)
            [[ $action == start ]] || die 'Choose only one of --stop, --logs or --status.'
            action="${1#--}"
            ;;
        --no-build) build=false ;;
        --data-only) data_only=true ;;
        --timeout)
            (($# >= 2)) || die '--timeout requires an integer between 30 and 1800.'
            [[ $2 =~ ^[0-9]{2,4}$ ]] || die '--timeout must be an integer between 30 and 1800.'
            timeout=$((10#$2))
            ((timeout >= 30 && timeout <= 1800)) || die '--timeout must be between 30 and 1800.'
            shift
            ;;
        -h|--help) usage; exit 0 ;;
        *) die "Unknown option: $1. See: bash scripts/start.sh --help" ;;
    esac
    shift
done

init_compose
targets=()
if [[ $data_only == true ]]; then targets=("${DATA_SERVICES[@]}"); fi
case "$action" in
    stop)
        if [[ $data_only == true ]]; then run_compose stop "${targets[@]}"; else run_compose down; fi
        printf 'Stopped. Database and model volumes are preserved.\n'
        ;;
    logs)
        exec "${COMPOSE[@]}" logs --follow --tail 100 "${targets[@]}"
        ;;
    status)
        run_compose ps --all "${targets[@]}"
        ;;
    start)
        validate_client_ids
        args=(up --detach --wait --wait-timeout "$timeout")
        if [[ $data_only == true ]]; then
            printf 'Starting PostgreSQL, MongoDB, Redis and Mailpit in Docker.\n'
        else
            printf 'Starting DubsiBhai in Docker. First startup installs dependencies and trains missing models.\n'
            if [[ $build == true ]]; then args+=(--build); else args+=(--no-build); fi
        fi
        run_compose "${args[@]}" "${targets[@]}"
        if [[ $data_only == true ]]; then
            printf 'Data services ready. PostgreSQL: 5432 | MongoDB: 27017 | Redis: 6379\n'
        else
            printf 'Frontend: http://localhost:3000\n'
            printf 'API docs: http://localhost:8000/docs | ML docs: http://localhost:8001/docs\n'
            printf 'Service hub: http://localhost:8080\n'
        fi
        printf 'Development email inbox: http://localhost:8025\n'
        printf 'Logs: bash scripts/start.sh --logs | Stop: bash scripts/start.sh --stop\n'
        ;;
esac
