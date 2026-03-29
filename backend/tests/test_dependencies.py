import pytest
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials

from app.dependencies import get_access_token, get_current_user, get_verified_user
from app.schemas.auth import SupabaseUser, UserResponse


class StubSupabaseAuthService:
    def __init__(self) -> None:
        self.last_access_token: str | None = None

    async def get_current_user(self, access_token: str) -> UserResponse:
        self.last_access_token = access_token
        return UserResponse(
            user=SupabaseUser(
                id="user-123",
                email="user@example.com",
                email_confirmed_at="2026-03-28T12:00:00Z",
            )
        )


def test_get_access_token_returns_bearer_credentials() -> None:
    token = get_access_token(
        HTTPAuthorizationCredentials(scheme="Bearer", credentials="access-token")
    )

    assert token == "access-token"


def test_get_access_token_rejects_missing_token() -> None:
    with pytest.raises(HTTPException) as exc_info:
        get_access_token(None)

    assert exc_info.value.status_code == 401
    assert exc_info.value.detail == "Missing bearer token."


def test_get_access_token_rejects_non_bearer_scheme() -> None:
    with pytest.raises(HTTPException) as exc_info:
        get_access_token(
            HTTPAuthorizationCredentials(scheme="Basic", credentials="access-token")
        )

    assert exc_info.value.status_code == 401
    assert exc_info.value.detail == "Missing bearer token."


@pytest.mark.anyio
async def test_get_current_user_returns_user_from_auth_service() -> None:
    auth_service = StubSupabaseAuthService()

    user = await get_current_user("access-token", auth_service)

    assert auth_service.last_access_token == "access-token"
    assert user.id == "user-123"
    assert user.email == "user@example.com"


@pytest.mark.anyio
async def test_get_verified_user_allows_confirmed_user() -> None:
    user = await get_verified_user(
        SupabaseUser(
            id="user-123",
            email="user@example.com",
            email_confirmed_at="2026-03-28T12:00:00Z",
        )
    )

    assert user.id == "user-123"


@pytest.mark.anyio
async def test_get_verified_user_rejects_anonymous_user() -> None:
    with pytest.raises(HTTPException) as exc_info:
        await get_verified_user(
            SupabaseUser(id="user-123", email="user@example.com", is_anonymous=True)
        )

    assert exc_info.value.status_code == 403
    assert exc_info.value.detail == "Anonymous users cannot access this resource."


@pytest.mark.anyio
async def test_get_verified_user_rejects_unverified_user() -> None:
    with pytest.raises(HTTPException) as exc_info:
        await get_verified_user(SupabaseUser(id="user-123", email="user@example.com"))

    assert exc_info.value.status_code == 403
    assert (
        exc_info.value.detail
        == "User must have a verified email or phone to access this resource."
    )
