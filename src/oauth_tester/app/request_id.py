from __future__ import annotations

import logging
import uuid
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response


class RequestIDMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, header_name: str = "X-Request-ID", logger_name: str = "oauth_tester"):
        super().__init__(app)
        self.header_name = header_name
        self.logger = logging.getLogger(logger_name)

    async def dispatch(self, request: Request, call_next) -> Response:
        request_id = request.headers.get(self.header_name, str(uuid.uuid4()))
        self.logger.info(
            "request",
            extra={
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
            },
        )
        response = await call_next(request)
        response.headers[self.header_name] = request_id
        return response

