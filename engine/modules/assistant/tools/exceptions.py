"""Assistant tool exceptions."""

class ToolExecutionError(Exception):
    def __init__(self, message: str, original_error: Exception = None, context: dict = None):
        super().__init__(message)
        self.original_error = original_error
        self.context = context or {}


class ConfigurationError(Exception):
    def __init__(self, message: str, original_error: Exception = None, context: dict = None):
        super().__init__(message)
        self.original_error = original_error
        self.context = context or {}


class LLMInitializationError(Exception):
    def __init__(self, message: str, original_error: Exception = None, context: dict = None):
        super().__init__(message)
        self.original_error = original_error
        self.context = context or {}


class SecurityGuardrailError(Exception):
    def __init__(self, message: str):
        super().__init__(message)
