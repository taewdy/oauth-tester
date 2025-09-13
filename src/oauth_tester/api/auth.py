from __future__ import annotations

from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse

from oauth_tester.settings import get_settings
from oauth_tester.clients.oauth import oauth, get_oauth_client
from oauth_tester.app.security import (
    generate_state,
    generate_nonce,
    generate_code_verifier,
    code_challenge_s256,
    compute_appsecret_proof,
)
from oauth_tester.app.jwt import verify_id_token
from authlib.integrations.base_client.errors import OAuthError


router = APIRouter(prefix="/auth", tags=["auth"])

# Session keys
STATE_KEY = "oauth_state"
NONCE_KEY = "oauth_nonce"
VERIFIER_KEY = "code_verifier"


def _redirect_uri() -> str:
    s = get_settings()
    return f"{s.oauth.base_url}{s.oauth.redirect_path}"


def _build_authorize_kwargs(s, state: str) -> tuple[Dict[str, Any], Optional[str]]:
    """Build parameters for authorize_redirect and return (kwargs, code_verifier)."""
    kwargs: Dict[str, Any] = {"redirect_uri": _redirect_uri(), "state": state}

    # OIDC-only nonce
    include_nonce = bool(s.oauth.oidc_discovery_url or s.oauth.jwks_url)
    if include_nonce:
        kwargs["nonce"] = generate_nonce()

    code_verifier: Optional[str] = None
    if s.oauth.use_pkce:
        code_verifier = generate_code_verifier()
        kwargs["code_challenge"] = code_challenge_s256(code_verifier)
        kwargs["code_challenge_method"] = "S256"

    return kwargs, code_verifier


@router.get("/login")
async def login(request: Request, client = Depends(get_oauth_client)):
    s = get_settings()
    state = generate_state()
    kwargs, code_verifier = _build_authorize_kwargs(s, state)

    # Persist minimal state needed for callback validation
    request.session[STATE_KEY] = state
    if "nonce" in kwargs:
        request.session[NONCE_KEY] = kwargs["nonce"]
    if code_verifier:
        request.session[VERIFIER_KEY] = code_verifier

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
    if not state_param or state_param != request.session.get(STATE_KEY):
        raise HTTPException(status_code=400, detail="Invalid state (check cookie SameSite/HTTPS)")

    try:
        token = await client.authorize_access_token(
            request,
            code_verifier=request.session.get(VERIFIER_KEY) if s.oauth.use_pkce else None,
        )
    except OAuthError as e:
        # Surface token exchange errors nicely on the UI
        request.session["auth_error"] = {
            "error": getattr(e, "error", None) or "oauth_error",
            "error_description": getattr(e, "description", None) or str(e),
        }
        return RedirectResponse(url="/")

    id_token = token.get("id_token")
    access_token = token.get("access_token")

    claims: Dict[str, Any] | None = None
    profile: Dict[str, Any] | None = None
    # Parse ID token only for OIDC flows
    is_oidc = bool(s.oauth.oidc_discovery_url or s.oauth.jwks_url)
    if is_oidc and id_token:
        try:
            maybe_claims = client.parse_id_token(token, nonce=request.session.get(NONCE_KEY))
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

    # Rotate transient values and persist results
    for k in (STATE_KEY, NONCE_KEY, VERIFIER_KEY):
        if k in request.session:
            request.session.pop(k)

    if id_token:
        request.session["id_token"] = id_token
    if access_token:
        request.session["access_token"] = access_token
    if isinstance(claims, dict):
        request.session["claims"] = claims
    if profile:
        request.session["profile"] = profile

    return RedirectResponse(url="/")


@router.post("/logout")
@router.get("/logout")
async def logout(request: Request):
    request.session.clear()
    return RedirectResponse(url="/")
