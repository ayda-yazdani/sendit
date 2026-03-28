import os
import sys
from collections.abc import Generator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

os.environ.setdefault("SUPABASE_URL", "https://example.supabase.co")
os.environ.setdefault("SUPABASE_PUBLISHABLE_KEY", "test-key")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.dependencies import get_supabase_auth_service
from app.main import app
from app.schemas.auth import (
    AuthResponse,
    RefreshSessionRequest,
    SignInRequest,
    SignUpRequest,
    SupabaseSession,
    SupabaseUser,
    UserResponse,
)


class StubSupabaseAuthService:
    def __init__(self) -> None:
        self.signup_payload: SignUpRequest | None = None
        self.login_payload: SignInRequest | None = None
        self.refresh_payload: RefreshSessionRequest | None = None
        self.current_user_token: str | None = None
        self.logout_token: str | None = None

    async def sign_up(self, payload: SignUpRequest) -> AuthResponse:
        self.signup_payload = payload
        return AuthResponse(
            user=SupabaseUser(id="user-123", email=payload.email),
            session=SupabaseSession(
                access_token="access-token",
                token_type="bearer",
                refresh_token="refresh-token",
                expires_in=3600,
            ),
        )

    async def sign_in(self, payload: SignInRequest) -> AuthResponse:
        self.login_payload = payload
        return AuthResponse(
            user=SupabaseUser(id="user-123", email=payload.email),
            session=SupabaseSession(
                access_token="login-token",
                token_type="bearer",
                refresh_token="login-refresh-token",
                expires_in=3600,
            ),
        )

    async def refresh_session(self, payload: RefreshSessionRequest) -> AuthResponse:
        self.refresh_payload = payload
        return AuthResponse(
            user=SupabaseUser(id="user-123", email="user@example.com"),
            session=SupabaseSession(
                access_token="new-access-token",
                token_type="bearer",
                refresh_token=payload.refresh_token,
                expires_in=3600,
            ),
        )

    async def get_current_user(self, access_token: str) -> UserResponse:
        self.current_user_token = access_token
        return UserResponse(
            user=SupabaseUser(id="user-123", email="user@example.com")
        )

    async def sign_out(self, access_token: str) -> None:
        self.logout_token = access_token


@pytest.fixture
def stub_auth_service() -> StubSupabaseAuthService:
    return StubSupabaseAuthService()


@pytest.fixture
def client(stub_auth_service: StubSupabaseAuthService) -> Generator[TestClient, None, None]:
    app.dependency_overrides[get_supabase_auth_service] = lambda: stub_auth_service
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def test_health_check_returns_ok(client: TestClient) -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_signup_returns_created_auth_payload(
    client: TestClient,
    stub_auth_service: StubSupabaseAuthService,
) -> None:
    response = client.post(
        "/api/v1/auth/signup",
        json={
            "email": "user@example.com",
            "password": "supersecret",
            "metadata": {"name": "Max"},
        },
    )

    assert response.status_code == 201
    assert stub_auth_service.signup_payload is not None
    assert stub_auth_service.signup_payload.email == "user@example.com"
    assert stub_auth_service.signup_payload.metadata == {"name": "Max"}
    assert response.json()["session"]["access_token"] == "access-token"


def test_login_returns_auth_payload(
    client: TestClient,
    stub_auth_service: StubSupabaseAuthService,
) -> None:
    response = client.post(
        "/api/v1/auth/login",
        json={"email": "user@example.com", "password": "supersecret"},
    )

    assert response.status_code == 200
    assert stub_auth_service.login_payload is not None
    assert stub_auth_service.login_payload.email == "user@example.com"
    assert response.json()["session"]["access_token"] == "login-token"


def test_refresh_returns_rotated_session(
    client: TestClient,
    stub_auth_service: StubSupabaseAuthService,
) -> None:
    response = client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": "refresh-token"},
    )

    assert response.status_code == 200
    assert stub_auth_service.refresh_payload is not None
    assert stub_auth_service.refresh_payload.refresh_token == "refresh-token"
    assert response.json()["session"]["access_token"] == "new-access-token"


def test_me_requires_bearer_token(client: TestClient) -> None:
    response = client.get("/api/v1/auth/me")

    assert response.status_code == 401
    assert response.json() == {"detail": "Missing bearer token."}


def test_me_returns_current_user_for_valid_token(
    client: TestClient,
    stub_auth_service: StubSupabaseAuthService,
) -> None:
    response = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": "Bearer access-token"},
    )

    assert response.status_code == 200
    assert stub_auth_service.current_user_token == "access-token"
    assert response.json()["user"]["email"] == "user@example.com"


def test_logout_revokes_session(
    client: TestClient,
    stub_auth_service: StubSupabaseAuthService,
) -> None:
    response = client.post(
        "/api/v1/auth/logout",
        headers={"Authorization": "Bearer access-token"},
    )

    assert response.status_code == 204
    assert response.text == ""
    assert stub_auth_service.logout_token == "access-token"
