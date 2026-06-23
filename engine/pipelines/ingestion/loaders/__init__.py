"""Document loaders: format-specific parsers (PDF, DOCX, XLSX, CSV, TXT, HTML, JSON, PPTX).

Bug fixed in register_all_loaders():
─────────────────────────────────────────────────────────────────────────────
BUG 1 — Duplicate MIME type registration (silent overwrite):
    "application/vnd.ms-excel" was registered TWICE:
        1st → XlsxLoader  (inside the xlsx block)
        2nd → XlsLoader   (inside the xls block, overwrites the first)

    Result: any file detected as "application/vnd.ms-excel" — including .xlsx
    files that browsers sometimes report with this MIME — was routed to XlsLoader,
    which tried to read it as a legacy BIFF .xls file and raised:
        CorruptDocumentError: Cannot parse XLS: Unsupported format, or corrupt
        file: Expected BOF record; found b'Name ,Nu'
    (The b'Name ,Nu' is the start of a CSV header — the CSV was routed here.)

    Fix: "application/vnd.ms-excel" belongs ONLY to XlsLoader (true .xls files).
    XlsxLoader registers only its own unambiguous MIME type.

BUG 2 — CSV content-type aliases not registered:
    Windows browsers and some HTTP servers send CSV files with these content types
    instead of "text/csv":
        - "application/csv"
        - "text/comma-separated-values"
        - "application/octet-stream" (generic binary fallback)
    None of these were registered, so CSV files from Windows clients silently fell
    through to the extension-sniff fallback in _detect_mime_type(), and in some
    cases landed on the wrong loader.

    Fix: Register all common CSV MIME aliases → CsvLoader.
─────────────────────────────────────────────────────────────────────────────
"""

from .base_loader import DocumentLoader
from .registry import LoaderRegistry

# Registration is done in register_all_loaders() called at app startup.
from .pdf_loader import PDFLoader
from .docx_loader import DocxLoader
from .xlsx_loader import XlsxLoader
from .csv_loader import CsvLoader
from .txt_loader import TxtLoader
from .html_loader import HtmlLoader
from .json_loader import JsonLoader
from .pptx_loader import PptxLoader
from .doc_loader import DocLoader
from .xls_loader import XlsLoader
from .ppt_loader import PptLoader


def register_all_loaders() -> None:
    """Register all document loaders with the registry. Call on app startup."""

    # ── PDF ───────────────────────────────────────────────────────────────────
    LoaderRegistry.register(["application/pdf"], PDFLoader)

    # ── Word DOCX ─────────────────────────────────────────────────────────────
    LoaderRegistry.register(
        ["application/vnd.openxmlformats-officedocument.wordprocessingml.document"],
        DocxLoader,
    )

    # ── Word DOC (legacy) ─────────────────────────────────────────────────────
    LoaderRegistry.register(
        ["application/msword", "application/vnd.ms-word", "application/x-msword"],
        DocLoader,
    )

    # ── Excel XLSX ────────────────────────────────────────────────────────────
    # IMPORTANT: do NOT include "application/vnd.ms-excel" here.
    # That MIME type belongs to legacy .xls files (registered below under XlsLoader).
    # Registering it here AND there causes a silent overwrite — whichever block runs
    # last wins, and the other loader becomes unreachable for that MIME type.
    LoaderRegistry.register(
        ["application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"],
        XlsxLoader,
    )

    # ── Excel XLS (legacy) ────────────────────────────────────────────────────
    # "application/vnd.ms-excel" is the correct MIME for .xls only.
    # xlrd reads these directly from bytes — no LibreOffice required.
    LoaderRegistry.register(
        [
            "application/vnd.ms-excel",
            "application/x-msexcel",
            "application/vnd.ms-excel.sheet.macroEnabled.12",
        ],
        XlsLoader,
    )

    # ── CSV ───────────────────────────────────────────────────────────────────
    # Register all common CSV MIME aliases:
    # - "text/csv"                      standard RFC 4180
    # - "application/csv"               sent by some Windows/Excel clients
    # - "text/comma-separated-values"   older convention, still used by some tools
    # Note: "application/octet-stream" is intentionally NOT registered here because
    # it's a generic fallback used for many binary formats — routing it to CsvLoader
    # would break binary uploads. The _detect_mime_type() extension sniff handles it.
    LoaderRegistry.register(
        [
            "text/csv",
            "application/csv",
            "text/comma-separated-values",
        ],
        CsvLoader,
    )

    # ── Plain text / Markdown ─────────────────────────────────────────────────
    LoaderRegistry.register(["text/plain", "text/markdown"], TxtLoader)

    # ── HTML ──────────────────────────────────────────────────────────────────
    LoaderRegistry.register(["text/html", "application/xhtml+xml"], HtmlLoader)

    # ── JSON ──────────────────────────────────────────────────────────────────
    LoaderRegistry.register(["application/json", "text/json"], JsonLoader)

    # ── PowerPoint PPTX ───────────────────────────────────────────────────────
    LoaderRegistry.register(
        ["application/vnd.openxmlformats-officedocument.presentationml.presentation"],
        PptxLoader,
    )

    # ── PowerPoint PPT (legacy) ───────────────────────────────────────────────
    LoaderRegistry.register(
        ["application/vnd.ms-powerpoint", "application/x-mspowerpoint"],
        PptLoader,
    )


__all__ = [
    "DocumentLoader",
    "LoaderRegistry",
    "register_all_loaders",
    "PDFLoader",
    "DocxLoader",
    "XlsxLoader",
    "CsvLoader",
    "TxtLoader",
    "HtmlLoader",
    "JsonLoader",
    "DocLoader",
    "XlsLoader",
    "PptLoader",
    "PptxLoader",
]
