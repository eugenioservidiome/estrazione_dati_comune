"""Text extraction from HTML and PDF documents."""

import logging
from typing import Optional

logger = logging.getLogger(__name__)


def extract_text_from_html(html_content: bytes, url: str = "") -> str:
    """Extract text from HTML using trafilatura with BeautifulSoup fallback.
    
    Args:
        html_content: HTML content bytes
        url: URL for logging
        
    Returns:
        Extracted text (empty string if failed)
    """
    if not html_content:
        return ""
    
    try:
        # Try trafilatura first (better at removing boilerplate)
        import trafilatura
        
        text = trafilatura.extract(
            html_content,
            include_comments=False,
            include_tables=True,
            no_fallback=False
        )
        
        if text and len(text.strip()) > 50:
            return text.strip()
    except Exception as e:
        logger.debug(f"Trafilatura failed for {url}: {e}")
    
    # Fallback to BeautifulSoup
    try:
        from bs4 import BeautifulSoup
        
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Remove script and style elements
        for script in soup(['script', 'style', 'nav', 'header', 'footer']):
            script.decompose()
        
        # Get text
        text = soup.get_text(separator=' ', strip=True)
        
        # Clean up whitespace
        lines = (line.strip() for line in text.splitlines())
        chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
        text = ' '.join(chunk for chunk in chunks if chunk)
        
        return text.strip()
    except Exception as e:
        logger.warning(f"BeautifulSoup extraction failed for {url}: {e}")
        return ""


def extract_text_from_pdf(pdf_content: bytes, pdf_path: str = "") -> str:
    """Extract text from PDF using pdfplumber.
    
    Args:
        pdf_content: PDF content bytes
        pdf_path: Path or URL for logging
        
    Returns:
        Extracted text (empty string if failed or no text)
    """
    if not pdf_content:
        return ""
    
    try:
        import pdfplumber
        import io
        
        text_parts = []
        
        with pdfplumber.open(io.BytesIO(pdf_content)) as pdf:
            for page_num, page in enumerate(pdf.pages, 1):
                try:
                    page_text = page.extract_text()
                    if page_text:
                        text_parts.append(page_text)
                except Exception as e:
                    logger.debug(f"Could not extract text from page {page_num} of {pdf_path}: {e}")
                    continue
        
        text = '\n\n'.join(text_parts)
        
        if not text.strip():
            logger.debug(f"No text extracted from PDF: {pdf_path}")
            return ""
        
        return text.strip()
    except Exception as e:
        logger.warning(f"PDF extraction failed for {pdf_path}: {e}")
        return ""


def extract_text_with_cache(url: str, content: bytes, content_type: str, 
                            cache_dir: Optional[str] = None) -> str:
    """Extract text from content with optional caching.
    
    Args:
        url: Document URL
        content: Document content bytes
        content_type: 'html' or 'pdf'
        cache_dir: Directory to cache extracted text (optional)
        
    Returns:
        Extracted text
    """
    from pathlib import Path
    from .utils import url_to_cache_key
    
    # Check cache first
    if cache_dir:
        cache_path = Path(cache_dir) / f"{url_to_cache_key(url)}.txt"
        if cache_path.exists():
            try:
                with open(cache_path, 'r', encoding='utf-8') as f:
                    text = f.read()
                logger.debug(f"Loaded text from cache: {url}")
                return text
            except Exception as e:
                logger.debug(f"Error loading text cache for {url}: {e}")
    
    # Extract text
    if content_type == 'pdf':
        text = extract_text_from_pdf(content, url)
    else:
        text = extract_text_from_html(content, url)
    
    # Save to cache
    if cache_dir and text:
        try:
            cache_path = Path(cache_dir) / f"{url_to_cache_key(url)}.txt"
            with open(cache_path, 'w', encoding='utf-8') as f:
                f.write(text)
            logger.debug(f"Saved text to cache: {url}")
        except Exception as e:
            logger.debug(f"Error saving text cache for {url}: {e}")
    
    return text
