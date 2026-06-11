
# ============================================================================
# Generic Service Layer Exceptions
# ============================================================================

from engine.shared.exceptions.exceptions import AppException


class ServiceException(AppException):
    """Base exception for all service layers."""
    pass


# Validation Errors
class ValidationError(ServiceException):
    """Raised when validation fails."""
    status_code = 400
    error_code = "ERR_VALIDATION"
    message = "Validation failed"


# Not Found Errors
class NotFoundError(ServiceException):
    """Raised when resource not found."""
    status_code = 404
    error_code = "ERR_NOT_FOUND"
    message = "Resource not found"


class EntityNotFoundError(NotFoundError):
    """Generic entity not found (override message as needed)."""
    
    def __init__(self, entity_type: str, identifier: str = None):
        self.message = f"{entity_type} not found"
        if identifier:
            self.message += f" ({identifier})"
        super().__init__(self.message)


# Conflict Errors
class ConflictError(ServiceException):
    """Raised on conflict."""
    status_code = 409
    error_code = "ERR_CONFLICT"
    message = "Conflict error"


class AlreadyExistsError(ConflictError):
    """Resource already exists."""
    error_code = "ERR_ALREADY_EXISTS"
    message = "Resource already exists"


class StatusConflictError(ConflictError):
    """Invalid state transition or status."""
    error_code = "ERR_INVALID_STATUS"
    message = "Invalid status or state"


# Execution/Processing Errors
class ExecutionError(ServiceException):
    """Raised when execution/processing fails."""
    status_code = 502
    error_code = "ERR_EXECUTION_FAILED"
    message = "Execution failed"


class TimeoutError(ExecutionError):
    """Operation timed out."""
    error_code = "ERR_TIMEOUT"
    message = "Operation timed out"


class ExternalServiceError(ExecutionError):
    """External service call failed."""
    error_code = "ERR_EXTERNAL_SERVICE"
    message = "External service error"


# Authorization/Permission Errors
class AuthorizationError(ServiceException):
    """Raised when user lacks permission."""
    status_code = 403
    error_code = "ERR_FORBIDDEN"
    message = "Permission denied"


class AccessDeniedError(AuthorizationError):
    """Access to resource denied."""
    error_code = "ERR_ACCESS_DENIED"
    message = "Access denied"


# Business Logic Errors
class BusinessLogicError(ServiceException):
    """Raised when business logic constraint violated."""
    status_code = 422
    error_code = "ERR_BUSINESS_LOGIC"
    message = "Business logic error"


class InvalidOperationError(BusinessLogicError):
    """Operation not allowed in current state."""
    error_code = "ERR_INVALID_OPERATION"
    message = "Operation not allowed"