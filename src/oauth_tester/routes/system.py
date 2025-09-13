from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates


router = APIRouter(tags=["system"])

# Resolve templates directory relative to package root
BASE_DIR = Path(__file__).resolve().parents[1]
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))


@router.get("/health")
async def health_check() -> dict:
    return {"status": "healthy", "service": "oauth-tester"}


@router.get("/", response_class=HTMLResponse)
async def index(request: Request):
    import json

    claims = request.session.get("claims")
    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "id_token": request.session.get("id_token"),
            "access_token": request.session.get("access_token"),
            "claims_json": json.dumps(claims, indent=2) if claims else None,
        },
    )

