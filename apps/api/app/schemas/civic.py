from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.utilities.validation import image_link


class Input(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class LocationInput(Input):
    latitude: float = Field(ge=23.60, le=24.00, allow_inf_nan=False)
    longitude: float = Field(ge=90.20, le=90.60, allow_inf_nan=False)


class ComplaintInput(LocationInput):
    incident_id: str | None = Field(default=None, min_length=36, max_length=36)
    separate_incident: bool = False
    road_id: str | None = Field(default=None, max_length=36)
    category_code: str = Field(min_length=1, max_length=40)
    kind: Literal["complaint", "road_update"] = "complaint"
    title: str = Field(min_length=5, max_length=180)
    description: str = Field(min_length=10, max_length=5000)
    address: str = Field(min_length=3, max_length=300)
    condition: Literal["bad", "good", "unknown"] = "bad"
    images: list[str] = Field(default_factory=list, max_length=5)

    @field_validator("images")
    @classmethod
    def clean_images(cls, values):
        if any(len(v) > 2048 for v in values):
            raise ValueError("Image URL is too long")
        return list(dict.fromkeys(image_link(v) for v in values))

    @model_validator(mode="after")
    def complaint_condition(self):
        if self.kind == "complaint" and self.condition != "bad":
            raise ValueError("Complaints describe bad conditions; use road_update for good/unknown")
        if self.incident_id and self.separate_incident:
            raise ValueError("Choose an existing incident or a separate incident, not both")
        if self.kind == "road_update" and (self.incident_id or self.separate_incident):
            raise ValueError("Incident grouping applies to complaints, not road updates")
        return self


class VoteInput(Input):
    value: Literal[-1, 1]


class EvidenceInput(Input):
    image_url: str = Field(min_length=8, max_length=2048)
    comment: str = Field(min_length=5, max_length=1000)

    _url = field_validator("image_url")(image_link)


class ResolutionInput(Input):
    comment: str = Field(min_length=5, max_length=2000)
    image_url: str | None = Field(default=None, max_length=2048)

    @field_validator("image_url")
    @classmethod
    def url(cls, value):
        return image_link(value) if value else None


class ResolutionVoteInput(ResolutionInput, VoteInput):
    comment: str | None = Field(default=None, max_length=1000)

    @model_validator(mode="after")
    def evidence_required(self):
        if self.value == -1 and not self.image_url:
            raise ValueError("A dislike requires image evidence")
        return self


class WorkerApplicationInput(Input):
    nid_number: str | None = Field(default=None, pattern=r"^(?:\d{10}|\d{13}|\d{17})$")
    nid_image_url: str | None = Field(default=None, max_length=2048)

    @field_validator("nid_image_url")
    @classmethod
    def url(cls, value):
        if value and not value.startswith("https://"):
            raise ValueError(
                "NID links must use a private HTTPS location, not public report uploads"
            )
        return image_link(value) if value else None

    @model_validator(mode="after")
    def identity_required(self):
        if not self.nid_number and not self.nid_image_url:
            raise ValueError("Provide a NID number or a private NID image link")
        return self


class WorkerLocationInput(LocationInput):
    available: bool = True


class AvailabilityInput(Input):
    available: bool


class ReviewInput(Input):
    approve: bool
    note: str = Field(min_length=3, max_length=1000)


class AssignInput(Input):
    worker_id: str | None = Field(default=None, min_length=36, max_length=36)
    reassign: bool = False


class BlockInput(Input):
    blocked: bool
    reason: str = Field(min_length=5, max_length=1000)


class CaseReviewInput(Input):
    status: Literal["dismissed", "actioned"]
    note: str = Field(min_length=5, max_length=1000)


class RoadInput(LocationInput):
    area_id: str = Field(min_length=36, max_length=36)
    name: str = Field(min_length=3, max_length=150)


class AreaInput(Input):
    name: str = Field(min_length=3, max_length=100)
    ward: str | None = Field(default=None, max_length=30)
