"""Legacy DOC document loader (converts to DOCX via LibreOffice)."""

from __future__ import annotations

import asyncio
import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Tuple

from engine.pipelines.ingestion.exceptions import CorruptDocumentError, DocumentLoadError
from engine.pipelines.ingestion.loaders.base_loader import DocumentLoader
from engine.pipelines.ingestion.loaders.fetch import fetch_bytes_from_uri
from engine.pipelines.ingestion.loaders.libreoffice_utils import (
    LibreOfficeNotAvailableError,
    convert_office_bytes_to_format,
)

logger = logging.getLogger(__name__)


class DocLoader(DocumentLoader):
    """Load and extract text from legacy Microsoft Word (.doc) files."""

    @property
    def supported_mimetypes(self) -> List[str]:
        return [
            "application/msword",
            "application/vnd.ms-word",
            "application/x-msword",
        ]

    async def load_from_url(self, uri: str) -> Tuple[str, Dict[str, Any]]:
        if not self.validate_uri(uri):
            raise DocumentLoadError(f"Invalid URI scheme: {uri}")

        raw = await fetch_bytes_from_uri(uri)
        if not raw:
            raise CorruptDocumentError("Empty DOC")

        converted_path: Path | None = None
        try:
            try:
                converted_path = convert_office_bytes_to_format(
                    raw=raw,
                    input_suffix=".doc",
                    output_suffix=".docx",
                    convert_to="docx",
                )
            except LibreOfficeNotAvailableError as e:
                raise DocumentLoadError(str(e)) from e
            except Exception as e:
                raise CorruptDocumentError(f"Cannot convert DOC to DOCX: {e}") from e

            try:
                from llama_index.readers.file import DocxReader
            except ImportError as e:
                raise DocumentLoadError(
                    "llama-index-readers-file is required; run: pip install llama-index-readers-file"
                ) from e

            reader = DocxReader()
            docs = await asyncio.to_thread(reader.load_data, converted_path)

        except DocumentLoadError:
            raise
        except CorruptDocumentError:
            raise
        except Exception as e:
            raise CorruptDocumentError(f"Cannot parse DOC (converted): {e}") from e
        finally:
            if converted_path and os.path.exists(converted_path):
                try:
                    os.unlink(converted_path)
                except Exception:
                    pass

        if not docs:
            raise CorruptDocumentError("No content extracted from DOC")

        parts: List[str] = []
        metadata: Dict[str, Any] = {
            "format": "doc",
            "loader": "llama_index.DocxReader (via LibreOffice conversion)",
            "doc_count": len(docs),
        }

        for doc in docs:
            page_text = doc.text if hasattr(doc, "text") else str(doc)
            if page_text.strip():
                parts.append(page_text.strip())

        text = "\n\n".join(parts).strip()
        if not text:
            raise CorruptDocumentError("No text extracted from converted DOCX")
        return text, metadata

