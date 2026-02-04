# Estrazione Dati Comune

**Production-ready Python package** for automated extraction of missing data from Italian municipality CSV files using web crawling, TF-IDF document retrieval, and intelligent value extraction.

## 🎯 Overview

This project provides both a **Python package** and a **Google Colab notebook** for:

1. **Web crawling** municipal websites with robots.txt compliance, sitemap support, and PDF handling
2. **Automated query generation** using 25+ category templates with synonym expansion
3. **TF-IDF document retrieval** for intelligent document ranking
4. **Value extraction** with confidence scoring and Italian number format support
5. **CSV gap filling** with full traceability and audit logging

## 🚀 Quick Start

### Python Package (Local or Server)

```bash
# Install dependencies
pip install -r requirements.txt

# Run extraction
PYTHONPATH=src python -m municipality_extractor \
  --base-url https://www.comune.example.it \
  --comune "Example" \
  --input-dir ./input_csvs \
  --output-dir ./output \
  --years 2023 2024
```

### Google Colab Notebook

Open `estrazione_dati_comune.ipynb` in Google Colab and run all cells. The notebook is now a thin wrapper around the Python package.

## ✨ Key Features

### 🔍 Intelligent Query Generation
- **25 internal categories** for municipal data (Delibere CC/GC, Sedute, Personale, Patrimonio, Rifiuti, etc.)
- **7 external categories** for official sources (ISTAT, ISPRA, MEF, BDAP) - optional
- **Synonym expansion** for better recall
- **Dual query generation**: audit queries (with operators) + semantic queries (for TF-IDF)
- **Deterministic priority scoring** (1-10) based on template features

### 🕷️ Robust Web Crawling
- **Automatic retry** with exponential backoff
- **robots.txt compliance** (configurable)
- **Sitemap.xml parsing** for seed URLs
- **Content-type validation** (PDF vs HTML)
- **Disk caching** with SHA1 URL hashing and metadata (ETag, Last-Modified)
- **URL normalization** (fragment removal, trailing slash handling)
- **Crawl limits**: max_pages, max_depth, max_queue_size, max_pdf_mb

### 📊 Advanced Text & Value Extraction
- **HTML**: trafilatura + BeautifulSoup4 fallback with boilerplate removal
- **PDF**: pdfplumber with page-level error handling
- **Italian number parsing**: handles "1.234,56" format, percentages, currency
- **Confidence scoring** (0-1) based on keyword presence, year context, value validity
- **Minimum extraction requirements**: year + keywords in context window

### 🎯 TF-IDF Document Retrieval
- **Robust indexing** with automatic small-corpus handling
- **Stable doc_id** with metadata mapping
- **Italian stopwords** (optional, minimal internal list)
- **Cosine similarity ranking** for document search

### 📁 CSV Processing
- **Smart delimiter detection** using csv.Sniffer
- **Multiple encoding support** (UTF-8, Latin-1, Windows-1252)
- **Advanced section header detection** (not just fill-rate heuristic)
- **Missing cell detection** with configurable placeholders (n.d., N/A, -, etc.)

## 📤 Output Files

All outputs saved to `output_dir`:

1. **`*_filled.csv`** - Original CSVs with filled cells
2. **`sources_long.csv`** - Full traceability (URL, snippet, confidence for each value)
3. **`queries_generated.csv`** - Complete query audit (input_file, section, row_label, col_year, audit_query, semantic_query, priority, category)
4. **`run_report.md`** - Execution report with coverage statistics and NOT_FOUND items

## 📖 Usage

### Command Line Interface

```bash
# Basic usage
PYTHONPATH=src python -m municipality_extractor \
  --base-url https://www.comune.vigone.to.it \
  --comune "Vigone" \
  --input-dir ./input_csvs \
  --output-dir ./output

# Advanced usage with custom parameters
PYTHONPATH=src python -m municipality_extractor \
  --base-url https://www.comune.vigone.to.it \
  --comune "Vigone" \
  --years 2023 2024 2025 \
  --allow-external \
  --max-pages 1000 \
  --politeness-delay 1.0 \
  --no-respect-robots \
  --input-dir ./data/csvs \
  --output-dir ./results \
  --cache-dir ./cache

# See all options
PYTHONPATH=src python -m municipality_extractor --help
```

