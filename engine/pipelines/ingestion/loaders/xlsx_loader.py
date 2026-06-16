"""XLSX document loader."""

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

MAX_ROWS_PER_SHEET = 500
MAX_COLS_PER_ROW = 50


class XlsxLoader(DocumentLoader):
    """Load and extract text from Excel (.xlsx) files."""

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

        tmp_path = None
        try:
            with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as tmp:
                tmp.write(raw)
                tmp_path = tmp.name
            workbook = await asyncio.to_thread(
                openpyxl.load_workbook,
                Path(tmp_path),
                True,   # read_only
                True,   # data_only
            )
        except DocumentLoadError:
            raise
        except Exception as e:
            raise CorruptDocumentError(f"Cannot parse XLSX: {e}") from e
        finally:
            if tmp_path and os.path.exists(tmp_path):
                os.unlink(tmp_path)

        sheet_names = list(workbook.sheetnames or [])
        metadata: Dict[str, Any] = {
            "format": "xlsx",
            "loader": "openpyxl",
            "sheet_count": len(sheet_names),
            "sheets": sheet_names,
        }
        parts: List[str] = []

        for sheet_name in sheet_names:
            ws = workbook[sheet_name]
            rows_seen = 0
            sheet_lines: List[str] = []
            for row in ws.iter_rows(values_only=True):
                if rows_seen >= MAX_ROWS_PER_SHEET:
                    break
                values = ["" if v is None else str(v).strip() for v in row[:MAX_COLS_PER_ROW]]
                if not any(values):
                    continue
                sheet_lines.append(" | ".join(values))
                rows_seen += 1

            if sheet_lines:
                parts.append(f"--- Sheet: {sheet_name} ---\n" + "\n".join(sheet_lines))
            metadata[f"sheet_{sheet_name}_rows_previewed"] = rows_seen

        try:
            workbook.close()
        except Exception:
            pass

        text = "\n\n".join(parts).strip()
        if not text:
            raise CorruptDocumentError("No content extracted from XLSX")
        return text, metadata

