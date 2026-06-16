"""HTML document loader."""

import logging
from typing import Any, Dict, List, Tuple

from engine.pipelines.ingestion.exceptions import CorruptDocumentError, DocumentLoadError
from engine.pipelines.ingestion.loaders.base_loader import DocumentLoader
from engine.pipelines.ingestion.loaders.fetch import fetch_bytes_from_uri

logger = logging.getLogger(__name__)


class HtmlLoader(DocumentLoader):
    """Load and extract visible text from HTML/XHTML files."""

    @property
    def supported_mimetypes(self) -> List[str]:
        return ["text/html", "application/xhtml+xml"]

    async def load_from_url(self, uri: str) -> Tuple[str, Dict[str, Any]]:
        if not self.validate_uri(uri):
            raise DocumentLoadError(f"Invalid URI scheme: {uri}")

        raw = await fetch_bytes_from_uri(uri)
        if not raw:
            raise CorruptDocumentError("Empty HTML")

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
            from bs4 import BeautifulSoup
        except ImportError:
            raise DocumentLoadError("beautifulsoup4 is required; run: pip install beautifulsoup4")

        try:
            soup = BeautifulSoup(text, "html.parser")
            for tag in soup(["script", "style", "noscript"]):
                tag.decompose()
            extracted = soup.get_text(separator="\n")
            normalized = "\n".join(line.strip() for line in extracted.splitlines() if line.strip())
        except Exception as e:
            raise CorruptDocumentError(f"Cannot parse HTML: {e}") from e

        if not normalized:
            raise CorruptDocumentError("No visible text extracted from HTML")

        metadata: Dict[str, Any] = {
            "format": "html",
            "loader": "beautifulsoup4",
            "encoding": encoding,
            "characters": len(normalized),
        }
        title_tag = soup.title.string.strip() if soup.title and soup.title.string else None
        if title_tag:
            metadata["title"] = title_tag
        return normalized, metadata

