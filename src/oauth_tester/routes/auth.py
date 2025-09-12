from __future__ import annotations

import base64
import hashlib
from typing import Any, Dict

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse

from oauth_tester.settings import get_settings
from oauth_tester.oauth_client import oauth, register_oidc_client
from oauth_tester.security import generate_state, generate_nonce, generate_code_verifier, code_challenge_s256
from oauth_tester.jwt_utils import verify_id_token


router = APIRouter(prefix="/auth", tags=["auth"])


def b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def require_client():
    # Ensure client is registered (idempotent)
    s = get_settings()
    if s.oauth.provider_name not in oauth:
        register_oidc_client()


@router.get("/login")
async def login(request: Request, _: None = Depends(require_client)):
    s = get_settings()
    client = oauth.create_client(s.oauth.provider_name)
    state = generate_state()
    nonce = generate_nonce()
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
    return await client.authorize_redirect(
        request,
        redirect_uri=redirect_uri,
        state=state,
        nonce=nonce,
        code_challenge=code_challenge,
        code_challenge_method="S256",
    )


@router.get("/callback")
async def callback(request: Request, _: None = Depends(require_client)):
    s = get_settings()
    client = oauth.create_client(s.oauth.provider_name)

    # Validate state
    state_param = request.query_params.get("state")
    if not state_param or state_param != request.session.get("oauth_state"):
        raise HTTPException(status_code=400, detail="Invalid state")

    token = await client.authorize_access_token(
        request, code_verifier=request.session.get("code_verifier")
    )

    id_token = token.get("id_token")
    access_token = token.get("access_token")

    claims: Dict[str, Any] | None = None
    # Prefer provider-backed validation via discovery if available
    try:
        claims = client.parse_id_token(token, nonce=request.session.get("oauth_nonce"))
    except Exception:
        # Fallback to manual JWKS verification if configured
        if s.oauth.jwks_url:
            claims = await verify_id_token(
                id_token,
                jwks_url=s.oauth.jwks_url,
                audience=s.oauth.client_id,
            )

    request.session.update(
        {
            "id_token": id_token,
            "access_token": access_token,
            "claims": dict(claims) if claims else None,
        }
    )

    return RedirectResponse(url="/")


@router.post("/logout")
@router.get("/logout")
async def logout(request: Request):
    request.session.clear()
    return RedirectResponse(url="/")
