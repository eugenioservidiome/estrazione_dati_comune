"""Year detection from URL/filename and document content."""

import re
from pathlib import Path
from typing import Optional

# Valid year range for detection
MIN_VALID_YEAR = 1990
MAX_VALID_YEAR = 2030


def detect_year_from_url(url: str) -> Optional[int]:
    """Detect year from URL or filename using regex."""
    # Pattern: 4-digit year starting with 19 or 20, with flexible boundaries
    pattern = r'(?:^|[/_\-\s])(19\d{2}|20\d{2})(?:[/_\-\s.]|$)'
    matches = re.findall(pattern, url)
    
    if matches:
        # Return the most recent year if multiple found
        years = [int(y) for y in matches]
        # Filter to reasonable range
        valid_years = [y for y in years if MIN_VALID_YEAR <= y <= MAX_VALID_YEAR]
        if valid_years:
            return max(valid_years)
    
    return None


def detect_year_from_text(text: str, max_chars: int = 5000) -> Optional[int]:
    """Detect year from document text content."""
    # Limit text to avoid processing entire documents
    text = text[:max_chars]
    
    # Pattern: 4-digit year starting with 19 or 20
    pattern = r'\b(19\d{2}|20\d{2})\b'
    matches = re.findall(pattern, text)
    
    if matches:
        # Count occurrences of each year
        year_counts = {}
        for year_str in matches:
            year = int(year_str)
            # Filter to reasonable range
            if MIN_VALID_YEAR <= year <= MAX_VALID_YEAR:
                year_counts[year] = year_counts.get(year, 0) + 1
        
        if year_counts:
            # Return the most frequent year (or most recent if tie)
            return max(year_counts.items(), key=lambda x: (x[1], x[0]))[0]
    
    return None


def detect_year_from_filename(filename: str) -> Optional[int]:
    """Detect year from filename."""
    return detect_year_from_url(filename)


def extract_first_pages_text(pdf_path: Path, max_pages: int = 2) -> str:
    """
    Extract text from first N pages for year detection.
    Try PyMuPDF first, fallback to pdfplumber.
    """
    text = ""
    
    # Try PyMuPDF first
    try:
        import fitz  # PyMuPDF
        with fitz.open(pdf_path) as doc:
            for page_num in range(min(max_pages, len(doc))):
                page = doc[page_num]
                text += page.get_text()
        return text
    except Exception as e:
        pass
    
    # Fallback to pdfplumber
    try:
        import pdfplumber
        with pdfplumber.open(pdf_path) as pdf:
            for page_num in range(min(max_pages, len(pdf.pages))):
                page = pdf.pages[page_num]
                page_text = page.extract_text()
                if page_text:
                    text += page_text
        return text
    except Exception as e:
        pass
    
    return text


def detect_year_comprehensive(pdf_path: Path, url: str, filename: str) -> Optional[int]:
    """
    Comprehensive year detection:
    1. Try URL
    2. Try filename
    3. Extract first 2 pages and search text
    """
    # Try URL first
    year = detect_year_from_url(url)
    if year:
        return year
    
    # Try filename
    year = detect_year_from_filename(filename)
    if year:
        return year
    
    # Try document content
    try:
        text = extract_first_pages_text(pdf_path, max_pages=2)
        if text:
            year = detect_year_from_text(text)
            if year:
                return year
    except Exception:
        pass
    
    return None
