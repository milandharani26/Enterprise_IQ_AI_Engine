from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from shared.logging import get_logger
from engine.shared.schemas.common import ErrorResponse
from datetime import datetime, timezone

logger = get_logger()


# ============================================================================
# Domain Exceptions (Service Layer)
# ============================================================================

class AppException(Exception):
    """Base exception for entire application."""
    status_code: int = 500
    error_code: str = "ERR_INTERNAL"
    message: str = "An unexpected error occurred"
    
    def __init__(self, message: str = None, **kwargs):
        if message:
            self.message = message
        self.extra_data = kwargs
        super().__init__(self.message)


# Auth Service Exceptions
class AuthException(AppException):
    """Base exception for auth service."""
    pass


class InvalidCredentialsError(AuthException):
    """Invalid username or password."""
    status_code = 401
    error_code = "ERR_INVALID_CREDENTIALS"
    message = "Invalid username or password"


class AccountDisabledError(AuthException):
    """User account is disabled."""
    status_code = 403
    error_code = "ERR_ACCOUNT_DISABLED"
    message = "Account is disabled"


class SessionExpiredError(AuthException):
    """User session has expired."""
    status_code = 401
    error_code = "ERR_SESSION_EXPIRED"
    message = "Your session has expired. Please login again"


class InvalidSessionError(AuthException):
    """Session token is invalid."""
    status_code = 401
    error_code = "ERR_INVALID_SESSION"
    message = "Invalid or expired session"


class InvalidTokenError(AuthException):
    """JWT token is invalid or malformed."""
    status_code = 401
    error_code = "ERR_INVALID_TOKEN"
    message = "Invalid token"


class InvalidPasswordError(AuthException):
    """Current password is incorrect."""
    status_code = 401
    error_code = "ERR_INVALID_PASSWORD"
    message = "Current password is incorrect"


class PasswordTooShortError(AuthException):
    """New password does not meet minimum length requirement."""
    status_code = 400
    error_code = "ERR_PASSWORD_TOO_SHORT"
    message = "New password must be at least 8 characters"


class UserNotFoundError(AuthException):
    """User not found in database."""
    status_code = 404
    error_code = "ERR_USER_NOT_FOUND"
    message = "User not found"


# Document Service Exceptions
class DocumentException(AppException):
    """Base exception for document service."""
    pass


class DocumentNotFoundError(DocumentException):
    """Document not found in workspace."""
    status_code = 404
    error_code = "ERR_DOCUMENT_NOT_FOUND"
    message = "Document not found"


class DocumentAlreadyExistsError(DocumentException):
    """Document with same reference_id or title already exists."""
    status_code = 409
    error_code = "ERR_DOCUMENT_EXISTS"
    message = "Document already exists"


class InvalidDocumentStatusError(DocumentException):
    """Invalid document status value."""
    status_code = 400
    error_code = "ERR_INVALID_STATUS"
    message = "Invalid document status"


class InvalidChunkError(DocumentException):
    """Invalid chunk data."""
    status_code = 400
    error_code = "ERR_INVALID_CHUNK"
    message = "Invalid chunk data"


# Assistant Service Exceptions
class AssistantException(AppException):
    """Base exception for assistant service."""
    pass


class AssistantNotFoundError(AssistantException):
    """Assistant not found."""
    status_code = 404
    error_code = "ERR_ASSISTANT_NOT_FOUND"
    message = "Assistant not found"


class AssistantNotReadyError(AssistantException):
    """Assistants not preloaded or server starting up."""
    status_code = 503
    error_code = "ERR_ASSISTANTS_NOT_READY"
    message = "Assistants not preloaded. Server starting up."


class AssistantReloadError(AssistantException):
    """Failed to reload assistant."""
    status_code = 500
    error_code = "ERR_ASSISTANT_RELOAD_FAILED"
    message = "Failed to reload assistant"


class AssistantNameExistsError(AssistantException):
    """Assistant name already exists."""
    status_code = 409
    error_code = "ERR_ASSISTANT_NAME_EXISTS"
    message = "Assistant name already exists"


class AssistantCodeExistsError(AssistantException):
    """Assistant code already exists."""
    status_code = 409
    error_code = "ERR_ASSISTANT_CODE_EXISTS"
    message = "Assistant code already exists"


class InvalidAssistantCodeFormatError(AssistantException):
    """Assistant code format is invalid."""
    status_code = 400
    error_code = "ERR_INVALID_CODE_FORMAT"
    message = "Invalid code format. Use alphanumeric characters and underscores only."


class InvalidAssistantStatusError(AssistantException):
    """Assistant status is invalid."""
    status_code = 400
    error_code = "ERR_INVALID_STATUS"
    message = "Invalid status. Use 'enabled' or 'disabled'."


