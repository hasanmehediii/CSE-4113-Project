param(
    [ValidateSet('project_events', 'classify_reports')][string]$Worker = 'project_events',
    [switch]$SkipInstall
)
$ErrorActionPreference = 'Stop'
Push-Location $PSScriptRoot
try {
    if (-not $SkipInstall) {
        & uv sync --locked
        if ($LASTEXITCODE -ne 0) { throw 'API worker dependency installation failed.' }
    }
    & uv run --no-sync python -m "app.workers.$Worker"
    if ($LASTEXITCODE -ne 0) { throw "Worker exited with code $LASTEXITCODE." }
} finally {
    Pop-Location
}
