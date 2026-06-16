"""Document loaders: format-specific parsers (PDF, DOCX, XLSX, CSV, TXT, HTML, JSON, PPTX)."""

from .base_loader import DocumentLoader
from .registry import LoaderRegistry

# Registration is done in register_all_loaders() called at app startup.
# Import loader classes for registration:
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
    LoaderRegistry.register(["application/pdf"], PDFLoader)
    LoaderRegistry.register(
        ["application/vnd.openxmlformats-officedocument.wordprocessingml.document"],
        DocxLoader,
    )
    LoaderRegistry.register(
        [
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            "application/vnd.ms-excel",
        ],
        XlsxLoader,
    )
    LoaderRegistry.register(["text/csv"], CsvLoader)
    LoaderRegistry.register(["text/plain", "text/markdown"], TxtLoader)
    LoaderRegistry.register(["text/html", "application/xhtml+xml"], HtmlLoader)
    LoaderRegistry.register(["application/json", "text/json"], JsonLoader)
    LoaderRegistry.register(
        ["application/msword", "application/vnd.ms-word", "application/x-msword"],
        DocLoader,
    )
    LoaderRegistry.register(
        ["application/vnd.ms-excel", "application/x-msexcel", "application/vnd.ms-excel.sheet.macroEnabled.12"],
        XlsLoader,
    )
    LoaderRegistry.register(
        ["application/vnd.ms-powerpoint", "application/x-mspowerpoint"],
        PptLoader,
    )
    LoaderRegistry.register(
        ["application/vnd.openxmlformats-officedocument.presentationml.presentation"],
        PptxLoader,
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