class InvalidAssistantConfigurationError(AssistantException):
    """Assistant configuration payload is invalid."""
    status_code = 400
    error_code = "ERR_INVALID_ASSISTANT_CONFIGURATION"
    message = "Invalid assistant configuration"


class DuplicateAssistantToolError(AssistantException):
    """Assistant tool definitions contain duplicates."""
    status_code = 400
    error_code = "ERR_DUPLICATE_TOOL_ID"
    message = "Duplicate tool_id in assistant tools"


# Agent Service Exceptions
class AgentException(AppException):
    """Base exception for agent service."""
    pass


class AgentNotFoundError(AgentException):
    """Agent not found."""
    status_code = 404
    error_code = "ERR_AGENT_NOT_FOUND"
    message = "Agent not found"


class AgentNameExistsError(AgentException):
    """Agent name already exists."""
    status_code = 409
    error_code = "ERR_AGENT_NAME_EXISTS"
    message = "Agent name already exists"


class AgentCodeExistsError(AgentException):
    """Agent code already exists."""
    status_code = 409
    error_code = "ERR_AGENT_CODE_EXISTS"
    message = "Agent code already exists"


class InvalidAgentCodeFormatError(AgentException):
    """Agent code format is invalid."""
    status_code = 400
    error_code = "ERR_INVALID_CODE_FORMAT"
    message = (
        "Invalid code format. Code must start with a lowercase letter "
        "and contain only lowercase alphanumeric characters and underscores."
    )


# Connector Service Exceptions
class ConnectorException(AppException):
    """Base exception for connector service."""
    pass


class ConnectorNotFoundError(ConnectorException):
    """Connector not found."""
    status_code = 404
    error_code = "ERR_CONNECTOR_NOT_FOUND"
    message = "Connector not found"


class InvalidConnectorError(ConnectorException):
    """Connector payload or identifier is invalid."""
    status_code = 400
    error_code = "ERR_INVALID_CONNECTOR"
    message = "Invalid connector"


# Database Exceptions
class DatabaseError(AppException):
    """Database operation failed."""
    status_code = 500
    error_code = "ERR_DATABASE"
    message = "Database operation failed"


# Chat Feedback Service Exceptions
class ChatFeedbackException(AppException):
    """Base exception for chat feedback service."""
    pass


class MessageNotFoundError(ChatFeedbackException):
    """Conversation message not found."""
    status_code = 404
    error_code = "ERR_MESSAGE_NOT_FOUND"
    message = "Message not found"


class FeedbackNotFoundError(ChatFeedbackException):
    """Feedback not found for the requested scope."""
    status_code = 404
    error_code = "ERR_FEEDBACK_NOT_FOUND"
    message = "Feedback not found"


class InvalidFeedbackError(ChatFeedbackException):
    """Feedback payload is invalid."""
    status_code = 400
    error_code = "ERR_INVALID_FEEDBACK"
    message = "Invalid feedback payload"


class FeedbackPersistenceError(ChatFeedbackException):
    """Feedback create/update failed."""
    status_code = 500
    error_code = "ERR_FEEDBACK_PERSISTENCE"
    message = "Failed to persist feedback"


# Prompt Management Exceptions
class PromptManagementException(AppException):
    """Base exception for prompt management service."""
    pass


class PromptNotFoundError(PromptManagementException):
    """Prompt not found."""
    status_code = 404
    error_code = "ERR_PROMPT_NOT_FOUND"
    message = "Prompt not found"


class PromptDuplicateError(PromptManagementException):
    """Prompt title already exists."""
    status_code = 409
    error_code = "ERR_PROMPT_DUPLICATE"
    message = "Title already exists"


class PromptForbiddenError(PromptManagementException):
    """User is not allowed to manage this prompt."""
    status_code = 403
    error_code = "ERR_FORBIDDEN"
    message = "You do not have permission to perform this action"


class InvalidPromptStatusError(PromptManagementException):
    """Prompt status is invalid for the requested operation."""
    status_code = 400
    error_code = "ERR_INVALID_STATUS"
    message = "Invalid prompt status"


# Workspace Service Exceptions
class WorkspaceException(AppException):
    """Base exception for workspace service."""
    pass


class WorkspaceNotFoundError(WorkspaceException):
    """Workspace not found."""
    status_code = 404
    error_code = "ERR_WORKSPACE_NOT_FOUND"
    message = "Workspace not found"


class WorkspaceNameExistsError(WorkspaceException):
    """Workspace name already exists within the tenant."""
    status_code = 409
    error_code = "ERR_WORKSPACE_NAME_EXISTS"
    message = "A workspace with this name already exists"


class InvalidWorkspaceStatusError(WorkspaceException):
    """Workspace status is invalid."""
    status_code = 400
    error_code = "ERR_INVALID_STATUS"
    message = "Invalid status"


# Credential Service Exceptions
class CredentialException(AppException):
    """Base exception for credential service."""
    pass


