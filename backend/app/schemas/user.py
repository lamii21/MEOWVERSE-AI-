import re
import uuid
from datetime import datetime

from pydantic import BaseModel, EmailStr, Field, field_validator


class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=72)
    display_name: str = Field(min_length=1, max_length=60)

    @field_validator("password")
    @classmethod
    def _password_strength(cls, v: str) -> str:
        # Deliberately simple, real checks (not a fake "strength meter"):
        # a minimum length (enforced by Field above) plus at least one
        # letter and one digit. Not NIST-grade policy, but a genuine bar
        # above "12345678" — appropriate for this product's risk profile.
        if not re.search(r"[A-Za-z]", v) or not re.search(r"\d", v):
            raise ValueError("Password must contain at least one letter and one number.")
        return v

    @field_validator("display_name")
    @classmethod
    def _display_name_not_blank(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Display name can't be blank.")
        return v.strip()


class UserLogin(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=72)


class UserUpdate(BaseModel):
    """PATCH /api/v1/auth/me — every field optional, only provided ones change."""

    display_name: str | None = Field(default=None, min_length=1, max_length=60)
    avatar_url: str | None = Field(default=None, max_length=500)


class UserOut(BaseModel):
    """Never includes `password_hash` — this is the only shape a user
    (their own or, in principle, anyone's public profile) is ever
    rendered as."""

    id: uuid.UUID
    email: EmailStr
    display_name: str
    avatar_url: str | None
    created_at: datetime
