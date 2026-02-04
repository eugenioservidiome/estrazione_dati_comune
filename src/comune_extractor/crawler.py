"""Focused web crawler with sitemap.xml support and BFS."""

import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
from typing import Set, List, Optional, Tuple
from collections import deque
import xml.etree.ElementTree as ET


class Crawler:
    """Web crawler focused on finding PDFs with sitemap and BFS support."""
    
    def __init__(self, base_url: str, robots_handler, max_pages: int = 500,
                 max_pdfs: int = 2000):
        self.base_url = base_url.rstrip('/')
        self.robots_handler = robots_handler
        self.max_pages = max_pages
        self.max_pdfs = max_pdfs
        self.domain = urlparse(base_url).netloc
        self.visited_urls: Set[str] = set()
        self.pdf_urls: List[str] = []
        self.html_urls: List[str] = []
    
    def crawl(self) -> Tuple[List[str], List[str]]:
        """
        Crawl website for PDFs and HTML pages.
        Returns (pdf_urls, html_urls).
        """
        # Try sitemap first
        sitemap_urls = self.robots_handler.get_sitemap_urls()
        if sitemap_urls:
            for sitemap_url in sitemap_urls:
                self._process_sitemap(sitemap_url)
        
        # If we haven't found enough, do BFS crawl
        if len(self.pdf_urls) < self.max_pdfs and len(self.visited_urls) < self.max_pages:
            self._bfs_crawl()
        
        return self.pdf_urls[:self.max_pdfs], self.html_urls
    
    def _process_sitemap(self, sitemap_url: str):
        """Process sitemap.xml file."""
        try:
            response = requests.get(sitemap_url, timeout=10)
            if response.status_code != 200:
                return
            
            # Parse XML
            root = ET.fromstring(response.content)
            
            # Handle different namespaces
            namespaces = {
                'sm': 'http://www.sitemaps.org/schemas/sitemap/0.9',
                '': 'http://www.sitemaps.org/schemas/sitemap/0.9'
            }
            
            # Look for URLs
            for url_elem in root.findall('.//sm:url/sm:loc', namespaces):
                url = url_elem.text
                if url:
                    self._process_url(url)
            
            # Also try without namespace
            for url_elem in root.findall('.//url/loc'):
                url = url_elem.text
                if url:
                    self._process_url(url)
            
            # Check for sitemap index (nested sitemaps)
            for sitemap_elem in root.findall('.//sm:sitemap/sm:loc', namespaces):
                nested_url = sitemap_elem.text
                if nested_url and nested_url not in self.visited_urls:
                    self._process_sitemap(nested_url)
            
        except Exception as e:
            pass
    
    def _process_url(self, url: str):
        """Process a single URL (categorize as PDF or HTML)."""
        if url in self.visited_urls:
            return
        
        if len(self.pdf_urls) >= self.max_pdfs:
            return
        
        self.visited_urls.add(url)
        
        if url.lower().endswith('.pdf'):
            if self.robots_handler.can_fetch(url):
                self.pdf_urls.append(url)
        else:
            self.html_urls.append(url)
    
    def _bfs_crawl(self):
        """Breadth-first search crawl."""
        queue = deque([self.base_url])
        
        while queue and len(self.visited_urls) < self.max_pages and len(self.pdf_urls) < self.max_pdfs:
            url = queue.popleft()
            
            if url in self.visited_urls:
                continue
            
            if not self._is_same_domain(url):
                continue
            
            if not self.robots_handler.can_fetch(url):
                continue
            
            self.visited_urls.add(url)
            
            # Check if it's a PDF
            if url.lower().endswith('.pdf'):
                self.pdf_urls.append(url)
                continue
            
            # Fetch and parse HTML
            try:
                self.robots_handler.wait()
                response = requests.get(url, timeout=10, headers={
                    'User-Agent': self.robots_handler.user_agent
                })
                
                if response.status_code != 200:
                    continue
                
                # Check content type
                content_type = response.headers.get('Content-Type', '').lower()
                if 'pdf' in content_type:
                    self.pdf_urls.append(url)
                    continue
                
                if 'html' not in content_type:
                    continue
                
                self.html_urls.append(url)
                
                # Parse links
                soup = BeautifulSoup(response.content, 'html.parser')
                for link in soup.find_all('a', href=True):
                    href = link['href']
                    full_url = urljoin(url, href)
                    
                    if full_url not in self.visited_urls and self._is_same_domain(full_url):
                        queue.append(full_url)
                
            except Exception as e:
                continue
    
    def _is_same_domain(self, url: str) -> bool:
        """Check if URL belongs to the same domain."""
        return urlparse(url).netloc == self.domain

