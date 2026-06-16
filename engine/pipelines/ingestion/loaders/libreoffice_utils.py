"""LibreOffice (soffice) helpers for converting legacy office formats.

We keep this isolated because it depends on an external binary (soffice),
which may be missing on some deployments.
"""

from __future__ import annotations

import logging
import os
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Final, Optional

logger = logging.getLogger(__name__)


class LibreOfficeNotAvailableError(RuntimeError):
    """Raised when `soffice` is not available in PATH."""


def convert_office_bytes_to_format(
    *,
    raw: bytes,
    input_suffix: str,
    output_suffix: str,
    convert_to: str,
    timeout_seconds: int = 120,
) -> Path:
    """Convert input bytes to an output file using `soffice --headless`.

    Args:
        raw: File bytes to convert
        input_suffix: e.g. ".doc"
        output_suffix: e.g. ".docx"
        convert_to: e.g. "docx" (LibreOffice convert-to target)
        timeout_seconds: command timeout

    Returns:
        Path to the converted file.

    Raises:
        LibreOfficeNotAvailableError: if `soffice` not found
        RuntimeError: conversion failed
    """
    soffice = shutil.which("soffice")
    if not soffice:
        raise LibreOfficeNotAvailableError(
            "`soffice` (LibreOffice) is not available on this server; cannot convert DOC/XLS/PPT legacy formats."
        )

    if not input_suffix.startswith("."):
        input_suffix = f".{input_suffix}"
    if not output_suffix.startswith("."):
        output_suffix = f".{output_suffix}"

    out_path: Optional[Path] = None

    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir_path = Path(tmpdir)
        in_file = tmpdir_path / f"input{input_suffix}"
        out_dir = tmpdir_path / "out"
        out_dir.mkdir(parents=True, exist_ok=True)

        in_file.write_bytes(raw)

        cmd: Final[list[str]] = [
            soffice,
            "--headless",
            "--nologo",
            "--nolockcheck",
            "--nodefault",
            "--nofirststartwizard",
            "--convert-to",
            convert_to,
            "--outdir",
            str(out_dir),
            str(in_file),
        ]

        logger.info("LibreOffice converting %s -> %s via %s", input_suffix, output_suffix, convert_to)
        try:
            subprocess.run(
                cmd,
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=timeout_seconds,
            )
        except subprocess.TimeoutExpired as e:
            raise RuntimeError(f"LibreOffice conversion timed out after {timeout_seconds}s") from e
        except subprocess.CalledProcessError as e:
            stderr = (e.stderr or b"").decode("utf-8", errors="replace")[:2000]
            raise RuntimeError(f"LibreOffice conversion failed: {stderr}") from e

        # LibreOffice typically writes: input.<output_ext> based on stem name.
        expected = out_dir / f"input{output_suffix}"
        if expected.exists():
            out_path = expected
        else:
            # Fallback: find any file with output extension.
            matches = list(out_dir.glob(f"*{output_suffix}"))
            if matches:
                out_path = matches[0]

        if not out_path or not out_path.exists():
            raise RuntimeError(
                f"LibreOffice conversion did not produce expected output {output_suffix}."
            )

        # We need to return a real file outside tempdir; copy it to a temp file.
        # Caller is responsible for deleting returned file.
        tmp = tempfile.NamedTemporaryFile(
            delete=False,
            suffix=output_suffix,
            prefix="ingest_convert_",
        )
        try:
            tmp.write(out_path.read_bytes())
            tmp.flush()
            return Path(tmp.name)
        finally:
            try:
                tmp.close()
            except Exception:
                pass

