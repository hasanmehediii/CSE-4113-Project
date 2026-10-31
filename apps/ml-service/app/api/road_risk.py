from typing import Literal

from fastapi import APIRouter, HTTPException, Request
from pydantic import AwareDatetime, BaseModel, ConfigDict, Field

router = APIRouter(prefix="/road-risk", tags=["Road risk"])


class Scenario(BaseModel):
    model_config = ConfigDict(extra="forbid")
    at: AwareDatetime
    rainfall_mm: float = Field(default=0, ge=0, le=150, allow_inf_nan=False)
    forecast_horizon_min: Literal[30, 60, 120] = 60


def loaded(request):
    model = getattr(request.app.state, "road_risk", None)
    if model is None:
        raise HTTPException(503, "Road-risk model unavailable. Run python -m app.train_road_risk and restart.")
    return model


@router.post("/predict")
def predict(payload: Scenario, request: Request):
    return loaded(request).predict(payload.at, payload.rainfall_mm, payload.forecast_horizon_min)


@router.get("/model")
def model_info(request: Request):
    return loaded(request).metadata
