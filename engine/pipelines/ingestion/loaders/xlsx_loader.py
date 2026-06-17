"""XLSX document loader using openpyxl.

Root cause of original error:
    WinError 32: "The process cannot access the file because it is being used by another process"

    The original code deleted the temp file inside the `finally` block, but openpyxl in
    read_only mode holds the file open via a ZipFile handle. On Windows, you cannot delete
    an open file. The sequence was:
        1. write bytes → tmp_path
        2. openpyxl.load_workbook(tmp_path)   ← opens ZipFile handle
        3. finally: os.unlink(tmp_path)        ← CRASH on Windows (file still open)
        4. workbook.close()                    ← never reached

Fix:
    Close the workbook BEFORE attempting to delete the temp file.
    Restructured into two try/finally blocks:
        Block 1 — open workbook, read all data, close workbook.
        Block 2 — delete temp file (now safe because workbook is closed).
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

MAX_ROWS_PER_SHEET = 500
MAX_COLS_PER_ROW = 50


class XlsxLoader(DocumentLoader):
    """Load and extract text from Excel (.xlsx) files using openpyxl."""

    @property
    def supported_mimetypes(self) -> List[str]:
        return [
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            "application/vnd.ms-excel",
        ]

    async def load_from_url(self, uri: str) -> Tuple[str, Dict[str, Any]]:
        if not self.validate_uri(uri):
            raise DocumentLoadError(f"Invalid URI scheme: {uri}")

        raw = await fetch_bytes_from_uri(uri)
        if not raw:
            raise CorruptDocumentError("Empty XLSX")

        try:
            import openpyxl
        except ImportError:
            raise DocumentLoadError("openpyxl is required; run: pip install openpyxl")

        # Write bytes to temp file.
        # delete=False — we need to close the handle before openpyxl opens it
        # (required on Windows to avoid WinError 32).
        tmp_path = None
        try:
            with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as tmp:
                tmp.write(raw)
                tmp_path = tmp.name
            # File handle closed here — openpyxl can now open it on Windows.
        except Exception as e:
            raise DocumentLoadError(f"Failed to write XLSX temp file: {e}") from e

        # ── Open workbook, read data, then close — all before temp file deletion ──
        parts: List[str] = []
        metadata: Dict[str, Any] = {
            "format": "xlsx",
            "loader": "openpyxl",
        }

        workbook = None
        try:
            workbook = await asyncio.to_thread(
                openpyxl.load_workbook,
                tmp_path,
                True,  # read_only
                True,  # data_only (return cell values, not formulas)
            )

            sheet_names = list(workbook.sheetnames or [])
            metadata["sheet_count"] = len(sheet_names)
            metadata["sheets"] = sheet_names

            for sheet_name in sheet_names:
                ws = workbook[sheet_name]
                rows_seen = 0
                sheet_lines: List[str] = []

                for row in ws.iter_rows(values_only=True):
                    if rows_seen >= MAX_ROWS_PER_SHEET:
                        break
                    values = [
                        "" if v is None else str(v).strip()
                        for v in row[:MAX_COLS_PER_ROW]
                    ]
                    if not any(values):
                        continue
                    sheet_lines.append(" | ".join(values))
                    rows_seen += 1

                if sheet_lines:
                    parts.append(
                        f"--- Sheet: {sheet_name} ---\n" + "\n".join(sheet_lines)
                    )
                metadata[f"sheet_{sheet_name}_rows_previewed"] = rows_seen

        except (DocumentLoadError, CorruptDocumentError):
            raise
        except Exception as e:
            raise CorruptDocumentError(f"Cannot parse XLSX: {e}") from e
        finally:
            # ── Always close workbook before touching the temp file ────────
            # openpyxl read_only mode holds a ZipFile handle.
            # On Windows, os.unlink() will raise WinError 32 if this is skipped.
            if workbook is not None:
                try:
                    workbook.close()
                except Exception:
                    pass

            # ── Now safe to delete the temp file ──────────────────────────
            if tmp_path and os.path.exists(tmp_path):
                try:
                    os.unlink(tmp_path)
                except OSError as unlink_err:
                    # Non-fatal on Windows if handle not fully released yet
                    logger.warning(
                        "[XlsxLoader] Could not delete temp file %s: %s",
                        tmp_path,
                        unlink_err,
                    )

        text = "\n\n".join(parts).strip()
        if not text:
            raise CorruptDocumentError("No content extracted from XLSX")

        logger.info(
            "[XlsxLoader] Extracted %d sheet(s), %d chars",
            metadata.get("sheet_count", 0),
            len(text),
        )
        return text, metadata
