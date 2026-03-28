from typing import Any

from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class SupabaseModel(BaseModel):
    model_config = ConfigDict(extra="allow")


class WeakPasswordDetails(SupabaseModel):
    reasons: list[str] | None = None
    message: str | None = None


class UserIdentity(SupabaseModel):
    identity_id: str | None = None
    id: str | None = None
    user_id: str | None = None
    identity_data: dict[str, Any] | None = None
    provider: str | None = None
    last_sign_in_at: datetime | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
    email: EmailStr | None = None


class SupabaseUser(SupabaseModel):
    id: str
    aud: str | None = None
    role: str | None = None
    email: EmailStr | None = None
    phone: str | None = None
    app_metadata: dict[str, Any] | None = None
    user_metadata: dict[str, Any] | None = None
    identities: list[UserIdentity] | None = None
    is_anonymous: bool | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
    confirmed_at: datetime | None = None
    email_confirmed_at: datetime | None = None
    phone_confirmed_at: datetime | None = None
    last_sign_in_at: datetime | None = None
    banned_until: datetime | None = None
    confirmation_sent_at: datetime | None = None
    recovery_sent_at: datetime | None = None
    email_change_sent_at: datetime | None = None
    phone_change_sent_at: datetime | None = None
    reauthentication_sent_at: datetime | None = None
    invited_at: datetime | None = None
    new_email: str | None = None
    new_phone: str | None = None


class SupabaseSession(SupabaseModel):
    access_token: str
    token_type: str
    expires_in: int | None = None
    expires_at: int | None = None
    refresh_token: str | None = None
    provider_token: str | None = None
    provider_refresh_token: str | None = None
    weak_password: WeakPasswordDetails | None = None


class SignUpRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    metadata: dict[str, Any] | None = None


class SignInRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class RefreshSessionRequest(BaseModel):
    refresh_token: str = Field(min_length=1)


class AuthResponse(BaseModel):
    user: SupabaseUser | None = None
    session: SupabaseSession | None = None
    message: str | None = None


class UserResponse(BaseModel):
    user: SupabaseUser
