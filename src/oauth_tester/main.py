"""
Main entry point for the OAuth Tester application.
"""
from dotenv import load_dotenv
import uvicorn
from oauth_tester.app import create_app
from oauth_tester.settings import get_settings

# Load environment variables from a .env file if present
load_dotenv()

# Create the FastAPI application
app = create_app()


def main() -> None:
    """Main entry point for running the application."""
    s = get_settings()
    ssl_kwargs = {}
    if s.oauth.ssl_certfile and s.oauth.ssl_keyfile:
        ssl_kwargs = {"ssl_certfile": s.oauth.ssl_certfile, "ssl_keyfile": s.oauth.ssl_keyfile}
        print(
            f"[oauth-tester] TLS enabled: cert={s.oauth.ssl_certfile} key={s.oauth.ssl_keyfile} base_url={s.oauth.base_url}"
        )
    else:
        print("[oauth-tester] TLS DISABLED: serving HTTP. Set OAUTH_TESTER_OAUTH__SSL_CERTFILE and __SSL_KEYFILE.")

    uvicorn.run(
        "oauth_tester.main:app",
        host=s.server.host,
        port=s.server.port,
        reload=s.server.reload,
        log_level=s.server.log_level,
        **ssl_kwargs,
    )


if __name__ == "__main__":
    main()
