"""PPTX document loader using python-pptx directly (no torch/transformers required).

Root cause of original error:
    LlamaIndex PptxReader pulls in torch + transformers as heavy optional deps.
    Even if python-pptx is installed, LlamaIndex raises:
        "Please install extra dependencies: pip install torch transformers<4.50 python-pptx Pillow"
    because its reader wrapper checks for the full AI stack.

Fix:
    Parse PPTX directly with python-pptx — no torch, no transformers, no Pillow.
    Extracts: slide text frames, table cells, and speaker notes.
    This is lighter, faster, and produces the same (or better) text output for RAG.

Install requirement (already lightweight):
    pip install python-pptx
"""

import asyncio
import logging
import os
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Tuple

from engine.pipelines.ingestion.exceptions import (
    CorruptDocumentError,
    DocumentLoadError,
)
from engine.pipelines.ingestion.loaders.base_loader import DocumentLoader
from engine.pipelines.ingestion.loaders.fetch import fetch_bytes_from_uri

logger = logging.getLogger(__name__)


def _extract_pptx_text(file_path: str) -> Tuple[str, Dict[str, Any]]:
    """
    Extract text from a PPTX file using python-pptx.

    Extracts from each slide:
    - All text frames (titles, body, text boxes)
    - Table cell contents
    - Speaker notes

    Returns:
        (full_text, metadata_dict)
    """
    try:
        from pptx import Presentation
        from pptx.util import Pt
    except ImportError:
        raise DocumentLoadError("python-pptx is required; run: pip install python-pptx")

    prs = Presentation(file_path)
    parts: List[str] = []
    metadata: Dict[str, Any] = {
        "format": "pptx",
        "loader": "python-pptx",
        "slide_count": len(prs.slides),
    }

    for slide_num, slide in enumerate(prs.slides, start=1):
        slide_parts: List[str] = []

        # ── Text frames (titles, body, text boxes) ────────────────────────
        for shape in slide.shapes:
            if shape.has_text_frame:
                for para in shape.text_frame.paragraphs:
                    line = " ".join(
                        run.text for run in para.runs if run.text.strip()
                    ).strip()
                    if line:
                        slide_parts.append(line)

            # ── Table cells ───────────────────────────────────────────────
            if shape.has_table:
                for row in shape.table.rows:
                    cells = [
                        cell.text.strip() for cell in row.cells if cell.text.strip()
                    ]
                    if cells:
                        slide_parts.append(" | ".join(cells))

        # ── Speaker notes ─────────────────────────────────────────────────
        if slide.has_notes_slide:
            notes_tf = slide.notes_slide.notes_text_frame
            if notes_tf:
                notes_text = notes_tf.text.strip()
                if notes_text:
                    slide_parts.append(f"[Notes: {notes_text}]")

        if slide_parts:
            parts.append(f"--- Slide {slide_num} ---\n" + "\n".join(slide_parts))

        metadata[f"slide_{slide_num}_shapes"] = len(slide.shapes)

    text = "\n\n".join(parts).strip()
    return text, metadata


class PptxLoader(DocumentLoader):
    """
    Load and extract text from PowerPoint (.pptx) using python-pptx directly.

    Does NOT require torch, transformers, or Pillow.
    Extracts slide text frames, table cells, and speaker notes.
    """

    @property
    def supported_mimetypes(self) -> List[str]:
        return [
            "application/vnd.openxmlformats-officedocument.presentationml.presentation"
        ]

    async def load_from_url(self, uri: str) -> Tuple[str, Dict[str, Any]]:
        if not self.validate_uri(uri):
            raise DocumentLoadError(f"Invalid URI scheme: {uri}")

        # Check dependency upfront with a clear message
        try:
            import pptx  # noqa: F401
        except ImportError:
            raise DocumentLoadError(
                "python-pptx is required; run: pip install python-pptx"
            )

        raw = await fetch_bytes_from_uri(uri)
        if not raw:
            raise CorruptDocumentError("Empty PPTX")

        tmp_path = None
        try:
            # delete=False — we close the file before python-pptx opens it.
            # This avoids WinError 32 (file in use) on Windows.
            with tempfile.NamedTemporaryFile(suffix=".pptx", delete=False) as tmp:
                tmp.write(raw)
                tmp_path = tmp.name
            # File handle is closed here — safe to open with python-pptx on Windows.

            text, metadata = await asyncio.to_thread(_extract_pptx_text, tmp_path)

        except (DocumentLoadError, CorruptDocumentError):
            raise
        except Exception as e:
            raise CorruptDocumentError(f"Cannot parse PPTX: {e}") from e
        finally:
            if tmp_path and os.path.exists(tmp_path):
                try:
                    os.unlink(tmp_path)
                except OSError as unlink_err:
                    # Non-fatal — log and move on; OS will clean up temp dir eventually
                    logger.warning(
                        "[PptxLoader] Could not delete temp file %s: %s",
                        tmp_path,
                        unlink_err,
                    )

        if not text:
            raise CorruptDocumentError("No content extracted from PPTX")

        logger.info(
            "[PptxLoader] Extracted %d slides, %d chars",
            metadata.get("slide_count", 0),
            len(text),
        )
        return text, metadata
