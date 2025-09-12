from authlib.integrations.starlette_client import OAuth
from typing import Optional

from oauth_tester.settings import get_settings


oauth = OAuth()


def register_oidc_client(name: Optional[str] = None) -> None:
    """Register an OIDC client with Authlib.

    Uses discovery when available; otherwise falls back to manual endpoints.
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

    oauth.register(
        name=provider,
        client_id=s.oauth.client_id,
        client_secret=s.oauth.client_secret,
        client_kwargs={
            "scope": s.oauth.scopes,
        },
        **metadata_args,
    )
