"""
Shared Loguru-based logger.

Console: human-readable (pretty) output.
File sinks: structured JSON (see `shared/logging/formatter.py` for the schema).

Usage:
    from shared.logging import get_logger
    log = get_logger()
    log.bind(
        module="auth",
        event="login.success",
        outcome="success",
        request_id=rid,
        actor_id=str(user.admin_id),
        email=user.email,
    ).info("user logged in")
"""

import sys
import os
from pathlib import Path

from loguru import logger

from shared.logging.formatter import ensure_console_defaults, json_formatter

_SHARED_LOGS_DIR = Path(__file__).resolve().parent.parent / "logs"

_CONSOLE_FORMAT = (
    "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
    "<level>{level: <8}</level> | "
    "<dim>{extra[request_id]!s:<12}</dim> | "
    "<cyan>{extra[event]!s:<24}</cyan> | "
    "<level>{message}</level>"
)

_TOOL_EVENTS = (
    '"event": "tool_start"',
    '"event": "tool_success"',
    '"event": "tool_error"',
    '"event": "tool_execution_summary"',
)


def _tool_execution_filter(record: dict) -> bool:
    msg = record["message"].strip()
    return msg.startswith("{") and any(evt in msg for evt in _TOOL_EVENTS)


import logging


class InterceptHandler(logging.Handler):
    """Logs standard library logging messages to Loguru."""

    def emit(self, record: logging.LogRecord) -> None:
        # Get corresponding Loguru level if it exists
        try:
            level = logger.level(record.levelname).name
        except ValueError:
            level = record.levelno

        # Find caller from where originated the logged message
        frame, depth = logging.currentframe(), 2
        while frame and frame.f_code.co_filename == logging.__file__:
            frame = frame.f_back
            depth += 1

        logger.opt(depth=depth, exception=record.exc_info).log(level, record.getMessage())


class LoggerConfig:
    def __init__(self, log_dir: str | Path | None = None, service_name: str | None = None):
        self.service_name = service_name
        if log_dir is not None:
            self.log_dir = Path(log_dir)
        elif service_name is not None:
            self.log_dir = _SHARED_LOGS_DIR / service_name
        else:
            self.log_dir = _SHARED_LOGS_DIR
        self.log_dir.mkdir(parents=True, exist_ok=True)

    def setup(self):
        logger.remove()
        logger.configure(extra={"service": self.service_name})
        log_level = os.getenv("LOG_LEVEL", "INFO").upper()
        if log_level == "INFO":
            # Helpful default for local debugging without requiring env changes.
            env_name = os.getenv("ENV", "").lower()
            if env_name in {"local", "dev", "development", "debug"}:
                log_level = "DEBUG"

        logger.add(
            sys.stdout,
            level=log_level,
            serialize=False,
            format=_CONSOLE_FORMAT,
            filter=ensure_console_defaults,
        )

        # Single JSON log file for all application, request, tool, and error logs
        logger.add(
            _SHARED_LOGS_DIR / "app.json.log",
            level=log_level,
            rotation="50 MB",
            retention="30 days",
            compression="zip",
            serialize=False,
            format=json_formatter,
        )

        # Route standard library logs to Loguru
        logging.basicConfig(handlers=[InterceptHandler()], level=0, force=True)
        for logger_name in ("uvicorn", "uvicorn.access", "uvicorn.error", "fastapi", "sqlalchemy"):
            logging_logger = logging.getLogger(logger_name)
            logging_logger.handlers = [InterceptHandler()]
            logging_logger.propagate = False

        return logger