### Python API

```python
from municipality_extractor import RunConfig, run_pipeline

# Create configuration
config = RunConfig(
    base_url='https://www.comune.vigone.to.it',
    comune='Vigone',
    years_to_fill=[2023, 2024],
    allow_external_official=False,
    input_dir='./input_csvs',
    output_dir='./output',
    max_pages=500,
    politeness_delay=0.5
)

# Run extraction pipeline
results = run_pipeline(config)
```

### Google Colab

1. Open `estrazione_dati_comune.ipynb` in Google Colab
2. Run the first cell to install dependencies
3. Configure parameters in the second cell
4. Run all cells

The notebook now imports and uses the `municipality_extractor` package as a thin wrapper.

## 🛠️ Installation

### Requirements

- Python 3.10+
- pip

### Install Dependencies

```bash
pip install -r requirements.txt
```

### Dependencies

- **pandas** - CSV manipulation
- **requests** - HTTP client
- **beautifulsoup4** - HTML parsing
- **trafilatura** - HTML text extraction
- **scikit-learn** - TF-IDF vectorization
- **pdfplumber** - PDF text extraction
- **tqdm** - Progress bars
- **lxml** - XML parsing (for sitemap)
- **rapidfuzz** - Fuzzy string matching (future use)

## 🏗️ Architecture

```
municipality_extractor/
├── config.py           # RunConfig dataclass with validation
├── utils.py            # URL normalization, Italian number parsing, logging
├── crawler.py          # WebCrawler with caching & robots.txt
├── extractors.py       # HTML & PDF text extraction
├── query_builder.py    # Template-based query generation
├── csv_io.py           # CSV loading & section detection
├── indexing.py         # TF-IDF document indexing
├── value_extraction.py # Confidence-based value extraction
├── pipeline.py         # Main orchestration
└── __main__.py         # CLI entrypoint
```

### Data Flow

```
1. Configuration
   └─> RunConfig (base_url, years, directories, limits)

2. Web Crawling
   ├─> Crawl site (robots.txt, sitemap, dedup)
   ├─> Download HTML/PDF with caching
   └─> Extract text (trafilatura + pdfplumber)

3. Indexing
   └─> Build TF-IDF index from documents

4. CSV Processing (for each CSV file)
   ├─> Load & detect missing cells
   ├─> Detect section headers
   └─> For each missing cell:
       ├─> Categorize cell → select query templates
       ├─> Build queries (audit + semantic)
       ├─> Search documents (TF-IDF cosine similarity)
       └─> Extract value with confidence scoring

5. Output
   ├─> Save filled CSVs
   ├─> Save sources with traceability
   ├─> Save query audit log
   └─> Generate run report
```

## 📋 Configuration Options

All configurable via CLI or `RunConfig`:

### Core Settings
- `base_url` - Municipality website URL (required)
- `comune` - Municipality name (optional, for query generation)
- `years_to_fill` - List of years to extract (default: [2023, 2024])
- `allow_external_official` - Allow external official sources (ISTAT, MEF, etc.)

### Directories
- `input_dir` - Input CSV directory (default: ./input)
- `output_dir` - Output directory (default: ./output)
- `cache_dir` - Cache directory (default: output_dir/cache)

### Crawling Limits
- `max_pages` - Maximum pages to crawl (default: 500)
- `max_depth` - Maximum crawl depth (default: None = unlimited)
- `max_queue_size` - Maximum URLs in queue (default: 5000)
- `max_pdf_mb` - Maximum PDF size in MB (default: 50.0)

### Crawling Behavior
- `politeness_delay` - Seconds between requests (default: 0.5)
- `request_timeout` - HTTP timeout in seconds (default: 30)
- `respect_robots` - Respect robots.txt (default: True)
- `user_agent` - Custom user agent string

