from __future__ import annotations

from typing import Any, Mapping, Protocol

from starlette.requests import Request
from starlette.responses import Response


class OAuthClient(Protocol):
    async def authorize_redirect(self, request: Request, **params: Any) -> Response:
        ...

    async def authorize_access_token(self, request: Request, **params: Any) -> Mapping[str, Any]:
        ...

    def parse_id_token(self, token: Mapping[str, Any], **params: Any) -> Any:
        ...

