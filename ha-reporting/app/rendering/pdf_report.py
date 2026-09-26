from __future__ import annotations

import tempfile
from pathlib import Path

from weasyprint import HTML


def render_pdf_native(html: str, *, timeout_seconds: int = 120) -> Path:
    # WeasyPrint renders the already self-contained HTML/CSS locally. The
    # timeout argument is kept for API stability; rendering is synchronous.
    _ = timeout_seconds
    workdir = Path(tempfile.mkdtemp(prefix="ha-reporting-pdf-"))
    pdf_path = workdir / "report.pdf"
    try:
        HTML(string=html, base_url=str(workdir)).write_pdf(pdf_path)
    except Exception as exc:
        raise RuntimeError(f"Échec de génération PDF native: {exc}") from exc
    if not pdf_path.is_file() or pdf_path.stat().st_size <= 1000:
        raise RuntimeError("Échec de génération PDF native: fichier PDF vide ou incomplet")
    return pdf_path
