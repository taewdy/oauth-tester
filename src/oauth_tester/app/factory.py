from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware

from oauth_tester.settings import get_settings
from oauth_tester.routes import auth_router, system_router
from oauth_tester.middleware.request_id import RequestIDMiddleware
from oauth_tester.app.exceptions import register_exception_handlers
from oauth_tester.app.logging_config import configure_logging
from oauth_tester.app.metrics import instrument_metrics
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parents[2]


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
    
    # CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors.origins(),
        allow_credentials=True,
        allow_methods=settings.cors.methods(),
        allow_headers=settings.cors.headers(),
    )

    # Sessions
    app.add_middleware(
        SessionMiddleware,
        secret_key=settings.oauth.secret_key,
        session_cookie=settings.oauth.session_cookie_name,
        same_site="none",
        https_only=True,
    )

    # Static
    static_dir = BASE_DIR / "oauth_tester" / "static"
    if static_dir.exists():
        app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

    # Routers
    app.include_router(system_router)
    app.include_router(auth_router)

    # Middleware
    app.add_middleware(RequestIDMiddleware)

    # Exceptions, logging, metrics
    register_exception_handlers(app)
    configure_logging(settings.logging.as_json, settings.server.log_level)
    instrument_metrics(app)

    return app
