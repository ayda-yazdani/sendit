from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.config import Settings, get_settings
from app.services.supabase_auth import SupabaseAuthService

bearer_scheme = HTTPBearer(auto_error=False)


def get_supabase_auth_service(
    request: Request,
    settings: Settings = Depends(get_settings),
) -> SupabaseAuthService:
    return SupabaseAuthService(
        http_client=request.app.state.http_client,
        settings=settings,
    )


def get_access_token(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> str:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing bearer token.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return credentials.credentials
