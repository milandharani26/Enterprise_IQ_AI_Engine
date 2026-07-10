"""DOCX document loader using LlamaIndex DocxReader."""

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


class DocxLoader(DocumentLoader):
    """
    Load and extract text from Word documents (.docx) using LlamaIndex DocxReader.

    LlamaIndex DocxReader (backed by python-docx) extracts paragraphs and tables,
    preserving section metadata aligned with the Phase 1 LlamaIndex integration spec.
    """

    @property
    def supported_mimetypes(self) -> List[str]:
        return ["application/vnd.openxmlformats-officedocument.wordprocessingml.document"]

    async def load_from_url(self, uri: str) -> Tuple[str, Dict[str, Any]]:
        if not self.validate_uri(uri):
            raise DocumentLoadError(f"Invalid URI scheme: {uri}")

        try:
            from llama_index.readers.file import DocxReader
        except ImportError:
            raise DocumentLoadError(
                "llama-index-readers-file is required; run: pip install llama-index-readers-file"
            )

        raw = await fetch_bytes_from_uri(uri)
        if not raw:
            raise CorruptDocumentError("Empty DOCX")

        tmp_path = None
        try:
            with tempfile.NamedTemporaryFile(suffix=".docx", delete=False) as tmp:
                tmp.write(raw)
                tmp_path = tmp.name

            reader = DocxReader()
            docs = await asyncio.to_thread(reader.load_data, Path(tmp_path))
        except DocumentLoadError:
            raise
        except Exception as e:
            raise CorruptDocumentError(f"Cannot parse DOCX: {e}") from e
        finally:
            if tmp_path and os.path.exists(tmp_path):
                os.unlink(tmp_path)

        if not docs:
            raise CorruptDocumentError("No content extracted from DOCX")

        parts: List[str] = []
        metadata: Dict[str, Any] = {
            "format": "docx",
            "loader": "llama_index.DocxReader",
            "doc_count": len(docs),
        }

        for doc in docs:
            page_text = doc.text if hasattr(doc, "text") else str(doc)
            if page_text.strip():
                parts.append(page_text.strip())
            # Carry over LlamaIndex metadata (section, author, etc.)
            if hasattr(doc, "metadata") and doc.metadata:
                for k, v in doc.metadata.items():
                    if k not in ("file_path",):
                        metadata[k] = v

        text = "\n\n".join(parts).strip()
        return text, metadata
