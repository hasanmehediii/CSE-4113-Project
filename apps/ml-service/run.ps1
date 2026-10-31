param([switch]$SkipInstall)
$ErrorActionPreference = 'Stop'

if (-not (Get-Command uv -ErrorAction SilentlyContinue)) {
    throw 'Install uv and Python 3.11+, then reopen PowerShell.'
}

Push-Location $PSScriptRoot
try {
    if (-not $SkipInstall) {
        & uv sync --locked
        if ($LASTEXITCODE -ne 0) { throw 'ML service dependency installation failed.' }
    }

    # A missing artifact is expected on a fresh checkout. Do not replace an
    # existing, incompatible artifact silently, or ignore ML_MODEL_PATH.
    & uv run --no-sync python -c 'import sys; from app.core.config import get_settings; from app.models.classifier import ComplaintClassifier; path = get_settings().model_path; sys.exit(2) if not path.is_file() else ComplaintClassifier.load(path)'
    if ($LASTEXITCODE -eq 2) {
        Write-Host 'No classifier found. Training with the bundled synthetic dataset.'
        & uv run --no-sync python -m app.train
        if ($LASTEXITCODE -ne 0) { throw 'Initial ML training failed. Check the training output above.' }
    } elseif ($LASTEXITCODE -ne 0) {
        throw 'Existing ML model could not be loaded. Retrain explicitly with ./train.ps1.'
    }

    & uv run --no-sync python -c 'import sys; from app.core.config import get_settings; from app.models.road_risk import RoadRiskModel; path = get_settings().road_risk_model_path; sys.exit(2) if not path.is_file() else RoadRiskModel.load(path)'
    if ($LASTEXITCODE -eq 2) {
        Write-Host 'No road-risk model found. Generating synthetic scenarios and training.'
        & uv run --no-sync python -m app.train_road_risk
        if ($LASTEXITCODE -ne 0) { throw 'Road-risk model training failed.' }
    } elseif ($LASTEXITCODE -ne 0) {
        throw 'Existing road-risk model is incompatible. Run uv run python -m app.train_road_risk.'
    }

    & uv run --no-sync uvicorn app.main:app --reload --host 127.0.0.1 --port 8001
    if ($LASTEXITCODE -ne 0) { throw "ML service exited with code $LASTEXITCODE." }
} finally {
    Pop-Location
}
