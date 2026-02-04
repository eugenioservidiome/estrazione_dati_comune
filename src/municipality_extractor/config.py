"""Configuration management for municipality data extraction."""

from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional
from urllib.parse import urlparse
import logging

logger = logging.getLogger(__name__)


@dataclass
class RunConfig:
    """Configuration for a single extraction run.
    
    Attributes:
        base_url: Municipality website URL (will be normalized to https with trailing slash)
        comune: Municipality name (optional, for logging/output naming)
        years_to_fill: List of years to extract data for
        allow_external_official: Whether to include external official sources (ISTAT, MEF, etc.)
        input_dir: Directory containing input CSV files
        output_dir: Directory for output files (_filled.csv, sources, queries, report)
        cache_dir: Directory for caching downloaded HTML/PDF and extracted text
        max_pages: Maximum number of pages to crawl
        max_depth: Maximum crawl depth from seed URL (None = unlimited)
        max_queue_size: Maximum URLs in crawl queue (prevents runaway crawling)
        max_pdf_mb: Maximum PDF size in MB to download
        politeness_delay: Seconds to wait between requests
        request_timeout: HTTP request timeout in seconds
        respect_robots: Whether to respect robots.txt
        user_agent: User agent string for HTTP requests
        max_tfidf_features: Maximum features for TF-IDF vectorizer
        ngram_range: N-gram range for TF-IDF (min, max)
        top_k_queries: Number of top queries to use per cell
        context_window_chars: Characters of context around extracted value
        min_keywords_for_extraction: Minimum keyword matches required to extract value
    """
    
    base_url: str
    comune: Optional[str] = None
    years_to_fill: List[int] = field(default_factory=lambda: [2023, 2024])
    allow_external_official: bool = False
    
    # Directories
    input_dir: Path = field(default_factory=lambda: Path("input"))
    output_dir: Path = field(default_factory=lambda: Path("output"))
    cache_dir: Optional[Path] = None  # Will default to output_dir/cache
    
    # Crawling limits
    max_pages: int = 500
    max_depth: Optional[int] = None
    max_queue_size: int = 5000
    max_pdf_mb: float = 50.0
    
    # Crawling behavior
    politeness_delay: float = 0.5
    request_timeout: int = 30
    respect_robots: bool = True
    user_agent: str = "MunicipalityDataExtractor/1.0 (civic-tech; +https://github.com/eugenioservidiome/estrazione_dati_comune)"
    
    # TF-IDF parameters
    max_tfidf_features: int = 5000
    ngram_range: tuple = (1, 3)
    top_k_queries: int = 10
    
    # Value extraction
    context_window_chars: int = 500
    min_keywords_for_extraction: int = 1
    
    # Internal fields (computed)
    domain: str = field(init=False)
    normalized_base_url: str = field(init=False)
    
    def __post_init__(self):
        """Validate and normalize configuration."""
        # Normalize base_url
        self.normalized_base_url = self._normalize_base_url(self.base_url)
        
        # Extract domain
        parsed = urlparse(self.normalized_base_url)
        self.domain = parsed.netloc
        
        if not self.domain:
            raise ValueError(f"Could not extract domain from base_url: {self.base_url}")
        
        # Ensure https
        if parsed.scheme != 'https':
            logger.warning(f"Base URL is not HTTPS: {self.base_url}. Proceeding with {parsed.scheme}://")
        
        # Convert string paths to Path objects
        if isinstance(self.input_dir, str):
            self.input_dir = Path(self.input_dir)
        if isinstance(self.output_dir, str):
            self.output_dir = Path(self.output_dir)
        
        # Set default cache_dir if not specified
        if self.cache_dir is None:
            self.cache_dir = self.output_dir / "cache"
        elif isinstance(self.cache_dir, str):
            self.cache_dir = Path(self.cache_dir)
        
        # Create directories if they don't exist
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        # Validate years
        if not self.years_to_fill:
            raise ValueError("years_to_fill cannot be empty")
        
        for year in self.years_to_fill:
            if not isinstance(year, int) or year < 2000 or year > 2100:
                raise ValueError(f"Invalid year: {year}. Must be integer between 2000 and 2100")
        
        logger.info(f"Configuration initialized for {self.domain}")
        logger.info(f"Years to fill: {self.years_to_fill}")
        logger.info(f"Output dir: {self.output_dir}")
        logger.info(f"Cache dir: {self.cache_dir}")
    
    @staticmethod
    def _normalize_base_url(url: str) -> str:
        """Normalize URL to https with trailing slash.
        
        Args:
            url: Raw URL from user
            
        Returns:
            Normalized URL with https:// and trailing slash
        """
        url = url.strip()
        
        # Add scheme if missing
        if not url.startswith(('http://', 'https://')):
            url = 'https://' + url
        
        # Parse and rebuild
        parsed = urlparse(url)
        
        # Ensure path has trailing slash for base URLs
        path = parsed.path
        if not path or path == '/':
            path = '/'
        elif not path.endswith('/'):
            # Only add trailing slash if it looks like a directory (no file extension)
            if '.' not in path.split('/')[-1]:
                path += '/'
        
        # Rebuild URL without fragment
        normalized = f"{parsed.scheme}://{parsed.netloc}{path}"
        
        if parsed.query:
            normalized += f"?{parsed.query}"
        
        return normalized
    
    def get_output_path(self, filename: str) -> Path:
        """Get full path for an output file.
        
        Args:
            filename: Name of the output file
            
        Returns:
            Full path in output directory
        """
        return self.output_dir / filename
    
    def get_cache_path(self, cache_key: str, extension: str = "") -> Path:
        """Get cache file path for a given key.
        
        Args:
            cache_key: Cache key (typically URL hash)
            extension: File extension (with or without dot)
            
        Returns:
            Full path in cache directory
        """
        if extension and not extension.startswith('.'):
            extension = '.' + extension
        return self.cache_dir / f"{cache_key}{extension}"
