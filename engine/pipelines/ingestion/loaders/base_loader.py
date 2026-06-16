"""Abstract base class for document loaders."""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Tuple

from engine.pipelines.ingestion.exceptions import DocumentLoadError  # noqa: I001


class DocumentLoader(ABC):
    """Abstract base class for document loaders."""

    @property
    @abstractmethod
    def supported_mimetypes(self) -> List[str]:
        """Return list of MIME types this loader handles."""
        pass

    @abstractmethod
    async def load_from_url(self, uri: str) -> Tuple[str, Dict[str, Any]]:
        """
        Load and parse document from URI.

        Args:
            uri: Source URI (s3://bucket/key, gs://bucket/blob, https://url).

        Returns:
            (text: str, metadata: dict)

        Raises:
            UnsupportedMimetypeError: URI not supported by this loader.
            DocumentLoadError: Fetching or parsing failed.
        """
        pass

    def validate_uri(self, uri: str) -> bool:
        """Check if URI has a valid scheme."""
        return any(
            uri.startswith(scheme)
            for scheme in ("s3://", "gs://", "http://", "https://", "file://")
        )
