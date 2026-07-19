"""Request-ID middleware for tracing and log correlation.

Every request receives a unique X-Request-ID header (either forwarded from an
upstream proxy or generated as a UUID4). The ID is:

- Bound to structlog context vars so every log line is automatically correlated
- Returned in the response headers for client-side debugging
- Accessible via ``request.state.request_id`` in route handlers and dependencies

Usage in a route handler::

    from app.utils.request_id import get_request_id

    @app.get("/example")
    async def example(request: Request):
        req_id = get_request_id(request)
        logger.info("something happened")  # automatically includes request_id
        return {"request_id": req_id}
"""

from __future__ import annotations

import uuid

import structlog
import structlog.contextvars
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint

REQUEST_ID_HEADER = "X-Request-ID"


class RequestIDMiddleware(BaseHTTPMiddleware):
    """Middleware that attaches a unique request ID to every request.

    The ID is:
    - Taken from the incoming X-Request-ID header (if present, for proxy
      chaining)
    - Generated as a UUID4 (if absent)
    - Added to the response headers
    - Bound to structlog context vars for automatic log correlation
    """

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        req_id = request.headers.get(REQUEST_ID_HEADER) or str(uuid.uuid4())
        request.state.request_id = req_id
        structlog.contextvars.bind_contextvars(request_id=req_id)
        try:
            response = await call_next(request)
            response.headers[REQUEST_ID_HEADER] = req_id
            return response
        finally:
            structlog.contextvars.unbind_contextvars("request_id")


def get_request_id(request: Request) -> str:
    """Retrieve the current request ID from request state."""
    return getattr(request.state, "request_id", "")
