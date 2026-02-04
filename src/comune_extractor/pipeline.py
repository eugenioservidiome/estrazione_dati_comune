"""End-to-end pipeline orchestration."""

import time
from pathlib import Path
from typing import Dict, List
from concurrent.futures import ThreadPoolExecutor, as_completed
from tqdm import tqdm

from .config import Config
from .catalog import Catalog
from .robots import RobotsHandler
from .crawler import Crawler
from .pdf_store import PDFStore
from .pdf_text import extract_text, save_text, load_text
from .paths import ensure_year_dirs, get_text_dir, get_llm_dir
from .indexer import BM25Index
from .retrieval import Retriever
from .query_builder import generate_queries_for_dataframe
from .csv_io import (load_multiple_csvs, detect_missing_cells, save_filled_csv,
                    create_sources_csv, create_queries_csv, update_dataframe_cell)
from .extract_heuristics import extract_value_heuristic
from .llm_extract import LLMExtractor
from .external_sources import ExternalSources
from .reporting import generate_run_report


class Pipeline:
    """Main extraction pipeline."""
    
    def __init__(self, config: Config):
        self.config = config
        self.catalog = Catalog(config.catalog_path)
        self.stats = {}
    
    def run(self):
        """Execute full pipeline."""
        print(f"\n=== Starting extraction for {self.config.comune} ===\n")
        
        # Setup directories
        ensure_year_dirs(self.config.workspace / "data", self.config.comune, self.config.years)
        
        # Step 1: Crawl
        print("\n--- Step 1: Crawling ---")
        pdf_urls, html_urls = self._crawl()
        
        # Step 2: Download PDFs
        print("\n--- Step 2: Downloading PDFs ---")
        self._download_pdfs(pdf_urls)
        
        # Step 3: Extract text
        print("\n--- Step 3: Extracting text ---")
        self._extract_texts()
        
        # Step 4: Build index
        print("\n--- Step 4: Building BM25 index ---")
        self._build_index()
        
        # Step 5: Fill CSVs
        print("\n--- Step 5: Filling CSVs ---")
        self._fill_csvs()
        
        # Step 6: Generate report
        print("\n--- Step 6: Generating report ---")
        self._generate_report()
        
        print(f"\n=== Extraction complete for {self.config.comune} ===")
        print(f"Results saved to: {self.config.output_dir}")
    
    def _crawl(self) -> tuple:
        """Crawl website for PDFs."""
        start = time.time()
        
        # Setup robots handler
        robots = RobotsHandler(self.config.base_url, self.config.user_agent, 
                              self.config.crawl_delay)
        if self.config.respect_robots:
            robots.load()
        
        # Crawl
        crawler = Crawler(self.config.base_url, robots, 
                         self.config.max_pages, self.config.max_pdfs)
        pdf_urls, html_urls = crawler.crawl()
        
        elapsed = time.time() - start
        self.stats['crawl'] = {
            'pdfs_found': len(pdf_urls),
            'html_found': len(html_urls),
            'time': elapsed
        }
        
        print(f"Found {len(pdf_urls)} PDFs and {len(html_urls)} HTML pages in {elapsed:.2f}s")
        return pdf_urls, html_urls
    
    def _download_pdfs(self, pdf_urls: List[str]):
        """Download PDFs with deduplication."""
        start = time.time()
        
        store = PDFStore(self.catalog, self.config.workspace / "data", 
                        self.config.comune, self.config.user_agent)
        download_stats = store.download_pdfs(pdf_urls, self.config.concurrency_download)
        
        elapsed = time.time() - start
        
        # Calculate cache hit rate
        total = download_stats['total']
        cached = download_stats['cached'] + download_stats['deduplicated']
        cache_hit_rate = cached / total if total > 0 else 0
        
        self.stats['download'] = {
            **download_stats,
            'time': elapsed,
            'cache_hit_rate': cache_hit_rate
        }
        
        print(f"Downloaded: {download_stats['downloaded']}, "
              f"Cached: {download_stats['cached']}, "
              f"Deduplicated: {download_stats['deduplicated']}, "
              f"Failed: {download_stats['failed']}")
        print(f"Cache hit rate: {cache_hit_rate:.1%}")
    
    def _extract_texts(self):
        """Extract text from all PDFs."""
        start = time.time()
        
        # Get all PDFs from catalog
        all_pdfs = self.catalog.get_all_pdfs()
        
        stats = {
            'total': len(all_pdfs),
            'extracted': 0,
            'cached': 0,
            'failed': 0
        }
        
        def process_pdf(pdf_info):
            sha1 = pdf_info['sha1']
            
            # Check if already extracted
            if self.catalog.text_exists(sha1):
                return 'cached'
            
            try:
                pdf_path = Path(pdf_info['local_path'])
                
                # Extract text
                text, pages, extractor = extract_text(pdf_path)
                
                # Determine text directory
                year = pdf_info['detected_year']
                text_dir = get_text_dir(self.config.workspace / "data", 
                                       self.config.comune, year)
                text_path = text_dir / f"{sha1}.txt"
                
                # Save text
                save_text(text, text_path)
                
                # Add to catalog
                self.catalog.add_text(sha1, str(text_path), extractor, pages, len(text))
                
                return 'extracted'
                
            except Exception as e:
                return 'failed'
        
        # Process in parallel
        with ThreadPoolExecutor(max_workers=self.config.concurrency_extract) as executor:
            futures = {executor.submit(process_pdf, pdf): pdf for pdf in all_pdfs}
            
            with tqdm(total=len(all_pdfs), desc="Extracting texts") as pbar:
                for future in as_completed(futures):
                    result = future.result()
                    stats[result] += 1
                    pbar.update(1)
        
        elapsed = time.time() - start
        cache_hit_rate = stats['cached'] / stats['total'] if stats['total'] > 0 else 0
        
        self.stats['extract'] = {
            **stats,
            'time': elapsed,
            'cache_hit_rate': cache_hit_rate
        }
        
        print(f"Extracted: {stats['extracted']}, Cached: {stats['cached']}, "
              f"Failed: {stats['failed']}")
        print(f"Cache hit rate: {cache_hit_rate:.1%}")
    
    def _build_index(self):
        """Build BM25 index for target years."""
        start = time.time()
        
        index = BM25Index(self.config.index_dir)
        
        # Try to load existing index
        if index.load():
            print("Loaded existing index")
        else:
            # Build new index
            documents = []
            
            for year in self.config.years:
                pdfs = self.catalog.get_pdfs_by_year(year)
                
                for pdf in pdfs:
                    sha1 = pdf['sha1']
                    text_info = self.catalog.text_exists(sha1)
                    
                    if text_info:
                        text_path = Path(text_info['text_path'])
                        if text_path.exists():
                            text = load_text(text_path)
                            if text:
                                documents.append({
                                    'sha1': sha1,
                                    'text': text,
                                    'year': year,
                                    'url': pdf['url'],
                                    'filename': pdf['original_name']
                                })
            
            index.build_index(documents)
            index.save()
        
        # Get stats
        by_year = {}
        for year in self.config.years:
            count = sum(1 for doc in index.documents if doc.get('year') == year)
            by_year[year] = count
        
        elapsed = time.time() - start
        self.stats['index'] = {
            'total_docs': len(index.documents),
            'by_year': by_year,
            'time': elapsed
        }
        
        print(f"Index contains {len(index.documents)} documents")
        for year, count in sorted(by_year.items()):
            print(f"  {year}: {count} documents")
        
        self.retriever = Retriever(index)
    
    def _fill_csvs(self):
        """Fill missing cells in CSVs."""
        start = time.time()
        
        # Load CSVs
        csvs = load_multiple_csvs(self.config.input_dir)
        
        # Initialize LLM if enabled
        llm = None
        if self.config.use_llm:
            llm = LLMExtractor(self.catalog, self.config.openai_api_key, 
                             self.config.openai_model, 
                             self.config.llm_confidence_threshold)
        
        # Initialize external sources
        external = ExternalSources(self.config.allow_external)
        
        all_sources = []
        all_queries = []
        not_found_list = []
        total_cells = 0
        filled_cells = 0
        
        # Process each CSV
        for csv_name, df in csvs.items():
            print(f"\nProcessing {csv_name}...")
            
            # Detect missing cells
            missing = detect_missing_cells(df, self.config.years)
            total_cells += len(missing)
            
            # Generate queries
            queries_df = generate_queries_for_dataframe(df, self.config.years)
            all_queries.extend(queries_df.to_dict('records'))
            
            # Fill cells
            for row_idx, indicator, year in tqdm(missing, desc=f"Filling {csv_name}"):
                # Generate queries for this cell
                queries = generate_queries(indicator, year=year, max_queries=2)
                
                # Retrieve documents
                docs = self.retriever.retrieve_multi_query(queries, 
                                                          top_k=self.config.top_k,
                                                          year=year,
                                                          min_score=self.config.min_score)
                
                value = None
                source_info = None
                method = 'NOT_FOUND'
                
                # Try LLM extraction if enabled
                if llm and llm.enabled and docs:
                    for doc in docs[:self.config.llm_max_docs]:
                        text = doc['text']
                        llm_dir = get_llm_dir(self.config.workspace / "data",
                                            self.config.comune, year)
                        
                        result = llm.extract_value(text, indicator, year, llm_dir)
                        if result and result.get('value') is not None:
                            value = result['value']
                            source_info = {
                                'indicator': indicator,
                                'year': year,
                                'value': value,
                                'url': doc['url'],
                                'snippet': result['evidence'][:200],
                                'confidence': result['confidence'],
                                'method': 'llm'
                            }
                            method = 'llm'
                            break
                
                # Fallback to heuristic extraction
                if value is None and docs:
                    for doc in docs[:3]:
                        extractions = extract_value_heuristic(doc['text'], 
                                                             queries, top_k=1)
                        if extractions and extractions[0]['score'] > 0:
                            value = extractions[0]['value']
                            source_info = {
                                'indicator': indicator,
                                'year': year,
                                'value': value,
                                'url': doc['url'],
                                'snippet': extractions[0]['snippet'][:200],
                                'confidence': extractions[0]['score'] / 5.0,
                                'method': 'heuristic'
                            }
                            method = 'heuristic'
                            break
                
                # Try external sources if enabled
                if value is None and external.enabled:
                    ext_result = external.query_all(self.config.comune, indicator, year)
                    if ext_result:
                        value = ext_result.get('value')
                        source_info = {
                            'indicator': indicator,
                            'year': year,
                            'value': value,
                            'url': ext_result.get('url', ''),
                            'snippet': '',
                            'confidence': 1.0,
                            'method': f"external_{ext_result.get('source', '')}"
                        }
                        method = 'external'
                
                # Update dataframe
                if value is not None:
                    df = update_dataframe_cell(df, row_idx, year, value)
                    filled_cells += 1
                    if source_info:
                        all_sources.append(source_info)
                else:
                    df = update_dataframe_cell(df, row_idx, year, 'NOT_FOUND')
                    not_found_list.append({'indicator': indicator, 'year': year})
            
            # Save filled CSV
            output_path = self.config.output_dir / f"{csv_name}_filled.csv"
            save_filled_csv(df, output_path)
        
        # Save sources and queries
        create_sources_csv(all_sources, self.config.output_dir / "sources_long.csv")
        create_queries_csv(all_queries, self.config.output_dir / "queries_generated.csv")
        
        elapsed = time.time() - start
        coverage = filled_cells / total_cells if total_cells > 0 else 0
        
        self.stats['fill'] = {
            'total_cells': total_cells,
            'filled': filled_cells,
            'not_found': len(not_found_list),
            'coverage': coverage,
            'time': elapsed
        }
        self.stats['not_found_list'] = not_found_list
        
        print(f"\nFilled {filled_cells}/{total_cells} cells ({coverage:.1%} coverage)")
    
    def _generate_report(self):
        """Generate run report."""
        report_path = self.config.output_dir / "run_report.md"
        generate_run_report(report_path, self.stats, self.config.comune,
                          self.config.base_url, self.config.years)
        print(f"Report saved to {report_path}")


from .query_builder import generate_queries
