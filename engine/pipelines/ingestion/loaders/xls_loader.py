"""Legacy XLS document loader (converts to XLSX via LibreOffice)."""

from __future__ import annotations

import logging
import asyncio
import os
import tempfile
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

MAX_ROWS_PER_SHEET = 500
MAX_COLS_PER_ROW = 50


class XlsLoader(DocumentLoader):
    """Load and extract text from legacy Excel (.xls) files."""

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

        raw = await fetch_bytes_from_uri(uri)
        if not raw:
            raise CorruptDocumentError("Empty XLS")

        converted_path: Path | None = None
        try:
            try:
                converted_path = convert_office_bytes_to_format(
                    raw=raw,
                    input_suffix=".xls",
                    output_suffix=".xlsx",
                    convert_to="xlsx",
                )
            except LibreOfficeNotAvailableError as e:
                raise DocumentLoadError(str(e)) from e
            except Exception as e:
                raise CorruptDocumentError(f"Cannot convert XLS to XLSX: {e}") from e

            try:
                import openpyxl
            except ImportError:
                raise DocumentLoadError("openpyxl is required for XLSX parsing")

            wb = await asyncio.to_thread(
                openpyxl.load_workbook,
                str(converted_path),
                True,   # read_only
                True,   # data_only
            )

        except DocumentLoadError:
            raise
        except CorruptDocumentError:
            raise
        except Exception as e:
            raise CorruptDocumentError(f"Cannot parse converted XLSX: {e}") from e
        finally:
            if converted_path and os.path.exists(converted_path):
                try:
                    os.unlink(converted_path)
                except Exception:
                    pass

        sheet_names = list(wb.sheetnames or [])
        metadata: Dict[str, Any] = {
            "format": "xls",
            "loader": "openpyxl (via LibreOffice conversion)",
            "sheet_count": len(sheet_names),
            "sheets": sheet_names,
        }

        parts: List[str] = []
        for sheet_name in sheet_names:
            ws = wb[sheet_name]
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
            wb.close()
        except Exception:
            pass

        text = "\n\n".join(parts).strip()
        if not text:
            raise CorruptDocumentError("No content extracted from converted XLSX")
        return text, metadata

