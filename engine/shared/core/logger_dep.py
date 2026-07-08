"""
FastAPI dependency that provides a request-scoped structured logger.

Usage in routes::

    from engine.shared.core.logger_dep import get_request_logger
    from shared.logging import StructuredLogger

    @router.post("/example")
    async def my_route(
        ...,
        logger: StructuredLogger = Depends(get_request_logger),
    ):
        logger.info("doing work", extra={"event": "example.start"})
        service = MyService(db, logger)
        ...
"""

from fastapi import Request

from shared.logging import get_logger, StructuredLogger


async def get_request_logger(request: Request) -> StructuredLogger:
    """Return a logger pre-bound with the current route path.

    The ``request_id``, ``method``, and ``path`` are already in the
    ContextVar (set by ``RequestLoggingMiddleware``).  This dependency
    adds ``route`` so services can see which endpoint invoked them.
    """
    return get_logger().bind(route=request.url.path)
