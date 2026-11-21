"""Explain why a model artifact failed to load, in API errors as well as the logs.

Startup never overwrites an existing artifact, so "train a model" is the wrong advice
when a file exists but is corrupt or incompatible; the reason tells the two apart.
"""
from pathlib import Path

from fastapi import HTTPException, Request

MODELS = {
    # state attribute: (display name, training command)
    "classifier": ("Classifier", "python -m app.train"),
    "road_risk": ("Road-risk model", "python -m app.train_road_risk"),
}


def describe_load_failure(kind: str, path: Path, error: Exception) -> str:
    name, command = MODELS[kind]
    if isinstance(error, FileNotFoundError):
        return f"{name} unavailable: {path.name} was not found. Run {command}, then restart the ML service."
    if isinstance(error, ValueError):
        reason = f"{path.name} is incompatible: {str(error).rstrip('.')}."
    else:
        reason = (f"{path.name} could not be read ({type(error).__name__}); "
                  "it may be corrupt or not produced by this service.")
    return (f"{name} unavailable: {reason} Retrain explicitly with {command} "
            "(startup never replaces an existing file), then restart the ML service.")


def require_model(request: Request, kind: str):
    model = getattr(request.app.state, kind, None)
    if model is None:
        name, command = MODELS[kind]
        detail = getattr(request.app.state, f"{kind}_error", None) or (
            f"{name} unavailable. Run {command}, then restart the ML service.")
        raise HTTPException(503, detail)
    return model
