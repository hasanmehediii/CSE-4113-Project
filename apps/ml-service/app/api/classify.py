from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field, field_validator

from app.models.classifier import normalize_text

router = APIRouter(tags=["Classification"])


class ClassifyRequest(BaseModel):
    text: str = Field(min_length=1, max_length=5000)

    @field_validator("text")
    @classmethod
    def nonblank_text(cls, value: str) -> str:
        value = normalize_text(value)
        if not value:
            raise ValueError("Complaint text must not be blank.")
        return value


class ClassifyResponse(BaseModel):
    predicted_category: str
    confidence: float = Field(ge=0, le=1)
    probabilities: dict[str, float]
    model_version: str
    data_source: str


@router.post("/classify", response_model=ClassifyResponse)
def classify(payload: ClassifyRequest, request: Request) -> dict:
    model = getattr(request.app.state, "classifier", None)
    if model is None:
        raise HTTPException(503, "Classifier unavailable. Run training and restart the ML service.")
    return model.predict(payload.text)


@router.get("/model")
def model_info(request: Request) -> dict:
    model = getattr(request.app.state, "classifier", None)
    if model is None:
        raise HTTPException(503, "Classifier unavailable. Run training and restart the ML service.")
    return model.metadata
