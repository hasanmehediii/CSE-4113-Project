#!/usr/bin/env bash
# Shared functions for the Linux Docker launchers. Do not source .env as shell code.
set -Eeuo pipefail

REPO_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)"
DATA_SERVICES=(db mongodb redis mailpit)

die() {
    printf 'Error: %s\n' "$*" >&2
    exit 1
}

docker_failure() {
    local status=$?
    printf 'Docker command failed (exit %s). Inspect the error above.\n' "$status" >&2
    printf 'Logs: bash "%s/scripts/start.sh" --logs\n' "$REPO_ROOT" >&2
    printf 'For a port conflict, stop the competing server before retrying.\n' >&2
    exit "$status"
}
trap docker_failure ERR

ensure_env_files() {
    local target example
    for target in .env apps/web/.env.local; do
        if [[ $target == .env ]]; then example=.env.example; else example=apps/web/.env.example; fi
        if [[ ! -e "$REPO_ROOT/$target" ]]; then
            [[ -f "$REPO_ROOT/$example" ]] || die "Missing environment example: $example"
            (umask 077; cp -n -- "$REPO_ROOT/$example" "$REPO_ROOT/$target")
            printf 'Created %s from its example.\n' "$target"
        fi
        [[ -f "$REPO_ROOT/$target" ]] || die "Expected a configuration file: $target"
    done
}

init_compose() {
    command -v docker >/dev/null 2>&1 || die 'Install Docker Engine or Docker Desktop, including the Compose v2 plugin.'
    if ! docker info >/dev/null 2>&1; then
        die 'Docker is unavailable. Start its engine and check that your user can access it.'
    fi
    if ! docker compose version >/dev/null 2>&1; then
        die 'Docker Compose v2 is required. Install or update the Compose plugin.'
    fi
    ensure_env_files
    COMPOSE=(docker compose
        --project-directory "$REPO_ROOT/infra"
        --env-file "$REPO_ROOT/.env"
        --env-file "$REPO_ROOT/apps/web/.env.local"
        -f "$REPO_ROOT/infra/docker-compose.local.yml")
    run_compose config --quiet
}

run_compose() {
    "${COMPOSE[@]}" "$@"
}

trim() {
    local value=$1
    value="${value#"${value%%[![:space:]]*}"}"
    value="${value%"${value##*[![:space:]]}"}"
    printf '%s' "$value"
}

read_client_id() {
    # OAuth client IDs are simple strings; read them without evaluating dotenv content.
    local file=$1 key=$2 line value='' expression
    expression="^[[:space:]]*(export[[:space:]]+)?${key}[[:space:]]*=(.*)$"
    while IFS= read -r line || [[ -n $line ]]; do
        line="${line%$'\r'}"
        line="${line#$'\xef\xbb\xbf'}"
        if [[ $line =~ $expression ]]; then
            value="$(trim "${BASH_REMATCH[2]}")"
            case "$value" in
                \"*) value="${value#\"}"; value="${value%%\"*}" ;;
                \'*) value="${value#\'}"; value="${value%%\'*}" ;;
                *) value="${value%%[[:space:]]#*}"; value="$(trim "$value")" ;;
            esac
        fi
    done < "$file"
    printf '%s' "$value"
}

validate_client_ids() {
    local server_id browser_id
    server_id="$(read_client_id "$REPO_ROOT/.env" GOOGLE_CLIENT_ID)"
    browser_id="$(read_client_id "$REPO_ROOT/apps/web/.env.local" NEXT_PUBLIC_GOOGLE_CLIENT_ID)"
    if [[ -n $server_id && -n $browser_id && $server_id != "$browser_id" ]]; then
        die 'Google client IDs in .env and apps/web/.env.local differ. Set them to the same OAuth web client ID.'
    fi
}

start_data_services() {
    run_compose up --detach --wait --wait-timeout 600 "${DATA_SERVICES[@]}"
}

helper_arguments() {
    local name=$1 description=$2
    shift 2
    if [[ ${1:-} == --help || ${1:-} == -h ]]; then
        printf 'Usage: bash scripts/%s\n%s\n' "$name" "$description"
        exit 0
    fi
    [[ $# == 0 ]] || die "Unexpected argument. See: bash scripts/$name --help"
}
