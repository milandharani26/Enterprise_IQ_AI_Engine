"""
Shared logging configuration. All services use this.
Log files: shared/logs/<service_name>/ matching project layout:
  - engine           -> shared/logs/engine/
  - cpanel/backend   -> shared/logs/cpanel/backend/
  - cpanel/frontend  -> shared/logs/cpanel/frontend/
  - gateway          -> shared/logs/gateway/
Call setup(service_name=...) at app startup.
"""
from shared.logging.adapter import StructuredLogger
from shared.logging.logger import LoggerConfig

_logger: StructuredLogger | None = None


def setup(log_dir: str | None = None, service_name: str | None = None) -> StructuredLogger:
    """Configure and return the shared logger. Call once at app startup with service_name (e.g. 'gateway', 'engine', 'cpanel/backend')."""
    global _logger
    underlying = LoggerConfig(log_dir=log_dir, service_name=service_name).setup()
    _logger = StructuredLogger(underlying)
    return _logger


def get_logger(module: str | None = None) -> StructuredLogger:
    """Return the shared logger.

    Args:
        module: Optional logical module name to bind once (for example,
            "assistant_service" or "auth"). When provided, all logs emitted
            from this instance will carry `module` unless overridden per call.
    """
    global _logger
    if _logger is None:
        # Fallback: write to shared/logs/ (no subfolder) so we never create shared/logs/app/
        underlying = LoggerConfig().setup()
        _logger = StructuredLogger(underlying)
    if module:
        return _logger.bind(module=module)
    return _logger


__all__ = ["LoggerConfig", "StructuredLogger", "setup", "get_logger"]
