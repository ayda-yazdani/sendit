from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

router = APIRouter(tags=["tester"])

TESTER_HTML_PATH = (
    Path(__file__).resolve().parents[2] / "static" / "tester" / "dist" / "index.html"
)


@router.get("/", response_class=FileResponse)
async def tester_page() -> FileResponse:
    if not TESTER_HTML_PATH.exists():
        raise HTTPException(
            status_code=503,
            detail=(
                "Tester frontend build is missing. Run "
                "`cd backend/tester-app && npm install && npm run build`."
            ),
        )
    return FileResponse(TESTER_HTML_PATH)
