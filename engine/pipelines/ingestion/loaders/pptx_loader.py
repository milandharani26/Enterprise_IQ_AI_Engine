"""PPTX document loader using LlamaIndex PptxReader."""

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


class PptxLoader(DocumentLoader):
    """
    Load and extract text from PowerPoint (.pptx) using LlamaIndex PptxReader.

    LlamaIndex PptxReader (backed by python-pptx) extracts slide text and notes,
    preserving slide metadata aligned with the Phase 1 LlamaIndex integration spec.
    """

    @property
    def supported_mimetypes(self) -> List[str]:
        return ["application/vnd.openxmlformats-officedocument.presentationml.presentation"]

    async def load_from_url(self, uri: str) -> Tuple[str, Dict[str, Any]]:
        if not self.validate_uri(uri):
            raise DocumentLoadError(f"Invalid URI scheme: {uri}")

        try:
            from llama_index.readers.file import PptxReader
        except ImportError:
            raise DocumentLoadError(
                "llama-index-readers-file is required; run: pip install llama-index-readers-file"
            )

        raw = await fetch_bytes_from_uri(uri)
        if not raw:
            raise CorruptDocumentError("Empty PPTX")

        tmp_path = None
        try:
            with tempfile.NamedTemporaryFile(suffix=".pptx", delete=False) as tmp:
                tmp.write(raw)
                tmp_path = tmp.name

            reader = PptxReader()
            docs = await asyncio.to_thread(reader.load_data, Path(tmp_path))
        except DocumentLoadError:
            raise
        except Exception as e:
            raise CorruptDocumentError(f"Cannot parse PPTX: {e}") from e
        finally:
            if tmp_path and os.path.exists(tmp_path):
                os.unlink(tmp_path)

        if not docs:
            raise CorruptDocumentError("No content extracted from PPTX")

        parts: List[str] = []
        metadata: Dict[str, Any] = {
            "format": "pptx",
            "loader": "llama_index.PptxReader",
            "slide_count": len(docs),
        }

        for i, doc in enumerate(docs):
            page_text = doc.text if hasattr(doc, "text") else str(doc)
            if page_text.strip():
                slide_label = None
                if hasattr(doc, "metadata") and doc.metadata:
                    slide_label = doc.metadata.get("page_label") or doc.metadata.get("slide")
                    if i == 0:
                        metadata["slide_label_first"] = slide_label
                    metadata[f"slide_{i + 1}_meta"] = {
                        k: v for k, v in doc.metadata.items()
                        if k not in ("file_path",)
                    }

                label = slide_label or str(i + 1)
                parts.append(f"--- Slide {label} ---\n{page_text.strip()}")

        text = "\n\n".join(parts).strip()
        return text, metadata
