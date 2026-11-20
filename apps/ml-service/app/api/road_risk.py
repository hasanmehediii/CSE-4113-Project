from typing import Literal

from fastapi import APIRouter, Request
from pydantic import AwareDatetime, BaseModel, ConfigDict, Field

from app.core.diagnostics import require_model

router = APIRouter(prefix="/road-risk", tags=["Road risk"])


class Scenario(BaseModel):
    model_config = ConfigDict(extra="forbid")
    at: AwareDatetime
    rainfall_mm: float = Field(default=0, ge=0, le=150, allow_inf_nan=False)
    forecast_horizon_min: Literal[30, 60, 120] = 60


def loaded(request):
    return require_model(request, "road_risk")


@router.post("/predict")
def predict(payload: Scenario, request: Request):
    return loaded(request).predict(payload.at, payload.rainfall_mm, payload.forecast_horizon_min)


@router.get("/model")
def model_info(request: Request):
    return loaded(request).metadata
