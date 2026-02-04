"""PDF text extraction with PyMuPDF primary, pdfplumber fallback, and disk caching."""

from pathlib import Path
from typing import Tuple, Optional


def extract_text_pymupdf(pdf_path: Path) -> Tuple[str, int]:
    """Extract text using PyMuPDF (fitz). Returns (text, page_count)."""
    import fitz
    
    text_parts = []
    with fitz.open(pdf_path) as doc:
        page_count = len(doc)
        for page in doc:
            text_parts.append(page.get_text())
    
    return "\n\n".join(text_parts), page_count


def extract_text_pdfplumber(pdf_path: Path) -> Tuple[str, int]:
    """Extract text using pdfplumber as fallback. Returns (text, page_count)."""
    import pdfplumber
    
    text_parts = []
    with pdfplumber.open(pdf_path) as pdf:
        page_count = len(pdf.pages)
        for page in pdf.pages:
            page_text = page.extract_text()
            if page_text:
                text_parts.append(page_text)
    
    return "\n\n".join(text_parts), page_count


def extract_text(pdf_path: Path) -> Tuple[str, int, str]:
    """
    Extract text from PDF with primary/fallback strategy.
    Returns (text, page_count, extractor_name).
    """
    # Try PyMuPDF first (faster)
    try:
        text, pages = extract_text_pymupdf(pdf_path)
        if text.strip():  # Only accept if we got actual text
            return text, pages, "pymupdf"
    except Exception as e:
        pass
    
    # Fallback to pdfplumber
    try:
        text, pages = extract_text_pdfplumber(pdf_path)
        return text, pages, "pdfplumber"
    except Exception as e:
        raise RuntimeError(f"Failed to extract text from {pdf_path}: {e}")


def save_text(text: str, text_path: Path):
    """Save extracted text to disk."""
    text_path.parent.mkdir(parents=True, exist_ok=True)
    with open(text_path, 'w', encoding='utf-8') as f:
        f.write(text)


def load_text(text_path: Path) -> Optional[str]:
    """Load text from disk cache."""
    if text_path.exists():
        with open(text_path, 'r', encoding='utf-8') as f:
            return f.read()
    return None
