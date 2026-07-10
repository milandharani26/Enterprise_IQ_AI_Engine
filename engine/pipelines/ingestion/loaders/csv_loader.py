"""CSV document loader — pure Python stdlib, no LlamaIndex required.

Root cause of the error chain:
─────────────────────────────────────────────────────────────────────────────
The original csv_loader.py imported LlamaIndex SimpleCSVReader at the top of
load_from_url():

    from llama_index.readers.file import SimpleCSVReader

If llama-index-readers-file is not installed (or the package is missing), this
raises ImportError which bubbles up as a DocumentLoadError.

BUT — the loader then immediately re-parsed the same file using Python's built-in
csv module anyway. SimpleCSVReader was doing nothing useful; the final markdown
table was built entirely from stdlib csv.reader(). The LlamaIndex call was dead
weight that introduced a hard dependency and a crash path.

Fix:
    Remove SimpleCSVReader entirely. Parse with stdlib csv only.
    No new packages required — csv, io, chardet (optional, already present) only.
─────────────────────────────────────────────────────────────────────────────
"""

import csv
import io
import logging
from typing import Any, Dict, List, Tuple

from engine.pipelines.ingestion.exceptions import (
    CorruptDocumentError,
    DocumentLoadError,
)
from engine.pipelines.ingestion.loaders.base_loader import DocumentLoader
from engine.pipelines.ingestion.loaders.fetch import fetch_bytes_from_uri

logger = logging.getLogger(__name__)

MAX_ROWS_PREVIEW = 100


class CsvLoader(DocumentLoader):
    """
    Load and extract text from CSV files using Python's built-in csv module.

    No LlamaIndex, no torch, no external dependencies beyond chardet (optional).
    Renders output as a markdown table for clean RAG chunking.
    """

    @property
    def supported_mimetypes(self) -> List[str]:
        return [
            "text/csv",
            "application/csv",
            "text/comma-separated-values",
        ]

    async def load_from_url(self, uri: str) -> Tuple[str, Dict[str, Any]]:
        if not self.validate_uri(uri):
            raise DocumentLoadError(f"Invalid URI scheme: {uri}")

        raw = await fetch_bytes_from_uri(uri)
        if not raw:
            return "", {"format": "csv", "rows": 0, "columns": 0}

        # ── Encoding detection ────────────────────────────────────────────────
        detected_encoding = "utf-8"
        try:
            raw.decode("utf-8")
        except UnicodeDecodeError:
            try:
                import chardet

                result = chardet.detect(raw)
                detected_encoding = result.get("encoding") or "utf-8"
            except Exception:
                detected_encoding = "utf-8"

        try:
            text_content = raw.decode(detected_encoding, errors="replace")
        except Exception:
            text_content = raw.decode("utf-8", errors="replace")
            detected_encoding = "utf-8 (fallback)"

        # ── Dialect sniff ─────────────────────────────────────────────────────
        try:
            dialect = csv.Sniffer().sniff(text_content[:8192], delimiters=",\t;")
        except csv.Error:
            dialect = csv.excel  # safe default: comma-separated, double-quote

        # ── Parse ─────────────────────────────────────────────────────────────
        try:
            reader = csv.reader(io.StringIO(text_content), dialect)
            rows = [r for r in reader if any(cell.strip() for cell in r)]
        except Exception as e:
            raise CorruptDocumentError(f"Cannot parse CSV: {e}") from e

        metadata: Dict[str, Any] = {
            "format": "csv",
            "loader": "stdlib-csv",
            "encoding": detected_encoding,
            "rows": 0,
            "columns": 0,
        }

        if not rows:
            return "", metadata

        header = rows[0]
        data_rows = rows[1:]
        num_cols = len(header)
        num_rows = len(data_rows)

        metadata["rows"] = num_rows
        metadata["columns"] = num_cols
        metadata["column_names"] = [c.strip() for c in header]

        # ── Render as markdown table ───────────────────────────────────────────
        # Markdown tables are the best format for RAG: each row is human-readable
        # and chunking preserves the column context in every chunk.
        lines: List[str] = [
            "| " + " | ".join(str(c).strip() for c in header) + " |",
            "| " + " | ".join("---" for _ in header) + " |",
        ]

        display_rows = data_rows[:MAX_ROWS_PREVIEW]
        for row in display_rows:
            # Pad short rows, truncate long rows to match header column count
            padded = (row + [""] * num_cols)[:num_cols]
            lines.append("| " + " | ".join(str(c).strip() for c in padded) + " |")

        table_text = "\n".join(lines)

        if num_rows > MAX_ROWS_PREVIEW:
            omitted = num_rows - MAX_ROWS_PREVIEW
            table_text += f"\n\n[... {omitted} more rows not shown ...]"
            metadata["preview"] = True
            metadata["rows_shown"] = MAX_ROWS_PREVIEW

        logger.info(
            "[CsvLoader] Parsed %d rows x %d cols (encoding=%s)",
            num_rows,
            num_cols,
            detected_encoding,
        )
        return table_text, metadata
