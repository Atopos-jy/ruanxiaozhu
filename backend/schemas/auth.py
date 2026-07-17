from pydantic import BaseModel, EmailStr, Field, field_validator

from config import ACCESS_TOKEN_EXPIRE_MINUTES


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    accepted_terms: bool

    @field_validator("accepted_terms")
    @classmethod
    def terms_must_be_accepted(cls, accepted_terms: bool) -> bool:
        if not accepted_terms:
            raise ValueError("请先同意服务条款和隐私政策")
        return accepted_terms


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class UserResponse(BaseModel):
    id: str
    email: EmailStr


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int = ACCESS_TOKEN_EXPIRE_MINUTES * 60
    user: UserResponse


class RefreshRequest(BaseModel):
    refresh_token: str


class LogoutRequest(BaseModel):
    refresh_token: str | None = None
