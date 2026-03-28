from typing import Any

from datetime import datetime

from pydantic import AnyHttpUrl, BaseModel, ConfigDict, EmailStr, Field, field_validator


class StrictAPIModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


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


class SignUpRequest(StrictAPIModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    metadata: dict[str, Any] | None = None

    @field_validator("password")
    @classmethod
    def validate_password_not_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Password must not be blank.")
        return value


class SignInRequest(StrictAPIModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)

    @field_validator("password")
    @classmethod
    def validate_signin_password_not_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Password must not be blank.")
        return value


class RefreshSessionRequest(StrictAPIModel):
    refresh_token: str = Field(min_length=1)

    @field_validator("refresh_token")
    @classmethod
    def validate_refresh_token_not_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Refresh token must not be blank.")
        return value


class AuthResponse(BaseModel):
    user: SupabaseUser | None = None
    session: SupabaseSession | None = None
    message: str | None = None


class UserResponse(BaseModel):
    user: SupabaseUser


class SupabaseConfigCheckResponse(BaseModel):
    ok: bool = True
    supabase_url: AnyHttpUrl
    auth_url: AnyHttpUrl
    key_present: bool = True
    disable_signup: bool | None = None
    external: dict[str, bool] = Field(default_factory=dict)
    message: str


class SupabaseRuntimeInfoResponse(BaseModel):
    api_base_url: str
    supabase_url: AnyHttpUrl
    auth_url: AnyHttpUrl
    key_present: bool = True
    key_name: str
