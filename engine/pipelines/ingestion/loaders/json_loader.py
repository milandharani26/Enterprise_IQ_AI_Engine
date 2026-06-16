"""JSON document loader."""

import json
import logging
from typing import Any, Dict, List, Tuple

from engine.pipelines.ingestion.exceptions import CorruptDocumentError, DocumentLoadError
from engine.pipelines.ingestion.loaders.base_loader import DocumentLoader
from engine.pipelines.ingestion.loaders.fetch import fetch_bytes_from_uri

logger = logging.getLogger(__name__)


class JsonLoader(DocumentLoader):
    """Load and serialize JSON files into chunkable text."""

    @property
    def supported_mimetypes(self) -> List[str]:
        return ["application/json", "text/json"]

    async def load_from_url(self, uri: str) -> Tuple[str, Dict[str, Any]]:
        if not self.validate_uri(uri):
            raise DocumentLoadError(f"Invalid URI scheme: {uri}")

        raw = await fetch_bytes_from_uri(uri)
        if not raw:
            raise CorruptDocumentError("Empty JSON")

        encoding = "utf-8"
        try:
            text = raw.decode("utf-8")
        except UnicodeDecodeError:
            try:
                import chardet

                result = chardet.detect(raw)
                encoding = result.get("encoding") or "utf-8"
                text = raw.decode(encoding, errors="replace")
            except Exception:
                text = raw.decode("utf-8", errors="replace")
                encoding = "utf-8 (fallback)"

        try:
            payload = json.loads(text)
        except Exception as e:
            raise CorruptDocumentError(f"Cannot parse JSON: {e}") from e

        try:
            formatted = json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True)
        except Exception:
            formatted = str(payload)

        metadata: Dict[str, Any] = {
            "format": "json",
            "loader": "python-json",
            "encoding": encoding,
            "characters": len(formatted),
            "root_type": type(payload).__name__,
        }
        if isinstance(payload, dict):
            metadata["top_level_keys"] = list(payload.keys())[:100]
        elif isinstance(payload, list):
            metadata["list_length"] = len(payload)

        return formatted, metadata

