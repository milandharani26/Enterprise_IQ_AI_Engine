"""Legacy PPT document loader (converts to PPTX via LibreOffice)."""

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


class PptLoader(DocumentLoader):
    """Load and extract text from legacy PowerPoint (.ppt) files."""

    @property
    def supported_mimetypes(self) -> List[str]:
        return [
            "application/vnd.ms-powerpoint",
            "application/vnd.ms-powerpoint.presentation.macroEnabled.12",
            "application/x-mspowerpoint",
        ]

    async def load_from_url(self, uri: str) -> Tuple[str, Dict[str, Any]]:
        if not self.validate_uri(uri):
            raise DocumentLoadError(f"Invalid URI scheme: {uri}")

        raw = await fetch_bytes_from_uri(uri)
        if not raw:
            raise CorruptDocumentError("Empty PPT")

        converted_path: Path | None = None
        try:
            try:
                converted_path = convert_office_bytes_to_format(
                    raw=raw,
                    input_suffix=".ppt",
                    output_suffix=".pptx",
                    convert_to="pptx",
                )
            except LibreOfficeNotAvailableError as e:
                raise DocumentLoadError(str(e)) from e
            except Exception as e:
                raise CorruptDocumentError(f"Cannot convert PPT to PPTX: {e}") from e

            try:
                from llama_index.readers.file import PptxReader
            except ImportError as e:
                raise DocumentLoadError(
                    "llama-index-readers-file is required; run: pip install llama-index-readers-file"
                ) from e

            reader = PptxReader()
            docs = await asyncio.to_thread(reader.load_data, converted_path)

        except DocumentLoadError:
            raise
        except CorruptDocumentError:
            raise
        except Exception as e:
            raise CorruptDocumentError(f"Cannot parse PPT (converted): {e}") from e
        finally:
            if converted_path and os.path.exists(converted_path):
                try:
                    os.unlink(converted_path)
                except Exception:
                    pass

        if not docs:
            raise CorruptDocumentError("No content extracted from PPT")

        parts: List[str] = []
        metadata: Dict[str, Any] = {
            "format": "ppt",
            "loader": "llama_index.PptxReader (via LibreOffice conversion)",
            "slide_count": len(docs),
        }

        for i, doc in enumerate(docs):
            slide_text = doc.text if hasattr(doc, "text") else str(doc)
            if slide_text.strip():
                slide_label = None
                if hasattr(doc, "metadata") and doc.metadata:
                    slide_label = doc.metadata.get("page_label") or doc.metadata.get("slide")
                label = slide_label or str(i + 1)
                parts.append(f"--- Slide {label} ---\n{slide_text.strip()}")

        text = "\n\n".join(parts).strip()
        if not text:
            raise CorruptDocumentError("No text extracted from converted PPTX")
        return text, metadata

