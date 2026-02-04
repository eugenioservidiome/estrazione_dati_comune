"""
comune_extractor: Production-ready package for extracting data from Italian municipality websites.

Features:
- Focused web crawler with sitemap.xml and robots.txt support
- PDF download with SHA1 deduplication and SQLite catalog
- PyMuPDF primary extraction with pdfplumber fallback
- Automatic year detection from URLs and document content
- BM25 indexing for fast retrieval
- Optional LLM-based extraction with OpenAI API
- Comprehensive caching and audit trails
"""

__version__ = "2.0.0"

from .config import Config
from .pipeline import Pipeline

__all__ = ["Config", "Pipeline", "__version__"]