class CredentialNotFoundError(CredentialException):
    """Credential not found."""
    status_code = 404
    error_code = "ERR_CREDENTIAL_NOT_FOUND"
    message = "Credential not found"


class CredentialNameExistsError(CredentialException):
    """Credential name already exists."""
    status_code = 409
    error_code = "ERR_CREDENTIAL_NAME_EXISTS"
    message = "Credential name already exists"


class InvalidCredentialDataError(CredentialException):
    """Credential payload is invalid."""
    status_code = 400
    error_code = "ERR_INVALID_CREDENTIAL_DATA"
    message = "Invalid credential data"


class InvalidProviderError(CredentialException):
    """Credential provider is invalid or unavailable."""
    status_code = 400
    error_code = "ERR_INVALID_PROVIDER"
    message = "Invalid provider type"


class ProviderNotFoundError(CredentialException):
    """Credential provider was not found."""
    status_code = 404
    error_code = "ERR_PROVIDER_NOT_FOUND"
    message = "Provider not found"


# Service Account Service Exceptions
class ServiceAccountException(AppException):
    """Base exception for service account service."""
    pass


class ServiceAccountNotFoundError(ServiceAccountException):
    """Service account not found."""
    status_code = 404
    error_code = "ERR_SERVICE_ACCOUNT_NOT_FOUND"
    message = "Service account not found"


class InvalidAppNameError(ServiceAccountException):
    """App name is invalid or missing."""
    status_code = 400
    error_code = "ERR_INVALID_APP_NAME"
    message = "App name is required"


class InvalidExpirationError(ServiceAccountException):
    """Expiration date is invalid or in the past."""
    status_code = 400
    error_code = "ERR_INVALID_EXPIRATION"
    message = "Expiration date cannot be in the past"


class AccountAlreadyRevokedError(ServiceAccountException):
    """Service account is already revoked."""
    status_code = 400
    error_code = "ERR_ACCOUNT_ALREADY_REVOKED"
    message = "Account already revoked"


class GlobalExceptionHandler:
    @staticmethod
    async def handle_app_exception(request: Request, exc: AppException):
        """Handle custom domain exceptions from service layer."""
        error_res = ErrorResponse(
            success=False,
            status_code=exc.status_code,
            error_code=exc.error_code,
            message=exc.message,
            timestamp=datetime.now(timezone.utc)
        )
        return JSONResponse(
            status_code=exc.status_code,
            content=error_res.model_dump(mode="json")
        )

    @staticmethod
    async def handle_http(request: Request, exc: HTTPException):
        """Standard HTTP error message."""
        error_code = "ERR_BAD_REQUEST"
        message = str(exc.detail)
        
        if isinstance(exc.detail, dict):
            error_code = exc.detail.get("error_code", error_code)
            message = exc.detail.get("message", message)
            
        # Common status code to error code mapping
        if not isinstance(exc.detail, dict):
            if exc.status_code == 404:
                error_code = "ERR_NOT_FOUND"
            elif exc.status_code == 401:
                error_code = "ERR_UNAUTHORIZED"
            elif exc.status_code == 403:
                error_code = "ERR_FORBIDDEN"
            elif exc.status_code == 409:
                error_code = "ERR_CONFLICT"
            elif exc.status_code >= 500:
                error_code = "ERR_INTERNAL_SERVER"

        error_res = ErrorResponse(
            success=False,
            status_code=exc.status_code,
            error_code=error_code,
            message=message,
            timestamp=datetime.now(timezone.utc)
        )
        return JSONResponse(
            status_code=exc.status_code,
            content=error_res.model_dump(mode="json")
        )

    @staticmethod
    async def handle_unhandled(request: Request, exc: Exception):
        """Standard 500 error message."""
        logger.exception(f"Unhandled Exception: {str(exc)}")
        error_res = ErrorResponse(
            success=False,
            status_code=500,
            error_code="ERR_INTERNAL_SERVER",
            message="An unexpected error occurred",
            timestamp=datetime.now(timezone.utc)
        )
        return JSONResponse(
            status_code=500,
            content=error_res.model_dump(mode="json")
        )

    @staticmethod
    async def handle_validation(request: Request, exc: RequestValidationError):
        """Standard 400 validation error message."""
        errors = exc.errors()
        msg = "Validation error"
        if errors:
            # Extract the first error message to provide meaningful feedback
            error = errors[0]
            msg = error.get("msg", "Validation error")
            # Remove "Value error, " prefix often added by Pydantic if present
            if msg.startswith("Value error, "):
                msg = msg.replace("Value error, ", "")
            
        error_res = ErrorResponse(
            success=False,
            status_code=400,
            error_code="ERR_VALIDATION",
            message=msg,
            timestamp=datetime.now(timezone.utc)
        )
        return JSONResponse(
            status_code=400,
            content=error_res.model_dump(mode="json")
        )
