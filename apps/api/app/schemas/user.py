from datetime import UTC, date, datetime
from typing import Literal

from pydantic import (
    AliasChoices,
    BaseModel,
    ConfigDict,
    EmailStr,
    Field,
    field_validator,
    model_validator,
)

from app.core.security import PASSWORD_MAX_LENGTH, PASSWORD_MIN_LENGTH
from app.schemas.civic import WorkerApplicationInput
from app.utilities.validation import normalize_phone


class EmailInput(BaseModel):
    email: EmailStr

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value):
        return str(value).lower()


class RegisterInput(EmailInput):
    model_config = ConfigDict(extra="forbid")
    name: str = Field(min_length=1, max_length=100)
    password: str = Field(min_length=PASSWORD_MIN_LENGTH, max_length=PASSWORD_MAX_LENGTH)
    phone: str | None = Field(default=None, max_length=30)
    date_of_birth: date | None = None
    blood_group: str | None = None
    account_type: Literal["citizen", "worker"] = "citizen"
    worker_identity: WorkerApplicationInput | None = None

    @model_validator(mode="after")
    def validate_account_type(self):
        if self.account_type == "worker" and self.worker_identity is None:
            raise ValueError("Worker signup requires a NID number or private NID image link")
        if self.account_type == "citizen" and self.worker_identity is not None:
            raise ValueError("Identity documents are only needed for worker applications")
        return self

    @field_validator("phone")
    @classmethod
    def clean_phone(cls, value):
        return normalize_phone(value) if value else None

    @field_validator("date_of_birth")
    @classmethod
    def clean_dob(cls, value):
        if value and (value > datetime.now(UTC).date() or value.year < 1900):
            raise ValueError("Enter a valid date of birth")
        return value

    @field_validator("blood_group")
    @classmethod
    def clean_blood(cls, value):
        if value and value not in {"A+", "A-", "B+", "B-", "AB+", "AB-", "O+", "O-"}:
            raise ValueError("Unknown blood group")
        return value or None

    @field_validator("name")
    @classmethod
    def clean_name(cls, value):
        if not value.strip():
            raise ValueError("Name cannot be blank")
        return value.strip()


class LoginInput(BaseModel):
    identifier: str = Field(
        min_length=3, max_length=320, validation_alias=AliasChoices("identifier", "email")
    )
    password: str = Field(min_length=1, max_length=128)

    @field_validator("identifier")
    @classmethod
    def clean_identifier(cls, value):
        value = value.strip().lower()
        return value if "@" in value else normalize_phone(value)


class RecoveryInput(EmailInput):
    remembered_password: str = Field(min_length=1, max_length=128)
    date_of_birth: date


class TokenInput(BaseModel):
    token: str = Field(min_length=20, max_length=256)


class ResetInput(TokenInput):
    password: str = Field(min_length=PASSWORD_MIN_LENGTH, max_length=PASSWORD_MAX_LENGTH)


class GoogleInput(BaseModel):
    credential: str = Field(min_length=1, max_length=8192)
    nonce: str = Field(min_length=20, max_length=256)


class UserOutput(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    email: str
    name: str
    email_verified: bool
    role: str
    phone: str | None
    date_of_birth: date | None
    blood_group: str | None
    worker_application_status: str | None = None
