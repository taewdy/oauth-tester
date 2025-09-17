from __future__ import annotations

from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse

from oauth_tester.settings import get_settings
from oauth_tester.clients import get_oauth_client
from oauth_tester.clients.oauth import OAuthClientError
from oauth_tester.clients.types import OAuthClient
from oauth_tester.app.security import (
    generate_state,
    generate_nonce,
    generate_code_verifier,
    code_challenge_s256,
    compute_appsecret_proof,
)
from oauth_tester.app.jwt import verify_id_token
from oauth_tester.clients.threads_tokens import ThreadsTokenService, ThreadsTokenError


router = APIRouter(prefix="/auth", tags=["auth"])

# Session keys
STATE_KEY = "oauth_state"
NONCE_KEY = "oauth_nonce"
VERIFIER_KEY = "code_verifier"


def _redirect_uri() -> str:
    s = get_settings()
    return f"{s.oauth.base_url}{s.oauth.redirect_path}"


def _build_authorize_kwargs(s, state: str) -> tuple[Dict[str, Any], Optional[str]]:
    """Build authorization parameters and return (params, code_verifier)."""
    kwargs: Dict[str, Any] = {
        "redirect_uri": _redirect_uri(),
        "state": state,
        "scope": s.oauth.scopes,
    }

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
async def login(request: Request, client: OAuthClient = Depends(get_oauth_client)):
    s = get_settings()
    state = generate_state()
    kwargs, code_verifier = _build_authorize_kwargs(s, state)

    # Persist minimal state needed for callback validation
    request.session[STATE_KEY] = state
    if "nonce" in kwargs:
        request.session[NONCE_KEY] = kwargs["nonce"]
    if code_verifier:
        request.session[VERIFIER_KEY] = code_verifier

    authorize_url = await client.build_authorization_url(
        redirect_uri=kwargs["redirect_uri"],
        state=kwargs["state"],
        scope=kwargs["scope"],
        nonce=kwargs.get("nonce"),
        code_challenge=kwargs.get("code_challenge"),
        code_challenge_method=kwargs.get("code_challenge_method"),
    )
    return RedirectResponse(url=authorize_url)


@router.get("/callback")
async def callback(request: Request, client: OAuthClient = Depends(get_oauth_client)):
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

    code_param = request.query_params.get("code")
    if not code_param:
        raise HTTPException(status_code=400, detail="Missing authorization code")

    try:
        token = await client.exchange_code(
            code=code_param,
            redirect_uri=_redirect_uri(),
            code_verifier=request.session.get(VERIFIER_KEY) if s.oauth.use_pkce else None,
        )
    except OAuthClientError as e:
        # Surface token exchange errors nicely on the UI
        error_payload: Dict[str, Any] = {
            "error": e.error or "oauth_error",
            "error_description": e.description or str(e),
            "status_code": e.status_code,
        }
        if e.details:
            error_payload["details"] = e.details
        request.session["auth_error"] = error_payload
        return RedirectResponse(url="/")

    id_token = token.get("id_token")
    access_token = token.get("access_token")

    claims: Dict[str, Any] | None = None
    profile: Dict[str, Any] | None = None
    # Parse ID token only for OIDC flows
    is_oidc = bool(s.oauth.oidc_discovery_url or s.oauth.jwks_url)
    if is_oidc and id_token:
        try:
            claims = await client.parse_id_token(
                token_response=token,
                nonce=request.session.get(NONCE_KEY),
            )
        except OAuthClientError:
            jwks_url = await client.jwks_uri()
            if jwks_url:
                claims = await verify_id_token(
                    id_token,
                    jwks_url=jwks_url,
                    audience=s.oauth.client_id,
                    issuer=await client.issuer(),
                )

    # Non-OIDC providers: try to fetch user profile if configured
    userinfo_endpoint = await client.userinfo_endpoint()
    if not claims and access_token and userinfo_endpoint:
        import httpx

        params: Dict[str, Any] = {"access_token": access_token}
        if s.oauth.userinfo_fields:
            params["fields"] = s.oauth.userinfo_fields
        if s.oauth.compute_appsecret_proof and s.oauth.client_secret:
            params["appsecret_proof"] = compute_appsecret_proof(access_token, s.oauth.client_secret)
        try:
            async with httpx.AsyncClient(timeout=10) as client_http:
                resp = await client_http.get(str(userinfo_endpoint), params=params)
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

    # Optionally auto-exchange for a long-lived token for Threads provider
    if s.oauth.provider_name.lower() == "threads" and s.oauth.auto_exchange_long_lived and access_token:
        try:
            service = ThreadsTokenService()
            long = await service.exchange_long_lived(access_token)
            request.session["long_access_token"] = long.access_token
            request.session["long_token_type"] = long.token_type
            request.session["long_expires_in"] = long.expires_in
        except ThreadsTokenError as e:
            # Do not fail the flow; store error to display
            request.session["auth_error"] = {
                "error": "long_token_exchange_failed",
                "error_description": str(e),
                "status_code": getattr(e, "status_code", None),
            }

    return RedirectResponse(url="/")


@router.post("/logout")
@router.get("/logout")
async def logout(request: Request):
    request.session.clear()
    return RedirectResponse(url="/")


@router.post("/long-token/exchange")
async def exchange_long_token(request: Request):
    s = get_settings()
    if s.oauth.provider_name.lower() != "threads":
        raise HTTPException(status_code=400, detail="Long-lived exchange only supported for Threads")
    access_token = request.session.get("access_token")
    if not access_token:
        raise HTTPException(status_code=400, detail="No short-lived access token in session")
    try:
        service = ThreadsTokenService()
        long = await service.exchange_long_lived(access_token)
        request.session["long_access_token"] = long.access_token
        request.session["long_token_type"] = long.token_type
        request.session["long_expires_in"] = long.expires_in
        # Clear any previous error
        request.session.pop("auth_error", None)
    except ThreadsTokenError as e:
        request.session["auth_error"] = {
            "error": "long_token_exchange_failed",
            "error_description": str(e),
            "status_code": getattr(e, "status_code", None),
        }
    return RedirectResponse(url="/")


@router.post("/long-token/refresh")
async def refresh_long_token(request: Request):
    s = get_settings()
    if s.oauth.provider_name.lower() != "threads":
        raise HTTPException(status_code=400, detail="Long-lived refresh only supported for Threads")
    long_token = request.session.get("long_access_token")
    if not long_token:
        raise HTTPException(status_code=400, detail="No long-lived token in session")
    try:
        service = ThreadsTokenService()
        refreshed = await service.refresh_long_lived(long_token)
        request.session["long_access_token"] = refreshed.access_token
        request.session["long_token_type"] = refreshed.token_type
        request.session["long_expires_in"] = refreshed.expires_in
        request.session.pop("auth_error", None)
    except ThreadsTokenError as e:
        request.session["auth_error"] = {
            "error": "long_token_refresh_failed",
            "error_description": str(e),
            "status_code": getattr(e, "status_code", None),
        }
    return RedirectResponse(url="/")
