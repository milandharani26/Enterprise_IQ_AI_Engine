"""Legacy XLS document loader using xlrd (no LibreOffice required).

Root cause of original error:
    DocumentLoadError: `soffice` (LibreOffice) is not available on this server;
    cannot convert DOC/XLS/PPT legacy formats.

    The original loader converted .xls → .xlsx via LibreOffice (`soffice`).
    LibreOffice is not available on Windows dev machines or most cloud servers
    without explicit installation.

Fix:
    Read .xls files directly using `xlrd` — a pure-Python library that natively
    supports the legacy BIFF (.xls) format without any external tools.

    xlrd supports: .xls (BIFF 5–8), including Excel 97–2003 workbooks.
    It does NOT support .xlsx (use xlsx_loader.py for those).

Install requirement:
    pip install xlrd
    (xlrd >= 2.0 reads only .xls; that's exactly what we need here)
"""

from __future__ import annotations

import asyncio
import logging
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


def _extract_xls_from_bytes(raw: bytes) -> Tuple[str, Dict[str, Any]]:
    """
    Parse XLS bytes using xlrd and return (text, metadata).

    xlrd.open_workbook(file_contents=...) reads directly from bytes —
    no temp file needed, no LibreOffice, no file-locking issues on Windows.
    """
    try:
        import xlrd
    except ImportError:
        raise DocumentLoadError(
            "xlrd is required to read legacy .xls files; run: pip install xlrd"
        )

    try:
        wb = xlrd.open_workbook(file_contents=raw)
    except Exception as e:
        raise CorruptDocumentError(f"Cannot parse XLS: {e}") from e

    sheet_names = wb.sheet_names()
    metadata: Dict[str, Any] = {
        "format": "xls",
        "loader": "xlrd",
        "sheet_count": len(sheet_names),
        "sheets": sheet_names,
    }

    parts: List[str] = []

    for sheet_name in sheet_names:
        ws = wb.sheet_by_name(sheet_name)
        rows_seen = 0
        sheet_lines: List[str] = []

        for row_idx in range(ws.nrows):
            if rows_seen >= MAX_ROWS_PER_SHEET:
                break

            row_values = ws.row_values(row_idx, end_colx=MAX_COLS_PER_ROW)
            values = ["" if v is None else str(v).strip() for v in row_values]
            # Strip trailing float notation from integers (xlrd returns 1.0 for int 1)
            cleaned: List[str] = []
            for v in values:
                if v.endswith(".0") and v[:-2].lstrip("-").isdigit():
                    cleaned.append(v[:-2])
                else:
                    cleaned.append(v)

            if not any(cleaned):
                continue

            sheet_lines.append(" | ".join(cleaned))
            rows_seen += 1

        if sheet_lines:
            parts.append(f"--- Sheet: {sheet_name} ---\n" + "\n".join(sheet_lines))
        metadata[f"sheet_{sheet_name}_rows_previewed"] = rows_seen

    text = "\n\n".join(parts).strip()
    return text, metadata


class XlsLoader(DocumentLoader):
    """
    Load and extract text from legacy Excel (.xls) files using xlrd.

    Does NOT require LibreOffice or any system-level tools.
    Reads BIFF 5–8 format (.xls / Excel 97–2003) directly from bytes.
    """

    @property
    def supported_mimetypes(self) -> List[str]:
        return [
            "application/vnd.ms-excel",
            "application/x-msexcel",
            "application/vnd.ms-excel.sheet.macroEnabled.12",
        ]

    async def load_from_url(self, uri: str) -> Tuple[str, Dict[str, Any]]:
        if not self.validate_uri(uri):
            raise DocumentLoadError(f"Invalid URI scheme: {uri}")

        # Check dependency upfront with a clear message
        try:
            import xlrd  # noqa: F401
        except ImportError:
            raise DocumentLoadError(
                "xlrd is required to read legacy .xls files; run: pip install xlrd"
            )

        raw = await fetch_bytes_from_uri(uri)
        if not raw:
            raise CorruptDocumentError("Empty XLS")

        try:
            # xlrd reads from bytes in memory — no temp file, no WinError 32
            text, metadata = await asyncio.to_thread(_extract_xls_from_bytes, raw)
        except (DocumentLoadError, CorruptDocumentError):
            raise
        except Exception as e:
            raise CorruptDocumentError(f"XLS extraction failed: {e}") from e

        if not text:
            raise CorruptDocumentError("No content extracted from XLS")

        logger.info(
            "[XlsLoader] Extracted %d sheet(s), %d chars (via xlrd, no LibreOffice)",
            metadata.get("sheet_count", 0),
            len(text),
        )
        return text, metadata
