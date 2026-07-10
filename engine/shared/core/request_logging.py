"""
Request-scoped logging middleware.

For every incoming HTTP request this middleware:
1. Generates a short unique ``request_id``.
2. Reads method, path, query-params and (for mutating verbs) the request body.
3. Masks sensitive fields (password, secret, token …) in the logged body.
4. Binds all of the above into the shared ContextVar so that every log line
   emitted during the request automatically carries the ``request_id``.
5. Emits a ``request.start`` event at the beginning and a ``request.end``
   event (with ``status_code`` and ``duration_ms``) at the end.

All of these entries land in ``request_trace.json.log`` because the logger
sink filters on ``request_id is not None``.
"""

import time
import uuid
from typing import Any

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

from shared.logging import get_logger

_SENSITIVE_KEYS = frozenset({
    "password", "client_secret", "secret", "token",
    "refresh_token", "access_token", "api_key",
    "service_token", "code_verifier",
})

# Maximum body size we are willing to read and log (2 KB).
_MAX_BODY_LOG_BYTES = 2048

# Content types that we should NOT try to log (file uploads, images, etc.)
_SKIP_CONTENT_TYPES = frozenset({
    "multipart/form-data",
    "application/octet-stream",
    "image/",
    "audio/",
    "video/",
})


def _should_skip_body(content_type: str | None) -> bool:
    """Return True when the request body should NOT be logged."""
    if not content_type:
        return False
    ct = content_type.lower()
    return any(ct.startswith(skip) for skip in _SKIP_CONTENT_TYPES)


def _mask_sensitive(obj: Any) -> Any:
    """Recursively mask sensitive keys in dicts/lists."""
    if isinstance(obj, dict):
        return {
            k: "***" if k.lower() in _SENSITIVE_KEYS else _mask_sensitive(v)
            for k, v in obj.items()
        }
    if isinstance(obj, list):
        return [_mask_sensitive(item) for item in obj]
    return obj


def _short_id() -> str:
    """Return the first 12 hex chars of a UUID4 — short but unique enough."""
    return uuid.uuid4().hex[:12]


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Starlette middleware that binds per-request context to the shared logger."""

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        logger = get_logger(module="request")

        request_id = _short_id()
        method = request.method
        path = request.url.path
        query = dict(request.query_params) if request.query_params else None
        client_ip = request.client.host if request.client else None

        # --- Read body for mutating verbs (POST / PUT / PATCH) ---
        body_logged: Any = None
        if method in {"POST", "PUT", "PATCH"}:
            content_type = request.headers.get("content-type", "")
            if not _should_skip_body(content_type):
                try:
                    raw = await request.body()
                    if len(raw) <= _MAX_BODY_LOG_BYTES:
                        import json as _json
                        body_logged = _mask_sensitive(_json.loads(raw))
                    else:
                        body_logged = f"<body too large: {len(raw)} bytes>"
                except Exception:
                    body_logged = "<unreadable>"

        # --- Bind context (ContextVar) so ALL downstream logs carry these fields ---
        token = logger.bind_context(
            request_id=request_id,
            method=method,
            path=path,
        )

        try:
            # Log request start
            logger.info(
                f"{method} {path}",
                extra={
                    "event": "request.start",
                    "request_id": request_id,
                    "method": method,
                    "path": path,
                    "query": query,
                    "body": body_logged,
                    "client_ip": client_ip,
                },
            )

            start = time.perf_counter()
            response = await call_next(request)
            duration_ms = round((time.perf_counter() - start) * 1000)

            # --- Read response body if JSON ---
            response_body_logged: Any = None
            response_content_type = response.headers.get("content-type", "")
            if response_content_type and "application/json" in response_content_type.lower():
                try:
                    res_body = b""
                    async for chunk in response.body_iterator:
                        res_body += chunk
                    
                    # Reconstruct the response stream so client can still read it
                    response = Response(
                        content=res_body,
                        status_code=response.status_code,
                        headers=dict(response.headers),
                        media_type=response.media_type
                    )
                    
                    if len(res_body) <= _MAX_BODY_LOG_BYTES:
                        import json as _json
                        response_body_logged = _mask_sensitive(_json.loads(res_body))
                    else:
                        response_body_logged = f"<response too large: {len(res_body)} bytes>"
                except Exception:
                    response_body_logged = "<unreadable>"

            # Log request end
            logger.info(
                f"{method} {path} → {response.status_code} ({duration_ms}ms)",
                extra={
                    "event": "request.end",
                    "request_id": request_id,
                    "method": method,
                    "path": path,
                    "status_code": response.status_code,
                    "duration_ms": duration_ms,
                    "response_body": response_body_logged,
                },
            )

            return response

        except Exception as exc:
            duration_ms = round((time.perf_counter() - start) * 1000)
            logger.error(
                f"{method} {path} → UNHANDLED ({duration_ms}ms): {exc}",
                extra={
                    "event": "request.error",
                    "request_id": request_id,
                    "method": method,
                    "path": path,
                    "duration_ms": duration_ms,
                    "error": str(exc),
                },
            )
            raise
        finally:
            logger.reset_context(token)
