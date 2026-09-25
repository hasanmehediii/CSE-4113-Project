param(
    [string]$Dataset = (Join-Path $PSScriptRoot '../../docs/dataset/drainage_complaints_bn.csv'),
    [ValidateSet('synthetic', 'real', 'mixed')]
    [string]$DataSource = 'synthetic'
)

$ErrorActionPreference = 'Stop'
if (-not (Get-Command uv -ErrorAction SilentlyContinue)) {
    throw 'Install uv and Python 3.11+, then reopen PowerShell.'
}
$datasetPath = (Resolve-Path -LiteralPath $Dataset).Path
Push-Location $PSScriptRoot
try {
    & uv sync --locked
    if ($LASTEXITCODE -ne 0) { throw 'ML dependency installation failed.' }
    & uv run --no-sync python -m app.train --dataset $datasetPath --data-source $DataSource
    if ($LASTEXITCODE -ne 0) { throw 'Classifier training failed.' }
} finally {
    Pop-Location
}
