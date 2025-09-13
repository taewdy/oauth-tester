from __future__ import annotations

import base64
import json
from typing import Any, Dict, Optional

import httpx
from authlib.jose import jwt, JsonWebKey


def b64url_decode(data: str) -> bytes:
    padding = '=' * (-len(data) % 4)
    return base64.urlsafe_b64decode(data + padding)


async def fetch_jwks(jwks_url: str) -> Dict[str, Any]:
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get(jwks_url)
        resp.raise_for_status()
        return resp.json()


def pick_jwk(jwks: Dict[str, Any], kid: str | None) -> Dict[str, Any] | None:
    keys = jwks.get("keys", [])
    if kid:
        for k in keys:
            if k.get("kid") == kid:
                return k
    return keys[0] if keys else None


async def verify_id_token(id_token: str, jwks_url: str, audience: str, issuer: Optional[str] = None) -> Dict[str, Any]:
    header_part, _, _ = id_token.split(".")
    header = json.loads(b64url_decode(header_part))
    kid = header.get("kid")

    jwks = await fetch_jwks(jwks_url)
    jwk_dict = pick_jwk(jwks, kid)
    if not jwk_dict:
        raise ValueError("No JWK found to verify token")

    key = JsonWebKey.import_key(jwk_dict)
    claims = jwt.decode(id_token, key)

    claims.validate()
    if issuer and claims.get("iss") != issuer:
        raise ValueError("Invalid issuer")
    aud = claims.get("aud")
    if isinstance(aud, list):
        if audience not in aud:
            raise ValueError("Invalid audience")
    elif aud != audience:
        raise ValueError("Invalid audience")

    return dict(claims)

