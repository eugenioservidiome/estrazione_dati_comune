"""Web crawler with caching, robots.txt support, and retry logic."""

import json
import logging
import time
from collections import deque
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple
from urllib.parse import urlparse
from urllib.robotparser import RobotFileParser

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from tqdm import tqdm

from .config import RunConfig
from .utils import normalize_url, same_domain, is_useful_extension, url_to_cache_key

logger = logging.getLogger(__name__)


class WebCrawler:
    """Web crawler with caching and politeness."""
    
    def __init__(self, config: RunConfig):
        """Initialize crawler.
        
        Args:
            config: Run configuration
        """
        self.config = config
        self.session = self._create_session()
        self.robots_parser = None
        self.visited: Set[str] = set()
        self.failed_urls: Set[str] = set()
        
        # Initialize robots.txt parser if needed
        if config.respect_robots:
            self._init_robots_parser()
    
    def _create_session(self) -> requests.Session:
        """Create requests session with retry logic.
        
        Returns:
            Configured session
        """
        session = requests.Session()
        
        # Configure retry strategy
        retry_strategy = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["HEAD", "GET", "OPTIONS"]
        )
        
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        
        # Set headers
        session.headers.update({
            'User-Agent': self.config.user_agent,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'it-IT,it;q=0.9,en;q=0.8',
        })
        
        return session
    
    def _init_robots_parser(self) -> None:
        """Initialize robots.txt parser."""
        robots_url = f"{self.config.normalized_base_url}robots.txt"
        
        try:
            self.robots_parser = RobotFileParser()
            self.robots_parser.set_url(robots_url)
            self.robots_parser.read()
            logger.info(f"Loaded robots.txt from {robots_url}")
        except Exception as e:
            logger.warning(f"Could not load robots.txt from {robots_url}: {e}")
            self.robots_parser = None
    
    def can_fetch(self, url: str) -> bool:
        """Check if URL can be fetched according to robots.txt.
        
        Args:
            url: URL to check
            
        Returns:
            True if allowed, False otherwise
        """
        if not self.config.respect_robots or not self.robots_parser:
            return True
        
        try:
            return self.robots_parser.can_fetch(self.config.user_agent, url)
        except Exception as e:
            logger.warning(f"Error checking robots.txt for {url}: {e}")
            return True  # Allow on error
    
    def get_sitemap_urls(self) -> List[str]:
        """Try to extract URLs from sitemap.xml.
        
        Returns:
            List of URLs from sitemap (best effort)
        """
        sitemap_url = f"{self.config.normalized_base_url}sitemap.xml"
        urls = []
        
        try:
            response = self.session.get(sitemap_url, timeout=self.config.request_timeout)
            if response.status_code == 200:
                from bs4 import BeautifulSoup
                soup = BeautifulSoup(response.content, 'xml')
                
                # Extract <loc> tags
                for loc in soup.find_all('loc'):
                    url = loc.text.strip()
                    if url:
                        urls.append(url)
                
                logger.info(f"Found {len(urls)} URLs in sitemap.xml")
        except Exception as e:
            logger.debug(f"Could not load sitemap.xml: {e}")
        
        return urls
    
    def _get_cache_metadata_path(self, url: str) -> Path:
        """Get path to cache metadata file.
        
        Args:
            url: URL
            
        Returns:
            Path to metadata JSON file
        """
        cache_key = url_to_cache_key(url)
        return self.config.get_cache_path(cache_key, '.meta.json')
    
    def _get_cache_content_path(self, url: str, content_type: str) -> Path:
        """Get path to cached content file.
        
        Args:
            url: URL
            content_type: Content type (html or pdf)
            
        Returns:
            Path to cached content file
        """
        cache_key = url_to_cache_key(url)
        ext = '.pdf' if content_type == 'pdf' else '.html'
        return self.config.get_cache_path(cache_key, ext)
    
    def _load_from_cache(self, url: str) -> Optional[Tuple[bytes, str, Dict]]:
        """Load content from cache if available.
        
        Args:
            url: URL to load
            
        Returns:
            Tuple of (content_bytes, content_type, metadata) or None if not cached
        """
        meta_path = self._get_cache_metadata_path(url)
        
        if not meta_path.exists():
            return None
        
        try:
            with open(meta_path, 'r') as f:
                metadata = json.load(f)
            
            content_type = metadata.get('content_type', 'html')
            content_path = self._get_cache_content_path(url, content_type)
            
            if not content_path.exists():
                return None
            
            with open(content_path, 'rb') as f:
                content = f.read()
            
            logger.debug(f"Loaded from cache: {url}")
            return content, content_type, metadata
        except Exception as e:
            logger.warning(f"Error loading cache for {url}: {e}")
            return None
    
    def _save_to_cache(self, url: str, content: bytes, content_type: str, 
                       etag: Optional[str] = None, last_modified: Optional[str] = None) -> None:
        """Save content to cache.
        
        Args:
            url: URL
            content: Content bytes
            content_type: 'html' or 'pdf'
            etag: ETag header value (optional)
            last_modified: Last-Modified header value (optional)
        """
        try:
            # Save metadata
            metadata = {
                'url': url,
                'content_type': content_type,
                'cached_at': time.time(),
                'etag': etag,
                'last_modified': last_modified,
            }
            
            meta_path = self._get_cache_metadata_path(url)
            with open(meta_path, 'w') as f:
                json.dump(metadata, f, indent=2)
            
            # Save content
            content_path = self._get_cache_content_path(url, content_type)
            with open(content_path, 'wb') as f:
                f.write(content)
            
            logger.debug(f"Saved to cache: {url}")
        except Exception as e:
            logger.warning(f"Error saving cache for {url}: {e}")
    
    def fetch_url(self, url: str, allow_pdf: bool = True) -> Optional[Tuple[bytes, str]]:
        """Fetch URL with caching.
        
        Args:
            url: URL to fetch
            allow_pdf: Whether to download PDFs
            
        Returns:
            Tuple of (content_bytes, content_type) or None if failed
        """
        # Check cache first
        cached = self._load_from_cache(url)
        if cached:
            return cached[0], cached[1]
        
        # Check robots.txt
        if not self.can_fetch(url):
            logger.info(f"Blocked by robots.txt: {url}")
            return None
        
        try:
            # Politeness delay
            if self.visited:
                time.sleep(self.config.politeness_delay)
            
            # Fetch
            response = self.session.get(url, timeout=self.config.request_timeout, stream=True)
            response.raise_for_status()
            
            # Check content type
            content_type_header = response.headers.get('Content-Type', '').lower()
            
            # Determine if PDF
            is_pdf = (
                'application/pdf' in content_type_header or
                url.lower().endswith('.pdf')
            )
            
            if is_pdf:
                if not allow_pdf:
                    logger.debug(f"Skipping PDF: {url}")
                    return None
                
                # Check size
                content_length = response.headers.get('Content-Length')
                if content_length:
                    size_mb = int(content_length) / (1024 * 1024)
                    if size_mb > self.config.max_pdf_mb:
                        logger.warning(f"PDF too large ({size_mb:.1f} MB): {url}")
                        return None
                
                content_type = 'pdf'
            else:
                content_type = 'html'
            
            # Read content
            content = response.content
            
            # Save to cache
            etag = response.headers.get('ETag')
            last_modified = response.headers.get('Last-Modified')
            self._save_to_cache(url, content, content_type, etag, last_modified)
            
            self.visited.add(url)
            return content, content_type
            
        except requests.exceptions.RequestException as e:
            logger.warning(f"Failed to fetch {url}: {e}")
            self.failed_urls.add(url)
            return None
        except Exception as e:
            logger.error(f"Unexpected error fetching {url}: {e}")
            self.failed_urls.add(url)
            return None
    
    def extract_links_from_html(self, html_content: bytes, base_url: str) -> List[str]:
        """Extract and normalize links from HTML.
        
        Args:
            html_content: HTML content bytes
            base_url: Base URL for relative links
            
        Returns:
            List of normalized absolute URLs
        """
        from bs4 import BeautifulSoup
        
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            links = []
            
            for tag in soup.find_all(['a', 'link']):
                href = tag.get('href')
                if href:
                    normalized = normalize_url(href, base_url)
                    if normalized:
                        links.append(normalized)
            
            return links
        except Exception as e:
            logger.warning(f"Error extracting links from {base_url}: {e}")
            return []
    
    def crawl(self) -> Tuple[List[Dict], List[Dict]]:
        """Crawl website starting from base_url.
        
        Returns:
            Tuple of (html_documents, pdf_documents)
            Each document is a dict with 'url', 'content', 'type'
        """
        html_docs = []
        pdf_docs = []
        
        # Initialize queue with base URL
        queue = deque([self.config.normalized_base_url])
        
        # Add sitemap URLs if available
        sitemap_urls = self.get_sitemap_urls()
        for url in sitemap_urls:
            if same_domain(url, self.config.normalized_base_url):
                queue.append(url)
        
        seen_urls: Set[str] = set()
        pages_crawled = 0
        
        pbar = tqdm(desc="Crawling", unit="pages")
        
        while queue and pages_crawled < self.config.max_pages:
            # Check queue size limit
            if len(queue) > self.config.max_queue_size:
                logger.warning(f"Queue size exceeded {self.config.max_queue_size}, stopping crawl")
                break
            
            url = queue.popleft()
            
            # Skip if already seen
            if url in seen_urls:
                continue
            seen_urls.add(url)
            
            # Skip if not same domain
            if not same_domain(url, self.config.normalized_base_url):
                continue
            
            # Skip if not useful extension
            if not is_useful_extension(url):
                continue
            
            # Fetch
            result = self.fetch_url(url)
            if not result:
                continue
            
            content, content_type = result
            pages_crawled += 1
            pbar.update(1)
            pbar.set_postfix({'html': len(html_docs), 'pdf': len(pdf_docs)})
            
            if content_type == 'pdf':
                pdf_docs.append({
                    'url': url,
                    'content': content,
                    'type': 'pdf'
                })
            else:
                html_docs.append({
                    'url': url,
                    'content': content,
                    'type': 'html'
                })
                
                # Extract links for further crawling
                links = self.extract_links_from_html(content, url)
                for link in links:
                    if link not in seen_urls and same_domain(link, self.config.normalized_base_url):
                        queue.append(link)
        
        pbar.close()
        
        logger.info(f"Crawling complete: {len(html_docs)} HTML, {len(pdf_docs)} PDF documents")
        logger.info(f"Failed URLs: {len(self.failed_urls)}")
        
        return html_docs, pdf_docs
