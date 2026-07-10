"""
Thin adapter around Loguru's logger that:

1. Accepts a stdlib-style `extra={...}` kwarg on every log method and surfaces
   those keys at the ROOT of the emitted JSON (see `formatter.py`).
2. Supports both `%`-style and `{}`-style message formatting so existing
   call sites (e.g. `logger.info("loaded %s", n)`) keep working.
3. Preserves Loguru's chaining: `.bind(...)` / `.opt(...)` return another
   `StructuredLogger` so callers can keep chaining.

Usage:
    from shared.logging import get_logger
    log = get_logger()

    # Stdlib-style, extras flatten to the root of the JSON log object.
    log.info("assistant preloader refreshed (%s loaded)", count,
             extra={"module": "assistants", "event": "preloader.refreshed",
                    "outcome": "success", "loaded_count": count})

    # Loguru-style binding still works.
    log.bind(module="auth", event="login.success").info("user logged in")
"""

from collections.abc import Mapping
from contextvars import ContextVar, Token
from typing import Any, Optional

from loguru import logger as _loguru_logger

_log_context: ContextVar[dict[str, Any]] = ContextVar("_log_context", default={})


def _format_message(msg: Any, args: tuple) -> str:
    if not isinstance(msg, str) or not args:
        return str(msg)
    try:
        return msg % args
    except (TypeError, ValueError):
        try:
            return msg.format(*args)
        except Exception:
            return msg


def _normalize_extra(extra: Any) -> dict[str, Any]:
    """Accept dict-like or object-like extras and normalize to a plain dict."""
    if extra is None:
        return {}
    if isinstance(extra, Mapping):
        return dict(extra)
    if isinstance(extra, (str, bytes)):
        return {"extra_value": extra}
    if isinstance(extra, tuple):
        return {f"item_{idx}": value for idx, value in enumerate(extra)}
    if isinstance(extra, list):
        return {"items": extra}
    if hasattr(extra, "model_dump") and callable(extra.model_dump):
        try:
            dumped = extra.model_dump()
            if isinstance(dumped, Mapping):
                return dict(dumped)
        except Exception:
            pass
    if hasattr(extra, "__dict__"):
        try:
            return dict(vars(extra))
        except Exception:
            pass
    return {"extra_value": extra}


class StructuredLogger:
    """Loguru logger wrapper that accepts `extra={...}` and flattens it to the root."""

    __slots__ = ("_logger",)

    def __init__(self, logger=None):
        self._logger = logger if logger is not None else _loguru_logger

    def bind(self, **kwargs) -> "StructuredLogger":
        return StructuredLogger(self._logger.bind(**kwargs))

    def opt(self, **kwargs) -> "StructuredLogger":
        return StructuredLogger(self._logger.opt(**kwargs))

    def bind_context(self, **kwargs) -> Token:
        """Bind request/task context (auto-applied to all logs in this context)."""
        current = dict(_log_context.get())
        current.update(kwargs)
        return _log_context.set(current)

    def reset_context(self, token: Token) -> None:
        """Reset context back to a previously returned token."""
        _log_context.reset(token)

    def clear_context(self) -> None:
        """Clear all context-bound values for current execution context."""
        _log_context.set({})

    def _emit(
        self,
        level: str,
        msg: Any,
        args: tuple,
        extra: Any,
        *,
        exception: Any = None,
    ) -> None:
        formatted = _format_message(msg, args)
        bound = self._logger
        context_extra = _log_context.get()
        if context_extra:
            bound = bound.bind(**context_extra)
        if extra:
            bound = bound.bind(**_normalize_extra(extra))
        proxy = bound.opt(depth=2, exception=exception) if exception else bound.opt(depth=2)
        # Pre-formatted string is passed as a value so loguru never re-interprets
        # stray "{" / "}" characters that may be present in the final message.
        proxy.log(level, "{0}", formatted)

    # Standard level methods
    def debug(self, msg, *args, extra: Any = None, **_kwargs) -> None:
        self._emit("DEBUG", msg, args, extra)

    def info(self, msg, *args, extra: Any = None, **_kwargs) -> None:
        self._emit("INFO", msg, args, extra)

    def warning(self, msg, *args, extra: Any = None, **_kwargs) -> None:
        self._emit("WARNING", msg, args, extra)

    warn = warning

    def error(self, msg, *args, extra: Any = None, **_kwargs) -> None:
        self._emit("ERROR", msg, args, extra)

    def critical(self, msg, *args, extra: Any = None, **_kwargs) -> None:
        self._emit("CRITICAL", msg, args, extra)

    def exception(self, msg, *args, extra: Any = None, **_kwargs) -> None:
        # Captures the current exception info automatically.
        self._emit("ERROR", msg, args, extra, exception=True)

    def log(self, level, msg, *args, extra: Any = None, **_kwargs) -> None:
        self._emit(level, msg, args, extra)

    # Fall through for anything we haven't wrapped (e.g. level(), add(), remove()).
    def __getattr__(self, name):
        return getattr(self._logger, name)
