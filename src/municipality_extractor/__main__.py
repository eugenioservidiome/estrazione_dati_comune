"""Command-line interface for municipality data extractor."""

import argparse
import sys
from pathlib import Path

from .config import RunConfig
from .pipeline import run_pipeline


def parse_args():
    """Parse command line arguments.
    
    Returns:
        Parsed arguments namespace
    """
    parser = argparse.ArgumentParser(
        description='Extract missing data from municipality CSV files using web scraping and document retrieval.',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Basic usage
  python -m municipality_extractor --base-url https://www.comune.example.it --comune "Example"
  
  # Specify custom directories
  python -m municipality_extractor \\
    --base-url https://www.comune.example.it \\
    --comune "Example" \\
    --input-dir ./data/input \\
    --output-dir ./data/output
  
  # Allow external sources and customize years
  python -m municipality_extractor \\
    --base-url https://www.comune.example.it \\
    --comune "Example" \\
    --years 2022 2023 2024 \\
    --allow-external
  
  # Advanced: customize crawling behavior
  python -m municipality_extractor \\
    --base-url https://www.comune.example.it \\
    --max-pages 1000 \\
    --max-depth 5 \\
    --politeness-delay 1.0
"""
    )
    
    # Required arguments
    parser.add_argument(
        '--base-url',
        required=True,
        help='Base URL of municipality website (e.g., https://www.comune.vigone.to.it/)'
    )
    
    # Optional arguments
    parser.add_argument(
        '--comune',
        help='Municipality name (for logging and queries)'
    )
    
    parser.add_argument(
        '--years',
        type=int,
        nargs='+',
        default=[2023, 2024],
        help='Years to extract data for (default: 2023 2024)'
    )
    
    parser.add_argument(
        '--allow-external',
        action='store_true',
        help='Allow external official sources (ISTAT, MEF, ISPRA, etc.)'
    )
    
    # Directories
    parser.add_argument(
        '--input-dir',
        type=Path,
        default=Path('input'),
        help='Input directory containing CSV files (default: ./input)'
    )
    
    parser.add_argument(
        '--output-dir',
        type=Path,
        default=Path('output'),
        help='Output directory for results (default: ./output)'
    )
    
    parser.add_argument(
        '--cache-dir',
        type=Path,
        help='Cache directory for downloaded files (default: <output-dir>/cache)'
    )
    
    # Crawling limits
    parser.add_argument(
        '--max-pages',
        type=int,
        default=500,
        help='Maximum number of pages to crawl (default: 500)'
    )
    
    parser.add_argument(
        '--max-depth',
        type=int,
        help='Maximum crawl depth from seed URL (default: unlimited)'
    )
    
    parser.add_argument(
        '--max-queue-size',
        type=int,
        default=5000,
        help='Maximum URLs in crawl queue (default: 5000)'
    )
    
    parser.add_argument(
        '--max-pdf-mb',
        type=float,
        default=50.0,
        help='Maximum PDF size in MB to download (default: 50)'
    )
    
    # Crawling behavior
    parser.add_argument(
        '--politeness-delay',
        type=float,
        default=0.5,
        help='Seconds to wait between requests (default: 0.5)'
    )
    
    parser.add_argument(
        '--request-timeout',
        type=int,
        default=30,
        help='HTTP request timeout in seconds (default: 30)'
    )
    
    parser.add_argument(
        '--no-respect-robots',
        action='store_true',
        help='Do not respect robots.txt (use with caution)'
    )
    
    parser.add_argument(
        '--user-agent',
        help='Custom user agent string'
    )
    
    # TF-IDF parameters
    parser.add_argument(
        '--max-tfidf-features',
        type=int,
        default=5000,
        help='Maximum TF-IDF features (default: 5000)'
    )
    
    parser.add_argument(
        '--ngram-min',
        type=int,
        default=1,
        help='Minimum n-gram size (default: 1)'
    )
    
    parser.add_argument(
        '--ngram-max',
        type=int,
        default=3,
        help='Maximum n-gram size (default: 3)'
    )
    
    parser.add_argument(
        '--top-k-queries',
        type=int,
        default=10,
        help='Number of top queries to use per cell (default: 10)'
    )
    
    # Value extraction
    parser.add_argument(
        '--context-window',
        type=int,
        default=500,
        help='Characters of context around extracted value (default: 500)'
    )
    
    parser.add_argument(
        '--min-keywords',
        type=int,
        default=1,
        help='Minimum keyword matches required for extraction (default: 1)'
    )
    
    return parser.parse_args()


def main():
    """Main CLI entrypoint."""
    args = parse_args()
    
    try:
        # Create configuration from arguments
        config = RunConfig(
            base_url=args.base_url,
            comune=args.comune,
            years_to_fill=args.years,
            allow_external_official=args.allow_external,
            input_dir=args.input_dir,
            output_dir=args.output_dir,
            cache_dir=args.cache_dir,
            max_pages=args.max_pages,
            max_depth=args.max_depth,
            max_queue_size=args.max_queue_size,
            max_pdf_mb=args.max_pdf_mb,
            politeness_delay=args.politeness_delay,
            request_timeout=args.request_timeout,
            respect_robots=not args.no_respect_robots,
            user_agent=args.user_agent or RunConfig.user_agent,
            max_tfidf_features=args.max_tfidf_features,
            ngram_range=(args.ngram_min, args.ngram_max),
            top_k_queries=args.top_k_queries,
            context_window_chars=args.context_window,
            min_keywords_for_extraction=args.min_keywords
        )
        
        # Run pipeline
        result = run_pipeline(config)
        
        # Check result
        if result.get('error'):
            print(f"\n❌ Pipeline failed: {result['error']}", file=sys.stderr)
            sys.exit(1)
        elif result.get('success'):
            print("\n✅ Pipeline completed successfully!")
            print(f"   - Documents indexed: {result.get('documents', 0)}")
            print(f"   - Sources found: {result.get('sources', 0)}")
            print(f"   - Queries generated: {result.get('queries', 0)}")
            print(f"\nResults saved to: {config.output_dir}")
            sys.exit(0)
        else:
            print("\n⚠️  Pipeline completed with unknown status", file=sys.stderr)
            sys.exit(1)
            
    except KeyboardInterrupt:
        print("\n\n⚠️  Interrupted by user", file=sys.stderr)
        sys.exit(130)
    except Exception as e:
        print(f"\n❌ Fatal error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
