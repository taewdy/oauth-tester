from __future__ import annotations

from typing import Optional, Any, Dict

from authlib.integrations.starlette_client import OAuth

from oauth_tester.settings import get_settings
from oauth_tester.clients.types import OAuthClient


oauth = OAuth()


def register_client(name: Optional[str] = None) -> None:
    """Register an OAuth/OIDC client with Authlib.

    - If `OIDC_DISCOVERY_URL` is set, uses discovery to configure endpoints.
    - Otherwise, uses manual endpoints from settings (authorize/token/userinfo).
    - For non-OIDC providers (e.g., Threads), configures token auth as client_secret_post.
    """
    s = get_settings()
    provider = name or s.oauth.provider_name

    metadata_args = {}
    if s.oauth.oidc_discovery_url:
        metadata_args["server_metadata_url"] = s.oauth.oidc_discovery_url
    else:
        # Allow manual configuration when discovery is not supported
        metadata_args["api_base_url"] = str(s.oauth.base_url)
        if s.oauth.authorize_url:
            metadata_args["authorize_url"] = s.oauth.authorize_url
        if s.oauth.token_url:
            metadata_args["access_token_url"] = s.oauth.token_url
        if s.oauth.userinfo_endpoint:
            metadata_args["userinfo_endpoint"] = s.oauth.userinfo_endpoint

    client_kwargs: Dict[str, Any] = {
        "scope": s.oauth.scopes,
    }
    # For Threads/Meta and many non-OIDC providers, the token endpoint expects
    # client_id/client_secret in the POST body, not Basic auth.
    # Force client_secret_post when not using discovery or when provider is threads.
    if not s.oauth.oidc_discovery_url or s.oauth.provider_name.lower() == "threads":
        client_kwargs["token_endpoint_auth_method"] = "client_secret_post"

    oauth.register(
        name=provider,
        client_id=s.oauth.client_id,
        client_secret=s.oauth.client_secret,
        client_kwargs=client_kwargs,
        **metadata_args,
    )


def get_oauth_client(name: Optional[str] = None) -> OAuthClient:
    """Return a registered OAuth client, registering on-demand if missing.

    Intended for use as a FastAPI dependency.
    """
    s = get_settings()
    provider = name or s.oauth.provider_name
    client: Optional[OAuthClient] = oauth.create_client(provider)
    if client is None:
        register_client(provider)
        client = oauth.create_client(provider)
    if client is None:
        # Lazy import to avoid a top-level FastAPI dependency
        from fastapi import HTTPException

        raise HTTPException(status_code=500, detail="OAuth client registration failed")
    return client


# Backward-compat alias if referenced elsewhere
register_oidc_client = register_client
