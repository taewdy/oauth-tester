import os
import secrets
import hashlib
import base64
import hmac


def generate_state() -> str:
    return secrets.token_urlsafe(32)


def generate_nonce() -> str:
    return secrets.token_urlsafe(32)


def _b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def generate_code_verifier() -> str:
    # 32 bytes -> 43 chars base64url; valid PKCE range is 43-128
    return _b64url(os.urandom(32))


def code_challenge_s256(verifier: str) -> str:
    digest = hashlib.sha256(verifier.encode("ascii")).digest()
    return _b64url(digest)


def compute_appsecret_proof(access_token: str, app_secret: str) -> str:
    """Compute Facebook-style appsecret_proof for Graph API requests.

    HMAC-SHA256 of the access token using the app secret, hex-encoded.
    """
    return hmac.new(app_secret.encode("utf-8"), msg=access_token.encode("utf-8"), digestmod=hashlib.sha256).hexdigest()
