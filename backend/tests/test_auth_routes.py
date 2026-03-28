from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient

from app.dependencies import (
    get_instagram_reel_scraper_service,
    get_supabase_auth_service,
    get_tiktok_video_scraper_service,
    get_youtube_shorts_scraper_service,
)
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
from app.schemas.instagram import InstagramReelScrapeRequest, InstagramReelScrapeResponse
from app.schemas.tiktok import TikTokVideoScrapeRequest, TikTokVideoScrapeResponse
from app.schemas.youtube import YouTubeShortScrapeRequest, YouTubeShortScrapeResponse


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
            user=SupabaseUser(
                id="user-123",
                email="user@example.com",
                email_confirmed_at="2026-03-28T12:00:00Z",
            )
        )

    async def sign_out(self, access_token: str) -> None:
        self.logout_token = access_token


class StubInstagramReelScraperService:
    def __init__(self) -> None:
        self.request_payload: InstagramReelScrapeRequest | None = None

    async def scrape_reel(
        self, payload: InstagramReelScrapeRequest
    ) -> InstagramReelScrapeResponse:
        self.request_payload = payload
        return InstagramReelScrapeResponse(
            requested_url=payload.url,
            resolved_url="https://www.instagram.com/reel/abc123/",
            canonical_url="https://www.instagram.com/reel/abc123/",
            reel_id="abc123",
            title="Example reel",
            description="Example description",
            thumbnail_url="https://cdn.example.com/thumb.jpg",
            open_graph={"og:title": "Example reel"},
        )


class StubTikTokVideoScraperService:
    def __init__(self) -> None:
        self.request_payload: TikTokVideoScrapeRequest | None = None

    async def scrape_video(
        self, payload: TikTokVideoScrapeRequest
    ) -> TikTokVideoScrapeResponse:
        self.request_payload = payload
        return TikTokVideoScrapeResponse(
            requested_url=payload.url,
            resolved_url="https://www.tiktok.com/@creator/video/9876543210",
            canonical_url="https://www.tiktok.com/@creator/video/9876543210",
            video_id="9876543210",
            title="Example TikTok",
            description="Example TikTok description",
            thumbnail_url="https://cdn.example.com/tiktok-thumb.jpg",
            open_graph={"og:title": "Example TikTok"},
        )


class StubYouTubeShortsScraperService:
    def __init__(self) -> None:
        self.request_payload: YouTubeShortScrapeRequest | None = None

    async def scrape_short(
        self, payload: YouTubeShortScrapeRequest
    ) -> YouTubeShortScrapeResponse:
        self.request_payload = payload
        return YouTubeShortScrapeResponse(
            requested_url=payload.url,
            resolved_url="https://www.youtube.com/shorts/xyz987",
            canonical_url="https://www.youtube.com/shorts/xyz987",
            short_id="xyz987",
            title="Example Short",
            description="Example Short description",
            thumbnail_url="https://cdn.example.com/youtube-thumb.jpg",
            open_graph={"og:title": "Example Short"},
        )


@pytest.fixture
def stub_auth_service() -> StubSupabaseAuthService:
    return StubSupabaseAuthService()


@pytest.fixture
def stub_instagram_scraper_service() -> StubInstagramReelScraperService:
    return StubInstagramReelScraperService()


@pytest.fixture
def stub_tiktok_scraper_service() -> StubTikTokVideoScraperService:
    return StubTikTokVideoScraperService()


@pytest.fixture
def stub_youtube_scraper_service() -> StubYouTubeShortsScraperService:
    return StubYouTubeShortsScraperService()


@pytest.fixture
def client(
    stub_auth_service: StubSupabaseAuthService,
    stub_instagram_scraper_service: StubInstagramReelScraperService,
    stub_tiktok_scraper_service: StubTikTokVideoScraperService,
    stub_youtube_scraper_service: StubYouTubeShortsScraperService,
) -> Generator[TestClient, None, None]:
    app.dependency_overrides[get_supabase_auth_service] = lambda: stub_auth_service
    app.dependency_overrides[get_instagram_reel_scraper_service] = (
        lambda: stub_instagram_scraper_service
    )
    app.dependency_overrides[get_tiktok_video_scraper_service] = (
        lambda: stub_tiktok_scraper_service
    )
    app.dependency_overrides[get_youtube_shorts_scraper_service] = (
        lambda: stub_youtube_scraper_service
    )
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


def test_scrape_reel_requires_verified_bearer_token(client: TestClient) -> None:
    response = client.post(
        "/api/v1/instagram/reels/scrape",
        json={"url": "https://www.instagram.com/reel/abc123/"},
    )

    assert response.status_code == 401
    assert response.json() == {"detail": "Missing bearer token."}


def test_scrape_reel_returns_metadata_for_verified_user(
    client: TestClient,
    stub_instagram_scraper_service: StubInstagramReelScraperService,
) -> None:
    response = client.post(
        "/api/v1/instagram/reels/scrape",
        json={"url": "https://www.instagram.com/reel/abc123/"},
        headers={"Authorization": "Bearer access-token"},
    )

    assert response.status_code == 200
    assert stub_instagram_scraper_service.request_payload is not None
    assert (
        str(stub_instagram_scraper_service.request_payload.url)
        == "https://www.instagram.com/reel/abc123/"
    )
    assert response.json()["reel_id"] == "abc123"
    assert response.json()["title"] == "Example reel"


def test_scrape_reel_rejects_unverified_user(
    client: TestClient,
    stub_auth_service: StubSupabaseAuthService,
) -> None:
    async def unverified_current_user(_: str) -> UserResponse:
        return UserResponse(user=SupabaseUser(id="user-123", email="user@example.com"))

    stub_auth_service.get_current_user = unverified_current_user

    response = client.post(
        "/api/v1/instagram/reels/scrape",
        json={"url": "https://www.instagram.com/reel/abc123/"},
        headers={"Authorization": "Bearer access-token"},
    )

    assert response.status_code == 403
    assert response.json() == {
        "detail": "User must have a verified email or phone to access this resource."
    }


def test_scrape_tiktok_video_returns_metadata_for_verified_user(
    client: TestClient,
    stub_tiktok_scraper_service: StubTikTokVideoScraperService,
) -> None:
    response = client.post(
        "/api/v1/tiktok/videos/scrape",
        json={"url": "https://www.tiktok.com/@creator/video/9876543210"},
        headers={"Authorization": "Bearer access-token"},
    )

    assert response.status_code == 200
    assert stub_tiktok_scraper_service.request_payload is not None
    assert (
        str(stub_tiktok_scraper_service.request_payload.url)
        == "https://www.tiktok.com/@creator/video/9876543210"
    )
    assert response.json()["video_id"] == "9876543210"
    assert response.json()["title"] == "Example TikTok"


def test_scrape_youtube_short_returns_metadata_for_verified_user(
    client: TestClient,
    stub_youtube_scraper_service: StubYouTubeShortsScraperService,
) -> None:
    response = client.post(
        "/api/v1/youtube/shorts/scrape",
        json={"url": "https://www.youtube.com/shorts/xyz987"},
        headers={"Authorization": "Bearer access-token"},
    )

    assert response.status_code == 200
    assert stub_youtube_scraper_service.request_payload is not None
    assert (
        str(stub_youtube_scraper_service.request_payload.url)
        == "https://www.youtube.com/shorts/xyz987"
    )
    assert response.json()["short_id"] == "xyz987"
    assert response.json()["title"] == "Example Short"
