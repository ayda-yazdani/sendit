import json

import httpx
import pytest

from app.config import Settings
from app.schemas.auth import RefreshSessionRequest, SignInRequest
from app.services.supabase_auth import SupabaseAuthService


def build_settings() -> Settings:
    return Settings.model_validate(
        {
            "supabase_url": "https://example.supabase.co",
            "SUPABASE_PUBLISHABLE_KEY": "test-key",
        }
    )


@pytest.mark.anyio
async def test_sign_in_calls_supabase_token_endpoint_and_returns_session() -> None:
    captured_request: httpx.Request | None = None

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal captured_request
        captured_request = request
        return httpx.Response(
            200,
            json={
                "access_token": "access-token",
                "refresh_token": "refresh-token",
                "token_type": "bearer",
                "expires_in": 3600,
                "user": {"id": "user-123", "email": "user@example.com"},
            },
            request=request,
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        service = SupabaseAuthService(http_client=client, settings=build_settings())
        result = await service.sign_in(
            SignInRequest(email="user@example.com", password="supersecret")
        )

    assert captured_request is not None
    assert str(captured_request.url) == (
        "https://example.supabase.co/auth/v1/token?grant_type=password"
    )
    assert captured_request.headers["apikey"] == "test-key"
    assert captured_request.headers["Authorization"] == "Bearer test-key"
    assert json.loads(captured_request.content.decode()) == {
        "email": "user@example.com",
        "password": "supersecret",
    }
    assert result.user is not None
    assert result.user.email == "user@example.com"
    assert result.session is not None
    assert result.session.access_token == "access-token"


@pytest.mark.anyio
async def test_refresh_session_calls_supabase_refresh_token_endpoint() -> None:
    captured_request: httpx.Request | None = None

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal captured_request
        captured_request = request
        return httpx.Response(
            200,
            json={
                "access_token": "new-access-token",
                "refresh_token": "refresh-token",
                "token_type": "bearer",
                "expires_in": 3600,
                "user": {"id": "user-123", "email": "user@example.com"},
            },
            request=request,
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        service = SupabaseAuthService(http_client=client, settings=build_settings())
        result = await service.refresh_session(
            RefreshSessionRequest(refresh_token="refresh-token")
        )

    assert captured_request is not None
    assert str(captured_request.url) == (
        "https://example.supabase.co/auth/v1/token?grant_type=refresh_token"
    )
    assert json.loads(captured_request.content.decode()) == {
        "refresh_token": "refresh-token"
    }
    assert result.session is not None
    assert result.session.access_token == "new-access-token"


@pytest.mark.anyio
async def test_get_current_user_uses_access_token_for_supabase_lookup() -> None:
    captured_request: httpx.Request | None = None

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal captured_request
        captured_request = request
        return httpx.Response(
            200,
            json={
                "id": "user-123",
                "email": "user@example.com",
                "email_confirmed_at": "2026-03-27T11:22:33Z",
            },
            request=request,
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        service = SupabaseAuthService(http_client=client, settings=build_settings())
        result = await service.get_current_user("access-token")

    assert captured_request is not None
    assert str(captured_request.url) == "https://example.supabase.co/auth/v1/user"
    assert captured_request.headers["Authorization"] == "Bearer access-token"
    assert result.user.id == "user-123"
    assert result.user.email == "user@example.com"