### TF-IDF Parameters
- `max_tfidf_features` - Max features for vectorizer (default: 5000)
- `ngram_range` - N-gram range tuple (default: (1, 3))
- `top_k_queries` - Top K queries to use per cell (default: 10)

### Value Extraction
- `context_window_chars` - Context chars around value (default: 500)
- `min_keywords_for_extraction` - Min keyword matches (default: 1)

## 🎓 Supported Categories

### Internal Categories (25)
- **Governance**: Delibere CC/GC, Sedute CC/GC, Personale, Struttura, Servizio Civile
- **Financial**: Patrimonio, Debiti, Risultato Economico, Investimenti per Missione
- **Services**: Polizia Locale, Art. 208 CDS, Edilizia, Manutenzioni, Biblioteca
- **Waste**: Raccolta Differenziata, Frazioni Rifiuti
- **Projects**: PNRR, Opere Pubbliche
- **Social**: Social Media accounts

### External Categories (7, optional)
- **ISTAT**: Popolazione, Nati/Morti, Stranieri
- **ISPRA**: Rifiuti Urbani
- **MEF**: IMU, IRPEF
- **BDAP**: Dati Contabili

## 🧪 Testing

Run the test suite:

```bash
# Run all tests
PYTHONPATH=src python -m pytest tests/ -v

# Run specific test file
PYTHONPATH=src python -m pytest tests/test_query_builder.py -v

# Run with coverage
PYTHONPATH=src python -m pytest tests/ --cov=municipality_extractor --cov-report=html
```

Test coverage includes:
- URL normalization and validation
- Italian number parsing
- Query categorization and building
- CSV missing cell detection
- Value extraction with confidence scoring

## 🔒 Security & Privacy

- **No external API calls** - Everything runs locally with TF-IDF
- **No search engine queries** - Query strings are for audit only
- **Controlled scope** - Default: domain-only crawling
- **robots.txt compliance** - Respects crawler directives
- **Full traceability** - Every value linked to source document
- **Cached downloads** - Avoids re-downloading content

## ⚠️ Limitations & Considerations

- **Extraction accuracy** depends on document quality and template relevance
- **Performance** scales with site size and number of CSVs
- **Italian language focus** - Templates and patterns optimized for Italian municipalities
- **Manual validation recommended** - Check confidence scores and review low-confidence values

## 🤝 Contributing

Contributions welcome! Areas for improvement:
- Additional query templates for specific data types
- Better section header detection heuristics
- OCR support for scanned PDFs
- More sophisticated NLP for value extraction
- Multi-language support

## 📄 License

Open source project for Italian public administration transparency and civic tech.

## 🆕 Changes from Original Notebook

### Breaking Changes
None - the package maintains full functional compatibility with the original notebook.

### Improvements
1. **Modular architecture** - Clean separation of concerns
2. **Error handling** - No silent failures, comprehensive logging
3. **Caching system** - Disk-based with metadata
4. **Configuration** - Validated dataclass instead of global variables
5. **Testing** - 84 unit tests with pytest
6. **CLI** - Full command-line interface
7. **Type hints** - Complete type annotations
8. **Documentation** - Docstrings and README
9. **Synonym expansion** - Actually uses SYNONYMS dictionary
10. **Dual queries** - Audit + semantic query generation
11. **Confidence scoring** - Value extraction includes confidence metric
12. **Better CSV parsing** - csv.Sniffer + multiple encodings
13. **Robust TF-IDF** - Handles small corpus edge cases
14. **Security** - No hardcoded credentials, respects robots.txt

### Migration Guide

**From Colab Notebook:**
The notebook now imports the package. Update the parameters cell and run all cells as before.

**From Command Line:**
```bash
# Old: edit variables in notebook
# New: pass as CLI arguments
PYTHONPATH=src python -m municipality_extractor \
  --base-url <URL> \
  --comune <NAME> \
  --input-dir <PATH> \
  --output-dir <PATH>
```

## 📞 Support

For issues, questions, or suggestions, please open an issue on GitHub.