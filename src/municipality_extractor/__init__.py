"""Municipality data extraction package.

A robust package for extracting missing data from municipality CSV files
by crawling official websites and using TF-IDF document retrieval.
"""

__version__ = "1.0.0"

from .config import RunConfig
from .crawler import WebCrawler
from .extractors import extract_text_from_html, extract_text_from_pdf

__all__ = [
    'RunConfig',
    'WebCrawler',
    'extract_text_from_html',
    'extract_text_from_pdf',
]
