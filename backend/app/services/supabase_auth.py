from typing import Any

import httpx
from fastapi import HTTPException, status

from app.config import Settings
from app.schemas.auth import (
    AuthResponse,
    RefreshSessionRequest,
    SignInRequest,
    SignUpRequest,
    SupabaseConfigCheckResponse,
    SupabaseSession,
    SupabaseUser,
    UserResponse,
)

SESSION_KEYS = {
    "access_token",
    "expires_at",
    "expires_in",
    "provider_refresh_token",
    "provider_token",
    "refresh_token",
    "token_type",
    "weak_password",
}

USER_KEYS = {
    "app_metadata",
    "aud",
    "banned_until",
    "confirmation_sent_at",
    "confirmed_at",
    "created_at",
    "email",
    "email_change_sent_at",
    "email_confirmed_at",
    "id",
    "identities",
    "invited_at",
    "is_anonymous",
    "last_sign_in_at",
    "new_email",
    "new_phone",
    "phone",
    "phone_change_sent_at",
    "phone_confirmed_at",
    "reauthentication_sent_at",
    "recovery_sent_at",
    "role",
    "updated_at",
    "user_metadata",
}


class SupabaseAuthService:
    def __init__(self, http_client: httpx.AsyncClient, settings: Settings) -> None:
        self._http_client = http_client
        self._settings = settings

    async def sign_up(self, payload: SignUpRequest) -> AuthResponse:
        request_body: dict[str, Any] = {
            "email": payload.email,
            "password": payload.password,
        }

        if payload.metadata:
            request_body["data"] = payload.metadata

        response_data = await self._request(
            method="POST",
            path="/signup",
            json=request_body,
            authenticated=False,
        )
        return self._normalize_auth_payload(response_data)

    async def sign_in(self, payload: SignInRequest) -> AuthResponse:
        response_data = await self._request(
            method="POST",
            path="/token",
            params={"grant_type": "password"},
            json={
                "email": payload.email,
                "password": payload.password,
            },
            authenticated=False,
        )
        return self._normalize_auth_payload(response_data)

    async def refresh_session(self, payload: RefreshSessionRequest) -> AuthResponse:
        response_data = await self._request(
            method="POST",
            path="/token",
            params={"grant_type": "refresh_token"},
            json={"refresh_token": payload.refresh_token},
            authenticated=False,
        )
        return self._normalize_auth_payload(response_data)

    async def get_current_user(self, access_token: str) -> UserResponse:
        response_data = await self._request(
            method="GET",
            path="/user",
            access_token=access_token,
        )
        return UserResponse(user=SupabaseUser.model_validate(response_data))

    async def sign_out(self, access_token: str) -> None:
        await self._request(
            method="POST",
            path="/logout",
            access_token=access_token,
            expected_status_codes={status.HTTP_204_NO_CONTENT},
        )

    async def check_configuration(self) -> SupabaseConfigCheckResponse:
        response_data = await self._request(
            method="GET",
            path="/settings",
            authenticated=False,
        )
        external_settings = response_data.get("external")
        external = (
            {
                str(provider): bool(enabled)
                for provider, enabled in external_settings.items()
            }
            if isinstance(external_settings, dict)
            else {}
        )
        disable_signup = response_data.get("disable_signup")

        return SupabaseConfigCheckResponse(
            supabase_url=self._settings.supabase_url,
            auth_url=self._settings.supabase_auth_url,
            key_present=bool(self._settings.supabase_key),
            disable_signup=(
                disable_signup if isinstance(disable_signup, bool) else None
            ),
            external=external,
            message="Supabase Auth is reachable with the configured publishable key.",
        )

    async def _request(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        json: dict[str, Any] | None = None,
        access_token: str | None = None,
        authenticated: bool = True,
        expected_status_codes: set[int] | None = None,
    ) -> dict[str, Any]:
        headers = self._build_headers(
            access_token=access_token if authenticated else None
        )

        try:
            response = await self._http_client.request(
                method=method,
                url=f"{self._settings.supabase_auth_url}{path}",
                params=params,
                json=json,
                headers=headers,
            )
        except httpx.TimeoutException as exc:
            raise HTTPException(
                status_code=status.HTTP_504_GATEWAY_TIMEOUT,
                detail="Timed out while reaching Supabase Auth.",
            ) from exc
        except httpx.HTTPError as exc:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Could not reach Supabase Auth.",
            ) from exc

        valid_codes = expected_status_codes or {status.HTTP_200_OK}
        if response.status_code not in valid_codes:
            raise self._map_error(response)

        if response.status_code == status.HTTP_204_NO_CONTENT:
            return {}

        return response.json()

    def _build_headers(self, access_token: str | None = None) -> dict[str, str]:
        authorization_token = access_token or self._settings.supabase_key
        return {
            "apikey": self._settings.supabase_key,
            "Authorization": f"Bearer {authorization_token}",
            "Content-Type": "application/json",
        }

    def _map_error(self, response: httpx.Response) -> HTTPException:
        detail = "Supabase Auth request failed."

        try:
            payload = response.json()
        except ValueError:
            payload = {}

        if isinstance(payload, dict):
            detail = (
                payload.get("msg")
                or payload.get("message")
                or payload.get("error_description")
                or payload.get("error")
                or detail
            )
        elif response.text:
            detail = response.text

        return HTTPException(status_code=response.status_code, detail=detail)

    def _normalize_auth_payload(self, payload: dict[str, Any]) -> AuthResponse:
        session_payload = payload.get("session")
        if not session_payload:
            session_payload = {
                key: value
                for key, value in payload.items()
                if key in SESSION_KEYS and value is not None
            }
            if not session_payload:
                session_payload = None

        user_payload = payload.get("user")
        if user_payload is None:
            user_payload = {
                key: value
                for key, value in payload.items()
                if key in USER_KEYS and value is not None
            }
            if not user_payload:
                user_payload = None

        return AuthResponse(
            user=(
                SupabaseUser.model_validate(user_payload)
                if isinstance(user_payload, dict)
                else None
            ),
            session=(
                SupabaseSession.model_validate(session_payload)
                if isinstance(session_payload, dict)
                else None
            ),
            message=payload.get("message"),
        )
