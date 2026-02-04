"""Municipality data extraction package.

A robust package for extracting missing data from municipality CSV files
by crawling official websites and using TF-IDF document retrieval.
"""

__version__ = "1.0.0"

from .config import RunConfig
from .utils import setup_logging
from .crawler import WebCrawler
from .extractors import extract_text_from_html, extract_text_from_pdf
from .csv_io import load_csv_robust, detect_missing_cells, is_missing_cell
from .indexing import DocumentIndex, build_tfidf_index, search_documents
from .value_extraction import extract_value_from_text
from .pipeline import run_pipeline

__all__ = [
    # Configuration
    'RunConfig',
    
    # Utilities
    'setup_logging',
    
    # Crawling
    'WebCrawler',
    
    # Text extraction
    'extract_text_from_html',
    'extract_text_from_pdf',
    
    # CSV handling
    'load_csv_robust',
    'detect_missing_cells',
    'is_missing_cell',
    
    # Indexing
    'DocumentIndex',
    'build_tfidf_index',
    'search_documents',
    
    # Value extraction
    'extract_value_from_text',
    
    # Pipeline
    'run_pipeline',
]
