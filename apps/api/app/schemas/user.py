from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


class EmailInput(BaseModel):
    email: EmailStr

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value):
        return str(value).lower()


class RegisterInput(EmailInput):
    name: str = Field(min_length=1, max_length=100)
    password: str = Field(min_length=15, max_length=128)

    @field_validator("name")
    @classmethod
    def clean_name(cls, value):
        if not value.strip():
            raise ValueError("Name cannot be blank")
        return value.strip()


class LoginInput(EmailInput):
    password: str = Field(min_length=1, max_length=128)


class TokenInput(BaseModel):
    token: str = Field(min_length=20, max_length=256)


class ResetInput(TokenInput):
    password: str = Field(min_length=15, max_length=128)


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
