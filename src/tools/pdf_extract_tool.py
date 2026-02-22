import logging
from pathlib import Path


def extract_text(pdf_path: Path) -> str:
    """Extract text from PDF using PyMuPDF, with fallback to pdfminer.six."""
    try:
        text = _extract_with_pymupdf(pdf_path)
    except Exception as e:
        logging.warning(f"PyMuPDF failed ({e}), trying pdfminer.six...")
        text = _extract_with_pdfminer(pdf_path)
    # Null bytes (\x00) in PDF text cause subprocess failures when the SDK
    # passes the prompt as a CLI argument — strip them at the source.
    return text.replace("\x00", "")


def _extract_with_pymupdf(pdf_path: Path) -> str:
    import fitz  # PyMuPDF
    doc = fitz.open(str(pdf_path))
    pages = []
    for page in doc:
        pages.append(page.get_text())
    doc.close()
    text = "\n".join(pages).strip()
    if not text:
        raise ValueError("PyMuPDF extracted empty text")
    return text


def _extract_with_pdfminer(pdf_path: Path) -> str:
    from pdfminer.high_level import extract_text as pdfminer_extract
    text = pdfminer_extract(str(pdf_path))
    if not text or not text.strip():
        raise ValueError("pdfminer.six extracted empty text")
    return text.strip()
