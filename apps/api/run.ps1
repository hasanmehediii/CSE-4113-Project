param([switch]$SkipInstall)
$ErrorActionPreference = 'Stop'

if (-not (Get-Command uv -ErrorAction SilentlyContinue)) {
    throw 'Install uv and Python 3.11+, then reopen PowerShell.'
}

Push-Location $PSScriptRoot
try {
    if (-not $SkipInstall) {
        & uv sync --locked
        if ($LASTEXITCODE -ne 0) { throw 'API dependency installation failed.' }
    }

    & uv run --no-sync python -m alembic upgrade head
    if ($LASTEXITCODE -ne 0) { throw 'Database migration failed. Start the Docker data services first.' }
    & uv run --no-sync python -m app.workers.bootstrap
    if ($LASTEXITCODE -ne 0) { throw 'Catalog/admin bootstrap failed. Check the server-only .env settings.' }

    & uv run --no-sync uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
    if ($LASTEXITCODE -ne 0) { throw "FastAPI exited with code $LASTEXITCODE." }
} finally {
    Pop-Location
}
