from __future__ import annotations

from typing import Any, Dict, Mapping, Protocol


class OAuthClient(Protocol):
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
        ...

    async def exchange_code(
        self,
        *,
        code: str,
        redirect_uri: str,
        code_verifier: str | None = None,
    ) -> Mapping[str, Any]:
        ...

    async def parse_id_token(
        self,
        *,
        token_response: Mapping[str, Any],
        nonce: str | None = None,
    ) -> Dict[str, Any]:
        ...

    async def userinfo_endpoint(self) -> str | None:
        ...

    async def jwks_uri(self) -> str | None:
        ...

    async def issuer(self) -> str | None:
        ...

