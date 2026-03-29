from contextlib import asynccontextmanager
import logging

import httpx
from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError, ResponseValidationError
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api.router import api_router
from app.config import get_settings

settings = get_settings()
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.http_client = httpx.AsyncClient(
        timeout=settings.supabase_request_timeout_seconds
    )
    try:
        yield
    finally:
        await app.state.http_client.aclose()


app = FastAPI(
    title=settings.app_name,
    lifespan=lifespan,
)


@app.middleware("http")
async def ensure_http_client(request: Request, call_next):
    """Ensure http_client exists even when lifespan doesn't run (e.g. Vercel serverless)."""
    if not hasattr(request.app.state, "http_client") or request.app.state.http_client is None:
        request.app.state.http_client = httpx.AsyncClient(
            timeout=settings.supabase_request_timeout_seconds
        )
    return await call_next(request)

app.mount("/static", StaticFiles(directory="app/static"), name="static")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.backend_cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(RequestValidationError)
async def request_validation_exception_handler(
    _request: Request, exc: RequestValidationError
) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        content={
            "detail": "Invalid request payload.",
            "errors": jsonable_encoder(exc.errors()),
        },
    )


@app.exception_handler(ResponseValidationError)
async def response_validation_exception_handler(
    _request: Request, exc: ResponseValidationError
) -> JSONResponse:
    logger.exception("Response validation failed", exc_info=exc)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "Internal response validation failed."},
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(
    _request: Request, exc: Exception
) -> JSONResponse:
    logger.exception("Unhandled API exception", exc_info=exc)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "Internal server error."},
    )


@app.get("/health", tags=["health"])
async def health_check() -> dict[str, str]:
    return {"status": "ok"}


app.include_router(api_router, prefix=settings.api_v1_prefix)
