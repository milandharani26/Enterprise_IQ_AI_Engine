"""PDF document loader using LlamaIndex PDFReader."""

import asyncio
import logging
import os
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Tuple

from engine.pipelines.ingestion.exceptions import CorruptDocumentError, DocumentLoadError
from engine.pipelines.ingestion.loaders.base_loader import DocumentLoader
from engine.pipelines.ingestion.loaders.fetch import fetch_bytes_from_uri

logger = logging.getLogger(__name__)


class PDFLoader(DocumentLoader):
    """
    Load and extract text from PDF files using LlamaIndex PDFReader.

    Uses LlamaIndex PDFReader (backed by PyMuPDF) to extract per-page text
    with LlamaIndex metadata (page_label, file_name, etc.), aligning with
    the Phase 1 LlamaIndex integration spec.
    """

    @property
    def supported_mimetypes(self) -> List[str]:
        return ["application/pdf"]

    async def load_from_url(self, uri: str) -> Tuple[str, Dict[str, Any]]:
        if not self.validate_uri(uri):
            raise DocumentLoadError(f"Invalid URI scheme: {uri}")

        raw = await fetch_bytes_from_uri(uri)
        if not raw:
            raise CorruptDocumentError("Empty PDF")

        try:
            from llama_index.readers.file import PDFReader
        except ImportError:
            raise DocumentLoadError(
                "llama-index-readers-file is required; run: pip install llama-index-readers-file"
            )

        tmp_path = None
        try:
            with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
                tmp.write(raw)
                tmp_path = tmp.name

            reader = PDFReader(return_full_document=False)
            docs = await asyncio.to_thread(reader.load_data, Path(tmp_path))
        except DocumentLoadError:
            raise
        except Exception as e:
            raise CorruptDocumentError(f"Cannot parse PDF: {e}") from e
        finally:
            if tmp_path and os.path.exists(tmp_path):
                os.unlink(tmp_path)

        if not docs:
            raise CorruptDocumentError("No content extracted from PDF")

        parts: List[str] = []
        metadata: Dict[str, Any] = {
            "format": "pdf",
            "page_count": len(docs),
            "loader": "llama_index.PDFReader",
        }

        for i, doc in enumerate(docs):
            page_text = doc.text if hasattr(doc, "text") else str(doc)
            if page_text.strip():
                # Use page_label from LlamaIndex metadata if available
                page_label = None
                if hasattr(doc, "metadata") and doc.metadata:
                    page_label = doc.metadata.get("page_label") or doc.metadata.get("page")
                    if i == 0:
                        metadata["page_label_first"] = page_label
                    # Preserve LlamaIndex reader metadata per page
                    metadata[f"page_{i + 1}_meta"] = {
                        k: v for k, v in doc.metadata.items()
                        if k not in ("file_path",)  # skip local temp path
                    }

                label = page_label or str(i + 1)
                parts.append(f"--- Page {label} ---\n{page_text.strip()}")

        text = "\n\n".join(parts).strip()
        return text, metadata
