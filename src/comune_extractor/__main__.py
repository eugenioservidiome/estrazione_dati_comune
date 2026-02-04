"""CLI interface for comune_extractor."""

import argparse
from pathlib import Path
from .config import Config
from .pipeline import Pipeline


def main():
    parser = argparse.ArgumentParser(
        description="Extract data from Italian municipality websites",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Basic extraction
  python -m comune_extractor run \\
    --base-url https://comune.vigone.to.it/ \\
    --comune Vigone \\
    --years 2023 2024 \\
    --input-dir ./vigone_csv \\
    --output-dir ./vigone_output

  # With LLM and external sources
  python -m comune_extractor run \\
    --base-url https://comune.vigone.to.it/ \\
    --comune Vigone \\
    --years 2023 2024 \\
    --input-dir ./vigone_csv \\
    --output-dir ./vigone_output \\
    --use-llm \\
    --allow-external

  # Load config from YAML
  python -m comune_extractor run --config config.yaml
"""
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Command to run')
    
    # Run command
    run_parser = subparsers.add_parser('run', help='Run extraction pipeline')
    
    # Config source
    run_parser.add_argument('--config', type=Path, help='Load config from YAML file')
    
    # Target configuration
    run_parser.add_argument('--base-url', type=str, help='Base URL of municipality website')
    run_parser.add_argument('--comune', type=str, help='Municipality name')
    run_parser.add_argument('--years', type=int, nargs='+', help='Years to extract (e.g., 2023 2024)')
    
    # Directories
    run_parser.add_argument('--input-dir', type=Path, default='./input',
                          help='Directory with input CSV files (default: ./input)')
    run_parser.add_argument('--output-dir', type=Path, default='./output',
                          help='Directory for output files (default: ./output)')
    run_parser.add_argument('--workspace', type=Path, default='./workspace',
                          help='Workspace directory for data/cache (default: ./workspace)')
    
    # Crawler settings
    run_parser.add_argument('--max-pages', type=int, default=500,
                          help='Maximum pages to crawl (default: 500)')
    run_parser.add_argument('--max-pdfs', type=int, default=2000,
                          help='Maximum PDFs to download (default: 2000)')
    run_parser.add_argument('--no-respect-robots', action='store_true',
                          help='Ignore robots.txt (not recommended)')
    run_parser.add_argument('--crawl-delay', type=float, default=1.0,
                          help='Delay between requests in seconds (default: 1.0)')
    
    # Extraction settings
    run_parser.add_argument('--concurrency-download', type=int, default=8,
                          help='Concurrent downloads (default: 8)')
    run_parser.add_argument('--concurrency-extract', type=int, default=4,
                          help='Concurrent text extractions (default: 4)')
    
    # Indexing settings
    run_parser.add_argument('--top-k', type=int, default=10,
                          help='Top K documents to retrieve (default: 10)')
    run_parser.add_argument('--min-score', type=float, default=0.0,
                          help='Minimum BM25 score (default: 0.0)')
    
    # LLM settings
    run_parser.add_argument('--use-llm', action='store_true',
                          help='Enable LLM-based extraction (requires OpenAI API key)')
    run_parser.add_argument('--openai-api-key', type=str,
                          help='OpenAI API key (or set OPENAI_API_KEY env var)')
    run_parser.add_argument('--openai-model', type=str, default='gpt-4o-mini',
                          help='OpenAI model to use (default: gpt-4o-mini)')
    run_parser.add_argument('--llm-confidence-threshold', type=float, default=0.7,
                          help='Minimum confidence for LLM results (default: 0.7)')
    
    # External sources
    run_parser.add_argument('--allow-external', action='store_true',
                          help='Enable external data sources (ISTAT, MEF, etc.)')
    
    args = parser.parse_args()
    
    if args.command == 'run':
        # Load config
        if args.config:
            config = Config.from_yaml(args.config)
            # Override with CLI args if provided
            if args.base_url:
                config.base_url = args.base_url
            if args.comune:
                config.comune = args.comune
            if args.years:
                config.years = args.years
        else:
            # Build config from CLI args
            if not args.base_url or not args.comune or not args.years:
                parser.error("--base-url, --comune, and --years are required (or use --config)")
            
            config = Config(
                base_url=args.base_url,
                comune=args.comune,
                years=args.years,
                input_dir=args.input_dir,
                output_dir=args.output_dir,
                workspace=args.workspace,
                max_pages=args.max_pages,
                max_pdfs=args.max_pdfs,
                respect_robots=not args.no_respect_robots,
                crawl_delay=args.crawl_delay,
                concurrency_download=args.concurrency_download,
                concurrency_extract=args.concurrency_extract,
                top_k=args.top_k,
                min_score=args.min_score,
                use_llm=args.use_llm,
                openai_api_key=args.openai_api_key,
                openai_model=args.openai_model,
                llm_confidence_threshold=args.llm_confidence_threshold,
                allow_external=args.allow_external,
            )
        
        # Run pipeline
        pipeline = Pipeline(config)
        pipeline.run()
    
    else:
        parser.print_help()


if __name__ == '__main__':
    main()
