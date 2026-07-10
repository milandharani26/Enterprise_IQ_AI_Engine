"""Exceptions for document loading and ingestion."""


class DocumentLoadError(Exception):
    """Base error for document loading."""


class UnsupportedMimetypeError(DocumentLoadError):
    """Raised when MIME type has no registered loader."""


class CorruptDocumentError(DocumentLoadError):
    """Raised when document is corrupted or unreadable."""


class CloudStorageError(DocumentLoadError):
    """Raised when fetching from S3/GCS fails."""


class EncodingError(DocumentLoadError):
    """Raised when text encoding cannot be determined."""


class EmbeddingError(Exception):
    """Base error for embedding operations."""


class WebhookError(Exception):
    """Base error for webhook operations."""


class WebhookDeliveryError(WebhookError):
    """Failed to deliver webhook after all retries."""
