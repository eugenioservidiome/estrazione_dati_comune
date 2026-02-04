"""robots.txt parser with allow/disallow rules and politeness."""

import requests
import time
from urllib.parse import urlparse, urljoin
from urllib.robotparser import RobotFileParser
from typing import Optional


class RobotsHandler:
    """Handle robots.txt parsing and politeness delays."""
    
    def __init__(self, base_url: str, user_agent: str = "comune_extractor/2.0",
                 default_delay: float = 1.0):
        self.base_url = base_url
        self.user_agent = user_agent
        self.default_delay = default_delay
        self.parser = RobotFileParser()
        self.crawl_delay = default_delay
        self.last_request_time = 0.0
        self._loaded = False
    
    def load(self) -> bool:
        """Load and parse robots.txt."""
        try:
            parsed = urlparse(self.base_url)
            robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"
            
            response = requests.get(robots_url, timeout=10)
            if response.status_code == 200:
                self.parser.parse(response.text.splitlines())
                self._loaded = True
                
                # Try to get crawl-delay
                # Note: RobotFileParser doesn't expose crawl-delay directly
                # We'll parse it manually
                for line in response.text.splitlines():
                    line = line.strip().lower()
                    if line.startswith('crawl-delay:'):
                        try:
                            delay = float(line.split(':', 1)[1].strip())
                            self.crawl_delay = max(delay, self.default_delay)
                        except (ValueError, IndexError):
                            pass
                
                return True
            else:
                # No robots.txt found, allow all
                self._loaded = False
                return False
        except Exception as e:
            # On error, allow all but use default delay
            self._loaded = False
            return False
    
    def can_fetch(self, url: str) -> bool:
        """Check if URL can be fetched according to robots.txt."""
        if not self._loaded:
            return True  # No robots.txt means allow all
        
        return self.parser.can_fetch(self.user_agent, url)
    
    def wait(self):
        """Wait appropriate delay since last request."""
        elapsed = time.time() - self.last_request_time
        if elapsed < self.crawl_delay:
            time.sleep(self.crawl_delay - elapsed)
        self.last_request_time = time.time()
    
    def get_sitemap_urls(self) -> list[str]:
        """Extract sitemap URLs from robots.txt."""
        if not self._loaded:
            return []
        
        # RobotFileParser doesn't expose sitemaps, parse manually
        sitemaps = []
        try:
            parsed = urlparse(self.base_url)
            robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"
            response = requests.get(robots_url, timeout=10)
            
            if response.status_code == 200:
                for line in response.text.splitlines():
                    line = line.strip()
                    if line.lower().startswith('sitemap:'):
                        sitemap_url = line.split(':', 1)[1].strip()
                        sitemaps.append(sitemap_url)
        except Exception:
            pass
        
        return sitemaps
