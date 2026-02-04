"""PDF text extraction with PyMuPDF primary, pdfplumber fallback, and disk caching."""

from pathlib import Path
from typing import Tuple, Optional, List, Dict, Any


def extract_text_pymupdf(pdf_path: Path) -> Tuple[str, int]:
    """Extract text using PyMuPDF (fitz). Returns (text, page_count)."""
    import fitz
    
    text_parts = []
    with fitz.open(pdf_path) as doc:
        page_count = len(doc)
        for page in doc:
            text_parts.append(page.get_text())
    
    return "\n\n".join(text_parts), page_count


def extract_text_per_page_pymupdf(pdf_path: Path) -> Tuple[List[str], int]:
    """Extract text per page using PyMuPDF (fitz). Returns (page_texts, page_count)."""
    import fitz
    
    page_texts = []
    with fitz.open(pdf_path) as doc:
        page_count = len(doc)
        for page in doc:
            page_texts.append(page.get_text())
    
    return page_texts, page_count


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


def extract_text_per_page_pdfplumber(pdf_path: Path) -> Tuple[List[str], int]:
    """Extract text per page using pdfplumber. Returns (page_texts, page_count)."""
    import pdfplumber
    
    page_texts = []
    with pdfplumber.open(pdf_path) as pdf:
        page_count = len(pdf.pages)
        for page in pdf.pages:
            page_text = page.extract_text()
            page_texts.append(page_text if page_text else "")
    
    return page_texts, page_count


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


def extract_text_per_page(pdf_path: Path) -> Tuple[List[str], int, str]:
    """
    Extract text per page from PDF with primary/fallback strategy.
    Returns (page_texts, page_count, extractor_name).
    """
    # Try PyMuPDF first (faster)
    try:
        page_texts, pages = extract_text_per_page_pymupdf(pdf_path)
        if any(text.strip() for text in page_texts):  # Only accept if we got actual text
            return page_texts, pages, "pymupdf"
    except Exception as e:
        pass
    
    # Fallback to pdfplumber
    try:
        page_texts, pages = extract_text_per_page_pdfplumber(pdf_path)
        return page_texts, pages, "pdfplumber"
    except Exception as e:
        raise RuntimeError(f"Failed to extract text from {pdf_path}: {e}")


def save_text(text: str, text_path: Path):
    """Save extracted text to disk."""
    text_path.parent.mkdir(parents=True, exist_ok=True)
    with open(text_path, 'w', encoding='utf-8') as f:
        f.write(text)


def save_page_texts(page_texts: List[str], text_dir: Path, sha1: str):
    """Save extracted page texts to disk as separate files."""
    text_dir.mkdir(parents=True, exist_ok=True)
    for page_no, page_text in enumerate(page_texts, start=1):
        page_path = text_dir / f"{sha1}_page_{page_no}.txt"
        with open(page_path, 'w', encoding='utf-8') as f:
            f.write(page_text)


def load_text(text_path: Path) -> Optional[str]:
    """Load text from disk cache."""
    if text_path.exists():
        with open(text_path, 'r', encoding='utf-8') as f:
            return f.read()
    return None


def load_page_texts(text_dir: Path, sha1: str, page_count: int) -> Optional[List[str]]:
    """Load page texts from disk cache."""
    page_texts = []
    for page_no in range(1, page_count + 1):
        page_path = text_dir / f"{sha1}_page_{page_no}.txt"
        if not page_path.exists():
            return None  # Missing page, need to re-extract
        with open(page_path, 'r', encoding='utf-8') as f:
            page_texts.append(f.read())
    return page_texts
