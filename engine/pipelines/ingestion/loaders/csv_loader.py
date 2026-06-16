"""CSV document loader using LlamaIndex SimpleCSVReader."""

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

MAX_ROWS_PREVIEW = 100


class CsvLoader(DocumentLoader):
    """
    Load and extract text from CSV files using LlamaIndex SimpleCSVReader.

    LlamaIndex SimpleCSVReader reads CSV rows as structured text.
    Falls back to custom markdown-table rendering for large files to preserve
    readability in chunked retrieval.
    """

    @property
    def supported_mimetypes(self) -> List[str]:
        return ["text/csv"]

    async def load_from_url(self, uri: str) -> Tuple[str, Dict[str, Any]]:
        if not self.validate_uri(uri):
            raise DocumentLoadError(f"Invalid URI scheme: {uri}")

        raw = await fetch_bytes_from_uri(uri)
        if not raw:
            return "", {"format": "csv", "rows": 0, "columns": 0}

        # Decode bytes (handle encoding)
        detected_encoding = "utf-8"
        try:
            raw.decode("utf-8")
        except UnicodeDecodeError:
            try:
                import chardet
                result = chardet.detect(raw)
                detected_encoding = result.get("encoding") or "utf-8"
                raw = raw.decode(detected_encoding).encode("utf-8")
            except Exception:
                raw = raw.decode("utf-8", errors="replace").encode("utf-8")
                detected_encoding = "utf-8 (fallback)"

        try:
            from llama_index.readers.file import SimpleCSVReader
        except ImportError:
            raise DocumentLoadError(
                "llama-index-readers-file is required; run: pip install llama-index-readers-file"
            )

        tmp_path = None
        try:
            with tempfile.NamedTemporaryFile(suffix=".csv", delete=False, mode="wb") as tmp:
                tmp.write(raw)
                tmp_path = tmp.name

            reader = SimpleCSVReader(encoding=detected_encoding)
            docs = await asyncio.to_thread(reader.load_data, Path(tmp_path))
        except DocumentLoadError:
            raise
        except Exception as e:
            raise CorruptDocumentError(f"Cannot parse CSV: {e}") from e
        finally:
            if tmp_path and os.path.exists(tmp_path):
                os.unlink(tmp_path)

        if not docs:
            return "", {"format": "csv", "rows": 0, "columns": 0}

        # LlamaIndex SimpleCSVReader returns row-level Documents
        # Reconstruct as markdown table for better chunk retrieval
        import csv
        import io

        text_content = raw.decode("utf-8")
        try:
            import csv as csv_mod
            dialect = csv_mod.Sniffer().sniff(text_content[:8192], delimiters=",\t;")
        except csv.Error:
            import csv as csv_mod
            dialect = csv_mod.excel

        reader_obj = csv.reader(io.StringIO(text_content), dialect)
        rows = list(reader_obj)

        metadata: Dict[str, Any] = {
            "format": "csv",
            "loader": "llama_index.SimpleCSVReader",
            "encoding": detected_encoding,
            "rows": 0,
            "columns": 0,
        }

        if not rows:
            return "", metadata

        header = rows[0]
        num_cols = len(header)
        num_rows = len(rows) - 1
        metadata["rows"] = num_rows
        metadata["columns"] = num_cols
        metadata["column_names"] = header
        metadata["row_index"] = list(range(num_rows))  # LlamaIndex-style metadata

        lines = [
            "| " + " | ".join(str(c) for c in header) + " |",
            "| " + " | ".join("---" for _ in header) + " |",
        ]
        display_rows = rows[1:] if num_rows <= MAX_ROWS_PREVIEW else rows[1: MAX_ROWS_PREVIEW + 1]
        for r in display_rows:
            padded = (r + [""] * num_cols)[:num_cols]
            lines.append("| " + " | ".join(str(c) for c in padded) + " |")

        table_text = "\n".join(lines)
        if num_rows > MAX_ROWS_PREVIEW:
            table_text += f"\n\n[... {num_rows - MAX_ROWS_PREVIEW} more rows ...]"
            metadata["preview"] = True
            metadata["rows_shown"] = MAX_ROWS_PREVIEW

        return table_text, metadata
