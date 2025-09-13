from __future__ import annotations

import httpx
from fastapi import FastAPI
from fastapi.responses import JSONResponse


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(httpx.HTTPError)
    async def httpx_error_handler(_, exc: httpx.HTTPError):
        return JSONResponse(status_code=502, content={"detail": f"External API error: {str(exc)}"})

    @app.exception_handler(Exception)
    async def unhandled_error_handler(_, __: Exception):
        return JSONResponse(status_code=500, content={"detail": "Internal server error"})

