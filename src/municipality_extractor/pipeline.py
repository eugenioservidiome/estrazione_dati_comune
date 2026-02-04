"""Main orchestration pipeline for municipality data extraction."""

import logging
from pathlib import Path
from typing import Dict, List, Optional

import pandas as pd
from tqdm import tqdm

from .config import RunConfig
from .crawler import WebCrawler
from .csv_io import (
    load_csv_robust,
    detect_missing_cells,
    detect_section_headers,
    get_section_for_row
)
from .extractors import extract_text_from_html, extract_text_from_pdf
from .indexing import DocumentIndex
from .query_builder import categorize_cell, build_queries
from .utils import setup_logging, url_to_cache_key
from .value_extraction import extract_value_from_text

logger = logging.getLogger(__name__)


def process_single_csv(
    csv_path: Path,
    config: RunConfig,
    index: DocumentIndex
) -> Dict:
    """Process a single CSV file to fill missing values.
    
    Args:
        csv_path: Path to input CSV
        config: Run configuration
        index: Built document index
        
    Returns:
        Dict with keys:
            - df_filled: DataFrame with filled values
            - sources: List of source records
            - queries: List of query records
            - stats: Processing statistics
    """
    logger.info(f"Processing CSV: {csv_path.name}")
    
    # Load CSV
    df, delimiter = load_csv_robust(csv_path)
    logger.info(f"Loaded CSV with {len(df)} rows, {len(df.columns)} columns")
    
    # Detect missing cells
    missing_cells = detect_missing_cells(df)
    logger.info(f"Found {len(missing_cells)} missing cells")
    
    # Detect section headers
    section_rows = detect_section_headers(df)
    
    # Results storage
    sources = []
    queries_generated = []
    fills_attempted = 0
    fills_successful = 0
    
    # Process each missing cell
    for row_idx, col_name in tqdm(missing_cells, desc=f"Processing {csv_path.name}"):
        fills_attempted += 1
        
        # Get row context
        row = df.iloc[row_idx]
        section = get_section_for_row(row_idx, section_rows)
        
        # Categorize cell
        first_col = df.columns[0] if len(df.columns) > 0 else ""
        row_label = str(row.get(first_col, ""))
        category = categorize_cell(row_label, section or "")
        
        # Generate queries for this cell
        cell_queries = []
        for year in config.years_to_fill:
            query_list = build_queries(
                category=category,
                domain=config.domain,
                comune=config.comune or "Comune",
                year=year,
                allow_external=config.allow_external_official,
                extra_params={'LABEL': col_name}
            )
            # Extract semantic queries
            for q in query_list:
                cell_queries.append(q['semantic_query'])
        
        if not cell_queries:
            logger.debug(f"No queries generated for row {row_idx}, column {col_name}")
            continue
        
        # Record queries
        for q in cell_queries[:config.top_k_queries]:
            queries_generated.append({
                'csv_file': csv_path.name,
                'row': row_idx,
                'column': col_name,
                'query': q,
                'section': section
            })
        
        # Search documents with each query
        best_value = None
        best_confidence = 0.0
        best_source = None
        
        for query in cell_queries[:config.top_k_queries]:
            # Search index
            results = index.search(query, top_k=5)
            
            if not results:
                continue
            
            # Try to extract value from top results
            for result in results[:3]:  # Check top 3 documents
                # Extract keywords from query
                keywords = _extract_keywords_from_query(query)
                
                # Try to extract value
                extraction = extract_value_from_text(
                    text=result['text'],
                    keywords=keywords,
                    year=config.years_to_fill[0] if config.years_to_fill else None,
                    context_window=config.context_window_chars,
                    min_keywords=config.min_keywords_for_extraction
                )
                
                # Check if better than current best
                if extraction['value'] is not None and extraction['confidence'] > best_confidence:
                    best_value = extraction['value']
                    best_confidence = extraction['confidence']
                    best_source = {
                        'doc_id': result['doc_id'],
                        'url': result.get('url', 'unknown'),
                        'score': result['score'],
                        'snippet': extraction['snippet'],
                        'keywords_found': extraction['keywords_found']
                    }
        
        # Fill cell if value found
        if best_value is not None and best_confidence >= 0.3:  # Minimum confidence threshold
            df.at[row_idx, col_name] = str(best_value)
            fills_successful += 1
            
            # Record source
            sources.append({
                'csv_file': csv_path.name,
                'row': row_idx,
                'column': col_name,
                'value': best_value,
                'confidence': best_confidence,
                'source_url': best_source['url'],
                'doc_id': best_source['doc_id'],
                'snippet': best_source['snippet'],
                'keywords_found': ', '.join(best_source['keywords_found'])
            })
    
    stats = {
        'csv_file': csv_path.name,
        'total_cells': len(df) * len(df.columns),
        'missing_cells': len(missing_cells),
        'fills_attempted': fills_attempted,
        'fills_successful': fills_successful,
        'fill_rate': fills_successful / max(1, fills_attempted)
    }
    
    logger.info(f"Filled {fills_successful}/{fills_attempted} cells ({stats['fill_rate']:.1%})")
    
    return {
        'df_filled': df,
        'sources': sources,
        'queries': queries_generated,
        'stats': stats
    }


