from pathlib import Path

from fastapi import APIRouter
from fastapi.responses import FileResponse

router = APIRouter(tags=["tester"])

TESTER_HTML_PATH = Path(__file__).resolve().parents[2] / "static" / "tester" / "index.html"


@router.get("/", response_class=FileResponse)
async def tester_page() -> FileResponse:
    return FileResponse(TESTER_HTML_PATH)
