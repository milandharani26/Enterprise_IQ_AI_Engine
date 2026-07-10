"""Plain text document loader."""

import logging
from typing import Any, Dict, List, Tuple

from engine.pipelines.ingestion.exceptions import CorruptDocumentError, DocumentLoadError
from engine.pipelines.ingestion.loaders.base_loader import DocumentLoader
from engine.pipelines.ingestion.loaders.fetch import fetch_bytes_from_uri

logger = logging.getLogger(__name__)


class TxtLoader(DocumentLoader):
    """Load plain text (and optionally markdown) files."""

    @property
    def supported_mimetypes(self) -> List[str]:
        return ["text/plain", "text/markdown"]

    async def load_from_url(self, uri: str) -> Tuple[str, Dict[str, Any]]:
        if not self.validate_uri(uri):
            raise DocumentLoadError(f"Invalid URI scheme: {uri}")

        raw = await fetch_bytes_from_uri(uri)

        encoding = "utf-8"
        try:
            text = raw.decode("utf-8")
        except UnicodeDecodeError:
            try:
                import chardet
                result = chardet.detect(raw)
                encoding = result.get("encoding") or "utf-8"
                text = raw.decode(encoding)
            except Exception as e:
                text = raw.decode("utf-8", errors="replace")
                encoding = "utf-8 (fallback)"

        text = text.replace("\r\n", "\n").replace("\r", "\n")
        lines = text.count("\n") + (1 if text.strip() else 0)
        metadata: Dict[str, Any] = {
            "format": "txt",
            "encoding": encoding,
            "lines": lines,
            "characters": len(text),
        }
        return text.strip(), metadata