def run_pipeline(config: RunConfig) -> Dict:
    """Run the complete extraction pipeline.
    
    Steps:
    1. Initialize logging
    2. Crawl municipality website
    3. Extract text from all documents
    4. Build TF-IDF index
    5. Process all CSV files
    6. Save outputs
    
    Args:
        config: Run configuration
        
    Returns:
        Dict with pipeline statistics and results
    """
    # Initialize logging
    setup_logging(level=logging.INFO)
    logger.info("=" * 80)
    logger.info("Starting Municipality Data Extraction Pipeline")
    logger.info("=" * 80)
    logger.info(f"Base URL: {config.base_url}")
    logger.info(f"Municipality: {config.comune or 'Unknown'}")
    logger.info(f"Years: {config.years_to_fill}")
    logger.info(f"Input dir: {config.input_dir}")
    logger.info(f"Output dir: {config.output_dir}")
    
    try:
        # Step 1: Crawl website
        logger.info("\n" + "=" * 80)
        logger.info("STEP 1: Crawling website")
        logger.info("=" * 80)
        
        crawler = WebCrawler(config)
        html_docs, pdf_docs = crawler.crawl()
        
        total_docs = len(html_docs) + len(pdf_docs)
        logger.info(f"Crawled {total_docs} documents ({len(html_docs)} HTML, {len(pdf_docs)} PDF)")
        logger.info(f"Visited: {len(crawler.visited)}, Failed: {len(crawler.failed_urls)}")
        
        # Step 2: Extract text from documents
        logger.info("\n" + "=" * 80)
        logger.info("STEP 2: Extracting text from documents")
        logger.info("=" * 80)
        
        documents = []
        
        # Process HTML documents
        for doc in tqdm(html_docs, desc="Extracting HTML"):
            text = extract_text_from_html(doc['content'], doc['url'])
            if text and len(text.strip()) > 100:
                doc_id = url_to_cache_key(doc['url'])
                documents.append({
                    'doc_id': doc_id,
                    'url': doc['url'],
                    'text': text,
                    'content_type': 'html',
                    'length': len(text)
                })
        
        # Process PDF documents
        for doc in tqdm(pdf_docs, desc="Extracting PDF"):
            text = extract_text_from_pdf(doc['content'], doc['url'])
            if text and len(text.strip()) > 100:
                doc_id = url_to_cache_key(doc['url'])
                documents.append({
                    'doc_id': doc_id,
                    'url': doc['url'],
                    'text': text,
                    'content_type': 'pdf',
                    'length': len(text)
                })
        
        logger.info(f"Extracted text from {len(documents)} documents")
        
        if not documents:
            logger.error("No documents with text extracted! Cannot proceed.")
            return {'error': 'No documents extracted'}
        
        # Step 3: Build TF-IDF index
        logger.info("\n" + "=" * 80)
        logger.info("STEP 3: Building TF-IDF index")
        logger.info("=" * 80)
        
        index = DocumentIndex(
            max_features=config.max_tfidf_features,
            ngram_range=config.ngram_range
        )
        index.build_index(documents)
        
        # Step 4: Process CSV files
        logger.info("\n" + "=" * 80)
        logger.info("STEP 4: Processing CSV files")
        logger.info("=" * 80)
        
        csv_files = list(config.input_dir.glob("*.csv"))
        if not csv_files:
            logger.warning(f"No CSV files found in {config.input_dir}")
            return {'error': f'No CSV files in {config.input_dir}'}
        
        logger.info(f"Found {len(csv_files)} CSV files")
        
        all_sources = []
        all_queries = []
        all_stats = []
        
        for csv_path in csv_files:
            try:
                result = process_single_csv(csv_path, config, index)
                
                # Save filled CSV
                output_path = config.get_output_path(f"{csv_path.stem}_filled.csv")
                result['df_filled'].to_csv(output_path, index=False)
                logger.info(f"Saved filled CSV to: {output_path}")
                
                # Accumulate results
                all_sources.extend(result['sources'])
                all_queries.extend(result['queries'])
                all_stats.append(result['stats'])
                
            except Exception as e:
                logger.error(f"Error processing {csv_path.name}: {e}", exc_info=True)
                all_stats.append({
                    'csv_file': csv_path.name,
                    'error': str(e)
                })
        
        # Step 5: Save outputs
        logger.info("\n" + "=" * 80)
        logger.info("STEP 5: Saving outputs")
        logger.info("=" * 80)
        
        # Save sources
        if all_sources:
            sources_df = pd.DataFrame(all_sources)
            sources_path = config.get_output_path("sources_long.csv")
            sources_df.to_csv(sources_path, index=False)
            logger.info(f"Saved {len(all_sources)} sources to: {sources_path}")
        
        # Save queries
        if all_queries:
            queries_df = pd.DataFrame(all_queries)
            queries_path = config.get_output_path("queries_generated.csv")
            queries_df.to_csv(queries_path, index=False)
            logger.info(f"Saved {len(all_queries)} queries to: {queries_path}")
        
        # Save statistics report
        report_lines = []
        report_lines.append("# Municipality Data Extraction Report\n")
        report_lines.append(f"**Municipality**: {config.comune or 'Unknown'}\n")
        report_lines.append(f"**Base URL**: {config.base_url}\n")
        report_lines.append(f"**Years**: {', '.join(map(str, config.years_to_fill))}\n")
        report_lines.append(f"\n## Crawl Statistics\n")
        report_lines.append(f"- Pages crawled: {total_docs}\n")
        report_lines.append(f"- HTML documents: {len(html_docs)}\n")
        report_lines.append(f"- PDF documents: {len(pdf_docs)}\n")
        report_lines.append(f"- Documents with text: {len(documents)}\n")
        report_lines.append(f"- Failed URLs: {len(crawler.failed_urls)}\n")
        report_lines.append(f"\n## Processing Statistics\n")
        
        for stat in all_stats:
            if 'error' in stat:
                report_lines.append(f"- **{stat['csv_file']}**: ERROR - {stat['error']}\n")
            else:
                report_lines.append(f"- **{stat['csv_file']}**:\n")
                report_lines.append(f"  - Missing cells: {stat['missing_cells']}\n")
                report_lines.append(f"  - Fills attempted: {stat['fills_attempted']}\n")
                report_lines.append(f"  - Fills successful: {stat['fills_successful']}\n")
                report_lines.append(f"  - Fill rate: {stat['fill_rate']:.1%}\n")
        
        report_path = config.get_output_path("run_report.md")
        report_path.write_text(''.join(report_lines))
        logger.info(f"Saved report to: {report_path}")
        
        logger.info("\n" + "=" * 80)
        logger.info("Pipeline completed successfully!")
        logger.info("=" * 80)
        
        return {
            'success': True,
            'documents': len(documents),
            'sources': len(all_sources),
            'queries': len(all_queries),
            'stats': all_stats
        }
        
    except Exception as e:
        logger.error(f"Pipeline failed with error: {e}", exc_info=True)
        return {'error': str(e)}


def _extract_keywords_from_query(query: str) -> List[str]:
    """Extract keywords from a query string.
    
    Removes common query operators and extracts meaningful terms.
    
    Args:
        query: Query string
        
    Returns:
        List of keywords
    """
    # Remove query operators
    query = query.replace('site:', '')
    query = query.replace('filetype:', '')
    query = query.replace('inurl:', '')
    query = query.replace('AND', ' ')
    query = query.replace('OR', ' ')
    query = query.replace('"', '')
    
    # Split and filter
    words = query.split()
    
    # Filter out domain names, file extensions, years, and short words
    keywords = []
    for word in words:
        word = word.strip('.,;:!?()[]{}')
        if len(word) < 3:
            continue
        if word.isdigit():
            continue
        if '.' in word and len(word.split('.')) > 1:  # Likely a domain
            continue
        keywords.append(word)
    
    return keywords[:10]  # Limit to top 10
