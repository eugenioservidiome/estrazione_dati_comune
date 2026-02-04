"""PDF download with SHA1 deduplication and SQLite catalog."""

import requests
from pathlib import Path
from typing import Optional, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed
from tqdm import tqdm

from .catalog import Catalog
from .paths import sanitize_filename, get_pdf_dir
from .year_detect import detect_year_comprehensive


class PDFStore:
    """Download and store PDFs with deduplication."""
    
    def __init__(self, catalog: Catalog, base_dir: Path, comune: str,
                 user_agent: str = "comune_extractor/2.0"):
        self.catalog = catalog
        self.base_dir = base_dir
        self.comune = comune
        self.user_agent = user_agent
    
    def download_pdfs(self, pdf_urls: list[str], max_workers: int = 8) -> dict:
        """
        Download PDFs with deduplication and year detection.
        Returns stats dict.
        """
        stats = {
            'total': len(pdf_urls),
            'downloaded': 0,
            'cached': 0,
            'failed': 0,
            'deduplicated': 0,
        }
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {executor.submit(self._download_pdf, url): url 
                      for url in pdf_urls}
            
            with tqdm(total=len(pdf_urls), desc="Downloading PDFs") as pbar:
                for future in as_completed(futures):
                    result = future.result()
                    if result == 'downloaded':
                        stats['downloaded'] += 1
                    elif result == 'cached':
                        stats['cached'] += 1
                    elif result == 'deduplicated':
                        stats['deduplicated'] += 1
                    else:
                        stats['failed'] += 1
                    pbar.update(1)
        
        return stats
    
    def _download_pdf(self, url: str) -> str:
        """Download a single PDF. Returns status: downloaded/cached/deduplicated/failed."""
        try:
            # Check if already in catalog by URL
            existing = self.catalog.pdf_exists(url)
            if existing:
                # Verify file still exists
                if Path(existing['local_path']).exists():
                    return 'cached'
            
            # Download to temporary location
            response = requests.get(url, timeout=30, headers={
                'User-Agent': self.user_agent
            })
            
            if response.status_code != 200:
                return 'failed'
            
            content_type = response.headers.get('Content-Type', '')
            if 'pdf' not in content_type.lower() and not url.lower().endswith('.pdf'):
                return 'failed'
            
            # Get original filename
            original_name = url.split('/')[-1].split('?')[0]
            if not original_name.endswith('.pdf'):
                original_name += '.pdf'
            
            # Save to temporary file to compute SHA1
            temp_path = self.base_dir / self.comune.lower() / "temp" / original_name
            temp_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(temp_path, 'wb') as f:
                f.write(response.content)
            
            # Compute SHA1
            sha1 = Catalog.compute_sha1(temp_path)
            
            # Check if this SHA1 already exists
            existing_sha1 = self.catalog.pdf_exists_by_sha1(sha1)
            if existing_sha1:
                # Already have this PDF, just update URL mapping
                temp_path.unlink()
                self.catalog.add_pdf(
                    url=url,
                    sha1=sha1,
                    original_name=original_name,
                    local_path=existing_sha1['local_path'],
                    detected_year=existing_sha1['detected_year'],
                    content_type=content_type,
                    size_bytes=existing_sha1['size_bytes']
                )
                return 'deduplicated'
            
            # Detect year
            detected_year = detect_year_comprehensive(temp_path, url, original_name)
            
            # Move to appropriate directory
            pdf_dir = get_pdf_dir(self.base_dir, self.comune, detected_year)
            pdf_dir.mkdir(parents=True, exist_ok=True)
            
            # Create final filename: {sha1}_{original_name}
            safe_name = sanitize_filename(original_name)
            final_name = f"{sha1[:8]}_{safe_name}"
            final_path = pdf_dir / final_name
            
            # Move file
            temp_path.rename(final_path)
            
            # Add to catalog
            self.catalog.add_pdf(
                url=url,
                sha1=sha1,
                original_name=original_name,
                local_path=str(final_path),
                detected_year=detected_year,
                content_type=content_type,
                size_bytes=len(response.content)
            )
            
            return 'downloaded'
            
        except Exception as e:
            return 'failed'
