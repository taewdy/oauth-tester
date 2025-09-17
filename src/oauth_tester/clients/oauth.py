from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Any, Dict, Mapping, Optional
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

import httpx

from oauth_tester.app.jwt import verify_id_token
from oauth_tester.settings import Settings, get_settings


@dataclass(frozen=True)
class ProviderMetadata:
    authorization_endpoint: str
    token_endpoint: str
    userinfo_endpoint: str | None = None
    jwks_uri: str | None = None
    issuer: str | None = None
    token_endpoint_auth_methods: tuple[str, ...] = ()


class OAuthClientError(Exception):
    def __init__(
        self,
        message: str,
        *,
        error: str | None = None,
        description: str | None = None,
        status_code: int | None = None,
        details: Mapping[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.error = error
        self.description = description
        self.status_code = status_code
        self.details = dict(details or {})


class OAuthConfigurationError(OAuthClientError):
    """Raised when provider configuration is incomplete."""


class OAuthTokenError(OAuthClientError):
    """Raised when the token endpoint returns an error."""


class HttpOAuthClient:
    """Manual OAuth 2.0 client that uses httpx for provider interactions."""

    def __init__(self, settings: Optional[Settings] = None, *, timeout: float = 10.0) -> None:
        self._settings = settings or get_settings()
        self._timeout = timeout
        self._metadata: ProviderMetadata | None = None
        self._metadata_lock = asyncio.Lock()

    async def build_authorization_url(
        self,
        *,
        redirect_uri: str,
        state: str,
        scope: str,
        nonce: str | None = None,
        code_challenge: str | None = None,
        code_challenge_method: str | None = None,
        extra_params: Mapping[str, Any] | None = None,
    ) -> str:
        metadata = await self._ensure_metadata()
        params: Dict[str, Any] = {
            "response_type": "code",
            "client_id": self._settings.oauth.client_id,
            "redirect_uri": redirect_uri,
            "scope": scope,
            "state": state,
        }
        if nonce:
            params["nonce"] = nonce
        if code_challenge:
            params["code_challenge"] = code_challenge
        if code_challenge_method:
            params["code_challenge_method"] = code_challenge_method
        if extra_params:
            params.update(extra_params)
        return _append_query(metadata.authorization_endpoint, params)

    async def exchange_code(
        self,
        *,
        code: str,
        redirect_uri: str,
        code_verifier: str | None = None,
    ) -> Dict[str, Any]:
        metadata = await self._ensure_metadata()
        data: Dict[str, Any] = {
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": redirect_uri,
            "client_id": self._settings.oauth.client_id,
        }
        if code_verifier:
            data["code_verifier"] = code_verifier

        use_basic = self._should_use_client_secret_basic(metadata)
        auth: httpx.Auth | tuple[str, str] | None = None
        if use_basic and self._settings.oauth.client_secret:
            auth = (self._settings.oauth.client_id, self._settings.oauth.client_secret)
        elif self._settings.oauth.client_secret:
            data["client_secret"] = self._settings.oauth.client_secret

        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                resp = await client.post(
                    metadata.token_endpoint,
                    data=data,
                    headers={"Accept": "application/json"},
                    auth=auth,
                )
        except httpx.HTTPError as exc:
            raise OAuthTokenError(
                "Network error during token exchange",
                error="network_error",
                description=str(exc),
            ) from exc

        if resp.status_code >= 400:
            payload = _safe_json(resp)
            raise OAuthTokenError(
                "Token exchange failed",
                error=_error_code(payload),
                description=_error_description(payload, resp.text),
                status_code=resp.status_code,
                details=payload,
            )

        return _safe_json(resp)

    async def parse_id_token(
        self,
        *,
        token_response: Mapping[str, Any],
        nonce: str | None = None,
    ) -> Dict[str, Any]:
        id_token = token_response.get("id_token")
        if not isinstance(id_token, str) or not id_token:
            raise OAuthClientError("Token response did not include an id_token", error="invalid_token")

        metadata = await self._ensure_metadata()
        jwks_url = self._settings.oauth.jwks_url or metadata.jwks_uri
        if not jwks_url:
            raise OAuthClientError("No JWKS endpoint configured for ID token verification", error="jwks_unavailable")

        claims = await verify_id_token(
            id_token,
            jwks_url=jwks_url,
            audience=self._settings.oauth.client_id,
            issuer=metadata.issuer,
        )
        if nonce and claims.get("nonce") != nonce:
            raise OAuthClientError("Nonce mismatch detected", error="invalid_nonce")
        return claims

    async def userinfo_endpoint(self) -> str | None:
        metadata = await self._ensure_metadata()
        return self._settings.oauth.userinfo_endpoint or metadata.userinfo_endpoint

    async def jwks_uri(self) -> str | None:
        metadata = await self._ensure_metadata()
        return self._settings.oauth.jwks_url or metadata.jwks_uri

    async def issuer(self) -> str | None:
        metadata = await self._ensure_metadata()
        return metadata.issuer

    async def _ensure_metadata(self) -> ProviderMetadata:
        if self._metadata:
            return self._metadata
        async with self._metadata_lock:
            if self._metadata:
                return self._metadata
            self._metadata = await self._load_metadata()
        return self._metadata

    async def _load_metadata(self) -> ProviderMetadata:
        if self._settings.oauth.oidc_discovery_url:
            return await self._load_from_discovery()
        return self._load_from_settings()

    async def _load_from_discovery(self) -> ProviderMetadata:
        discovery_url = self._settings.oauth.oidc_discovery_url
        if not discovery_url:
            raise OAuthConfigurationError("Discovery URL is not configured")
        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                resp = await client.get(discovery_url)
                resp.raise_for_status()
        except httpx.HTTPError as exc:
            raise OAuthConfigurationError(
                "Failed to load provider metadata",
                error="discovery_error",
                description=str(exc),
            ) from exc

        data = resp.json()
        authorize_endpoint = data.get("authorization_endpoint")
        token_endpoint = data.get("token_endpoint")
        if not authorize_endpoint or not token_endpoint:
            raise OAuthConfigurationError("Discovery document missing required endpoints")

        return ProviderMetadata(
            authorization_endpoint=authorize_endpoint,
            token_endpoint=token_endpoint,
            userinfo_endpoint=self._settings.oauth.userinfo_endpoint or data.get("userinfo_endpoint"),
            jwks_uri=self._settings.oauth.jwks_url or data.get("jwks_uri"),
            issuer=data.get("issuer"),
            token_endpoint_auth_methods=tuple(data.get("token_endpoint_auth_methods_supported", [])),
        )

    def _load_from_settings(self) -> ProviderMetadata:
        authorize_endpoint = self._settings.oauth.authorize_url
        token_endpoint = self._settings.oauth.token_url
        if not authorize_endpoint or not token_endpoint:
            raise OAuthConfigurationError(
                "Manual OAuth configuration requires authorize_url and token_url",
                error="configuration_error",
            )
        return ProviderMetadata(
            authorization_endpoint=authorize_endpoint,
            token_endpoint=token_endpoint,
            userinfo_endpoint=self._settings.oauth.userinfo_endpoint,
            jwks_uri=self._settings.oauth.jwks_url,
            issuer=None,
            token_endpoint_auth_methods=("client_secret_post",),
        )

    def _should_use_client_secret_basic(self, metadata: ProviderMetadata) -> bool:
        if self._settings.oauth.provider_name.lower() == "threads":
            return False
        if not self._settings.oauth.oidc_discovery_url:
            return False
        methods = set(metadata.token_endpoint_auth_methods)
        if methods:
            if "client_secret_basic" in methods:
                return True
            if "client_secret_post" in methods:
                return False
        return True


def get_oauth_client() -> HttpOAuthClient:
    return HttpOAuthClient()


def _append_query(url: str, params: Mapping[str, Any]) -> str:
    parsed = urlparse(url)
    query_params = parse_qsl(parsed.query, keep_blank_values=True)
    query_params.extend((str(k), str(v)) for k, v in params.items() if v is not None)
    new_query = urlencode(query_params, doseq=True)
    return urlunparse(parsed._replace(query=new_query))


def _safe_json(resp: httpx.Response) -> Dict[str, Any]:
    try:
        return resp.json()
    except ValueError:
        return {"raw": resp.text}


def _error_code(payload: Mapping[str, Any]) -> str | None:
    for key in ("error", "error_code", "code"):
        value = payload.get(key)
        if isinstance(value, str):
            return value
    return None


def _error_description(payload: Mapping[str, Any], default: str) -> str:
    for key in ("error_description", "errorReason", "message", "error_message"):
        value = payload.get(key)
        if isinstance(value, str) and value.strip():
            return value
    return default
