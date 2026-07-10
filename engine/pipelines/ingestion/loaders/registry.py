"""Loader registry: MIME type -> DocumentLoader."""

import logging
from typing import Dict, List, Type

from .base_loader import DocumentLoader
from engine.pipelines.ingestion.exceptions import UnsupportedMimetypeError  # noqa: I001

logger = logging.getLogger(__name__)


class LoaderRegistry:
    """Singleton registry for document loaders."""

    _loaders: Dict[str, Type[DocumentLoader]] = {}

    @classmethod
    def register(cls, mime_types: List[str], loader_class: Type[DocumentLoader]) -> None:
        """Register a loader for one or more MIME types."""
        for mime_type in mime_types:
            cls._loaders[mime_type] = loader_class
            logger.debug("Registered loader for %s: %s", mime_type, loader_class.__name__)

    @classmethod
    def _ensure_registered(cls) -> None:
        """Auto-register loaders if the registry is empty (e.g. in Celery workers)."""
        if not cls._loaders:
            try:
                try:
                    from engine.pipelines.ingestion.loaders import register_all_loaders
                except ImportError:
                    from engine.pipelines.ingestion.loaders import register_all_loaders
                register_all_loaders()
                logger.info("LoaderRegistry: auto-registered loaders (%d types)", len(cls._loaders))
            except Exception as e:
                logger.warning("LoaderRegistry: auto-registration failed: %s", e)

    @classmethod
    def get_loader(cls, mime_type: str) -> DocumentLoader:
        """Return an instantiated loader for the given MIME type."""
        cls._ensure_registered()
        loader_class = cls._loaders.get(mime_type)
        if not loader_class:
            raise UnsupportedMimetypeError(
                f"No loader for MIME type '{mime_type}'. Supported: {sorted(cls._loaders.keys())}"
            )
        return loader_class()

    @classmethod
    def supported_mimetypes(cls) -> List[str]:
        """Return all registered MIME types."""
        return list(cls._loaders.keys())

    @classmethod
    def list_loaders(cls) -> Dict[str, str]:
        """Return mime_type -> loader class name."""
        return {mime: cls._loaders[mime].__name__ for mime in cls._loaders}
