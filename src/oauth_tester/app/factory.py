from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from starlette.middleware.sessions import SessionMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from oauth_tester.settings import get_settings
from oauth_tester.routes import auth_router
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parents[2]
templates = Jinja2Templates(directory=str(BASE_DIR / "oauth_tester" / "templates"))


def create_app() -> FastAPI:
    """
    Create and configure the FastAPI application.
    
    Returns:
        Configured FastAPI application instance
    """
    settings = get_settings()

    app = FastAPI(
        title=settings.app_name,
        description="Local HTTPS OAuth/OIDC tester",
        version=settings.app_version,
        docs_url="/docs",
        redoc_url="/redoc",
        debug=settings.server.debug,
    )
    
    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors.origins(),
        allow_credentials=True,
        allow_methods=settings.cors.methods(),
        allow_headers=settings.cors.headers(),
    )

    app.add_middleware(
        SessionMiddleware,
        secret_key=settings.oauth.secret_key,
        session_cookie=settings.oauth.session_cookie_name,
        same_site="lax",
        https_only=True,
    )

    static_dir = BASE_DIR / "oauth_tester" / "static"
    if static_dir.exists():
        app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

    # Include OAuth routes
    app.include_router(auth_router)
    
    # Health check endpoint
    @app.get("/health")
    async def health_check() -> dict:
        """Health check endpoint."""
        return {"status": "healthy", "service": "oauth-tester"}
    
    # Root endpoint
    @app.get("/", response_class=HTMLResponse)
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

    # Exception handlers (centralized)
    import httpx
    from fastapi.responses import JSONResponse

    @app.exception_handler(httpx.HTTPError)
    async def httpx_error_handler(_, exc: httpx.HTTPError):
        return JSONResponse(status_code=502, content={"detail": f"External API error: {str(exc)}"})

    @app.exception_handler(Exception)
    async def unhandled_error_handler(_, exc: Exception):
        return JSONResponse(status_code=500, content={"detail": "Internal server error"})

    # Request ID middleware and simple request logging
    import uuid
    import logging
    from starlette.middleware.base import BaseHTTPMiddleware
    from starlette.requests import Request
    from starlette.responses import Response

    logger = logging.getLogger("oauth_tester")

    class RequestIDMiddleware(BaseHTTPMiddleware):
        def __init__(self, app, header_name: str = "X-Request-ID"):
            super().__init__(app)
            self.header_name = header_name

        async def dispatch(self, request: Request, call_next) -> Response:
            request_id = request.headers.get(self.header_name, str(uuid.uuid4()))
            logger.info(
                "request",
                extra={
                    "request_id": request_id,
                    "method": request.method,
                    "path": request.url.path,
                },
            )
            response = await call_next(request)
            response.headers[self.header_name] = request_id
            return response

    app.add_middleware(RequestIDMiddleware)

    # Configure logging format (JSON optional)
    try:
        import json
        import sys

        root_logger = logging.getLogger()
        # Avoid duplicating handlers on reload
        if not root_logger.handlers:
            handler = logging.StreamHandler(sys.stdout)

            if settings.logging.as_json:
                class JsonFormatter(logging.Formatter):
                    def format(self, record: logging.LogRecord) -> str:
                        payload = {
                            "level": record.levelname.lower(),
                            "logger": record.name,
                            "message": record.getMessage(),
                            "time": self.formatTime(record, self.datefmt),
                        }
                        for key in ("request_id", "method", "path"):
                            if hasattr(record, key):
                                payload[key] = getattr(record, key)
                        return json.dumps(payload)

                handler.setFormatter(JsonFormatter())
            else:
                handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))

            root_logger.addHandler(handler)
            root_logger.setLevel(getattr(logging, settings.server.log_level.upper(), logging.INFO))
    except Exception:
        # If logging configuration fails, continue with defaults
        pass

    # Metrics instrumentation
    try:
        from prometheus_fastapi_instrumentator import Instrumentator

        Instrumentator().instrument(app).expose(app, endpoint="/metrics")
    except Exception:
        # Metrics optional; ignore if dependency missing in certain environments
        pass

    return app
