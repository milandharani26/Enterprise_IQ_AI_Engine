"""
JSON log formatter for the shared Loguru logger.

Emits one JSON object per line with a flat schema. Reserved top-level fields
are always present (populated or null); anything else the caller binds or
passes via `extra={...}` is flattened at the root of the same object.

    {
      "timestamp":  "2026-04-21T10:00:00.123Z",   # ISO-8601, UTC, millisecond precision
      "level":      "INFO",
      "service":    "engine",
      "module":     "auth",
      "event":      "login.success",
      "outcome":    "success",                     # success | failure | error | null
      "request_id": "c1f2e3d4-...",
      "actor_id":   "uuid-or-null",
      "<anything else bound or passed via extra={...}>": ...
    }
"""

import json
from datetime import timezone

_RESERVED_KEYS = (
    "timestamp",
    "level",
    "message",
    "service",
    "module",
    "event",
    "outcome",
    "request_id",
    "actor_id",
    "exception",
)

_TOP_LEVEL_KEYS = (
    "service",
    "module",
    "event",
    "outcome",
    "request_id",
    "actor_id",
)

_INTERNAL_KEYS = ("_serialized",)


def _format_timestamp(record_time) -> str:
    ts = record_time.astimezone(timezone.utc)
    return f"{ts.strftime('%Y-%m-%dT%H:%M:%S')}.{ts.microsecond // 1000:03d}Z"


def _build_payload(record: dict) -> dict:
    raw_extra = dict(record.get("extra") or {})

    for k in _INTERNAL_KEYS:
        raw_extra.pop(k, None)

    nested = raw_extra.pop("extra", None)
    if isinstance(nested, dict):
        for k, v in nested.items():
            raw_extra.setdefault(k, v)

    top: dict = {}
    for key in _TOP_LEVEL_KEYS:
        top[key] = raw_extra.pop(key, None)

    if not top["module"]:
        top["module"] = record.get("module")
    if not top["event"]:
        top["event"] = record["message"]

    for reserved in _RESERVED_KEYS:
        raw_extra.pop(reserved, None)

    payload = {
        "timestamp": _format_timestamp(record["time"]),
        "level": record["level"].name,
        "message": record["message"],
        **top,
        **raw_extra,
    }

    exc = record.get("exception")
    if exc is not None:
        exc_type = getattr(exc.type, "__name__", str(exc.type)) if exc.type else None
        payload["exception"] = {
            "type": exc_type,
            "message": str(exc.value) if exc.value is not None else None,
        }

    return payload


def json_formatter(record: dict) -> str:
    """Loguru format callable: packs the record into our schema as a single JSON line."""
    payload = _build_payload(record)
    record["extra"]["_serialized"] = json.dumps(payload, default=str, ensure_ascii=False)
    return "{extra[_serialized]}\n"


def ensure_console_defaults(record: dict) -> bool:
    """Filter that guarantees {extra[event]} exists for the pretty console format."""
    record["extra"].setdefault("event", record["message"])
    return True
