from __future__ import annotations

from typing import Any, Dict

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse

from oauth_tester.settings import get_settings
from oauth_tester.oauth_client import oauth, register_oidc_client
from oauth_tester.security import (
    generate_state,
    generate_nonce,
    generate_code_verifier,
    code_challenge_s256,
    compute_appsecret_proof,
)
from oauth_tester.jwt_utils import verify_id_token


router = APIRouter(prefix="/auth", tags=["auth"])


def get_oauth_client():
    """Resolve or register the OAuth client and return it.

    This is idempotent and avoids relying on internal registry details.
    """
    s = get_settings()
    client = oauth.create_client(s.oauth.provider_name)
    if client is None:
        register_oidc_client()
        client = oauth.create_client(s.oauth.provider_name)
    if client is None:
        raise HTTPException(status_code=500, detail="OAuth client registration failed")
    return client


@router.get("/login")
async def login(request: Request, client = Depends(get_oauth_client)):
    s = get_settings()
    state = generate_state()
    # Only include nonce for OIDC flows
    include_nonce = bool(s.oauth.oidc_discovery_url or s.oauth.jwks_url)
    nonce = generate_nonce() if include_nonce else None
    code_verifier = None
    code_challenge = None
    if s.oauth.use_pkce:
        code_verifier = generate_code_verifier()
        code_challenge = code_challenge_s256(code_verifier)

    request.session.update(
        {
            "oauth_state": state,
            "oauth_nonce": nonce,
            "code_verifier": code_verifier,
        }
    )

    redirect_uri = f"{s.oauth.base_url}{s.oauth.redirect_path}"
    kwargs = dict(redirect_uri=redirect_uri, state=state)
    if nonce:
        kwargs["nonce"] = nonce
    if code_challenge:
        kwargs["code_challenge"] = code_challenge
        kwargs["code_challenge_method"] = "S256"
    return await client.authorize_redirect(request, **kwargs)


@router.get("/callback")
async def callback(request: Request, client = Depends(get_oauth_client)):
    s = get_settings()

    # Provider sign-in error
    if "error" in request.query_params:
        request.session["auth_error"] = {
            "error": request.query_params.get("error"),
            "error_reason": request.query_params.get("error_reason"),
            "error_description": request.query_params.get("error_description"),
        }
        return RedirectResponse(url="/")

    # Validate state
    state_param = request.query_params.get("state")
    if not state_param or state_param != request.session.get("oauth_state"):
        raise HTTPException(status_code=400, detail="Invalid state (check cookie SameSite/HTTPS)")

    token = await client.authorize_access_token(
        request,
        code_verifier=request.session.get("code_verifier") if s.oauth.use_pkce else None,
    )

    id_token = token.get("id_token")
    access_token = token.get("access_token")

    claims: Dict[str, Any] | None = None
    profile: Dict[str, Any] | None = None
    # Parse ID token only for OIDC flows
    is_oidc = bool(s.oauth.oidc_discovery_url or s.oauth.jwks_url)
    if is_oidc and id_token:
        try:
            maybe_claims = client.parse_id_token(token, nonce=request.session.get("oauth_nonce"))
            if hasattr(maybe_claims, "__await__"):
                claims = await maybe_claims  # type: ignore[func-returns-value]
            else:
                claims = maybe_claims  # type: ignore[assignment]
        except Exception:
            # Fallback to manual JWKS verification if configured
            if s.oauth.jwks_url:
                claims = await verify_id_token(
                    id_token,
                    jwks_url=s.oauth.jwks_url,
                    audience=s.oauth.client_id,
                )

    # Non-OIDC providers: try to fetch user profile if configured
    if not claims and access_token and s.oauth.userinfo_endpoint:
        import httpx

        params: Dict[str, Any] = {"access_token": access_token}
        if s.oauth.userinfo_fields:
            params["fields"] = s.oauth.userinfo_fields
        if s.oauth.compute_appsecret_proof and s.oauth.client_secret:
            params["appsecret_proof"] = compute_appsecret_proof(access_token, s.oauth.client_secret)
        try:
            async with httpx.AsyncClient(timeout=10) as client_http:
                resp = await client_http.get(str(s.oauth.userinfo_endpoint), params=params)
                if resp.status_code < 300:
                    profile = resp.json()
        except Exception:
            profile = None

    request.session.update(
        {
            "id_token": id_token,
            "access_token": access_token,
            "claims": dict(claims) if isinstance(claims, dict) else None,
            "profile": dict(profile) if profile else None,
        }
    )

    return RedirectResponse(url="/")


@router.post("/logout")
@router.get("/logout")
async def logout(request: Request):
    request.session.clear()
    return RedirectResponse(url="/")
