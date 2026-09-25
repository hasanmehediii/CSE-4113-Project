$ErrorActionPreference = 'Stop'

if (-not (Get-Command uv -ErrorAction SilentlyContinue)) {
    throw 'Install uv and Python 3.11+, then reopen PowerShell.'
}

Push-Location $PSScriptRoot
try {
    & uv sync --locked
    if ($LASTEXITCODE -ne 0) { throw 'API dependency installation failed.' }

    & uv run --no-sync uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
    if ($LASTEXITCODE -ne 0) { throw "FastAPI exited with code $LASTEXITCODE." }
} finally {
    Pop-Location
}
