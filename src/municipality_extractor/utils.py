"""Utility functions and helpers."""

import hashlib
import logging
import re
from typing import Optional
from urllib.parse import urlparse, urljoin, urlunparse


def setup_logging(level: int = logging.INFO) -> None:
    """Configure logging with proper formatting.
    
    Args:
        level: Logging level (default: INFO)
    """
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )


def url_to_cache_key(url: str) -> str:
    """Convert URL to a safe cache key using SHA1 hash.
    
    Args:
        url: URL to hash
        
    Returns:
        40-character hex string (SHA1 hash)
    """
    return hashlib.sha1(url.encode('utf-8')).hexdigest()


def normalize_url(url: str, base_url: str = "") -> Optional[str]:
    """Normalize URL by removing fragments, handling relative URLs, etc.
    
    Args:
        url: URL to normalize
        base_url: Base URL for resolving relative URLs
        
    Returns:
        Normalized URL or None if invalid
    """
    if not url:
        return None
    
    url = url.strip()
    
    # Filter out non-http(s) schemes
    if url.startswith(('mailto:', 'tel:', 'javascript:', 'data:', '#')):
        return None
    
    # Handle relative URLs
    if base_url and not url.startswith(('http://', 'https://')):
        url = urljoin(base_url, url)
    
    # Parse URL
    try:
        parsed = urlparse(url)
    except Exception:
        return None
    
    # Must have scheme and netloc
    if not parsed.scheme or not parsed.netloc:
        return None
    
    # Only http(s)
    if parsed.scheme not in ('http', 'https'):
        return None
    
    # Rebuild without fragment
    normalized = urlunparse((
        parsed.scheme,
        parsed.netloc,
        parsed.path,
        parsed.params,
        parsed.query,
        ''  # Remove fragment
    ))
    
    # Normalize trailing slashes for directories
    # If path ends with / or has no extension, keep/add trailing slash
    if normalized.endswith('/'):
        pass
    elif '.' not in normalized.split('/')[-1]:
        # No extension, likely a directory
        normalized += '/'
    
    return normalized


def same_domain(url1: str, url2: str) -> bool:
    """Check if two URLs are on the same domain.
    
    Args:
        url1: First URL
        url2: Second URL
        
    Returns:
        True if same domain (netloc), False otherwise
    """
    try:
        netloc1 = urlparse(url1).netloc
        netloc2 = urlparse(url2).netloc
        return netloc1 == netloc2
    except Exception:
        return False


def is_useful_extension(url: str) -> bool:
    """Check if URL has a useful extension for text extraction.
    
    Args:
        url: URL to check
        
    Returns:
        True if extension is useful or no extension, False for binary/media files
    """
    # Extensions we explicitly want
    useful_exts = {'.html', '.htm', '.pdf', '.txt', '.php', '.asp', '.aspx', '.jsp'}
    
    # Extensions we want to skip
    skip_exts = {
        '.jpg', '.jpeg', '.png', '.gif', '.svg', '.ico',  # Images
        '.css', '.js',  # Assets
        '.zip', '.rar', '.tar', '.gz', '.7z',  # Archives
        '.mp3', '.mp4', '.avi', '.mov', '.wmv',  # Media
        '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx',  # Office (need special handling)
        '.xml', '.json',  # Data formats (usually not useful for text)
    }
    
    path = urlparse(url).path.lower()
    
    # Check for useful extensions
    for ext in useful_exts:
        if path.endswith(ext):
            return True
    
    # Check for skip extensions
    for ext in skip_exts:
        if path.endswith(ext):
            return False
    
    # If no recognized extension, assume it's useful (could be a page without extension)
    return True


def parse_italian_number(text: str) -> Optional[float]:
    """Parse Italian-formatted number (1.234,56) to float.
    
    Handles:
    - Thousands separator: . (dot)
    - Decimal separator: , (comma)
    - Percentages: 12,5% → 12.5
    - Currency: €1.234,56 → 1234.56
    - Signs: +/-
    
    Args:
        text: String containing Italian-formatted number
        
    Returns:
        Parsed float or None if invalid
    """
    if not text:
        return None
    
    # Clean the text
    text = text.strip()
    
    # Remove currency symbols
    text = re.sub(r'[€$£]', '', text)
    
    # Handle percentage
    is_percentage = '%' in text
    text = text.replace('%', '')
    
    # Clean whitespace
    text = text.strip()
    
    # Pattern for Italian number: optional sign, digits with optional . as thousands separator,
    # optional , as decimal separator
    pattern = r'^([+-]?)(\d{1,3}(?:\.\d{3})*|\d+)(?:,(\d+))?$'
    match = re.match(pattern, text)
    
    if not match:
        return None
    
    sign = match.group(1)
    integer_part = match.group(2)
    decimal_part = match.group(3) or '0'
    
    # Remove thousands separators
    integer_part = integer_part.replace('.', '')
    
    # Build float
    try:
        value = float(f"{integer_part}.{decimal_part}")
        
        if sign == '-':
            value = -value
        
        # Don't convert percentages here - keep the raw value
        # The caller can decide how to interpret it
        
        return value
    except ValueError:
        return None


def extract_year_from_text(text: str, valid_years: Optional[list] = None) -> Optional[int]:
    """Extract a year from text.
    
    Args:
        text: Text to search for year
        valid_years: List of valid years to search for (optional)
        
    Returns:
        Found year or None
    """
    if not text:
        return None
    
    # Look for 4-digit years (2000-2099)
    year_pattern = r'\b(20\d{2})\b'
    matches = re.findall(year_pattern, text)
    
    if not matches:
        return None
    
    years = [int(m) for m in matches]
    
    # If valid_years specified, filter to those
    if valid_years:
        years = [y for y in years if y in valid_years]
    
    if not years:
        return None
    
    # Return the first match
    return years[0]
