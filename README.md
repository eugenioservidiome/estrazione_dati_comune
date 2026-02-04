# Estrazione Dati Comune

**Production-ready Python package** for automated extraction of missing data from Italian municipality CSV files using web crawling, BM25 document retrieval, and intelligent value extraction with optional LLM support.

## 🎯 Overview

**Version 2.0** - Complete refactoring with enterprise-grade features:

1. **Focused web crawler** with sitemap.xml support, robots.txt compliance, and BFS traversal
2. **SQLite catalog** for PDF/text tracking with SHA1 deduplication
3. **PyMuPDF primary extraction** with pdfplumber fallback (3x faster)
4. **Automatic year detection** from URLs, filenames, and document content
5. **BM25 indexing** (replaced TF-IDF) with incremental updates and disk persistence
6. **Simplified query generation** (1-2 queries per cell, not 8-20)
7. **Optional LLM extraction** via OpenAI API with structured outputs and JSON cache
8. **Full caching** - second run: 0 redownloads, 0 re-extractions
9. **Comprehensive reporting** with run_report.md and audit CSVs

## 🚀 Quick Start

### Installation

```bash
# Clone repository
git clone https://github.com/yourusername/estrazione_dati_comune.git
cd estrazione_dati_comune

# Install dependencies
pip install -r requirements.txt
```

### Basic Usage (Local)

```bash
# Run extraction
python -m comune_extractor run \
  --base-url https://comune.vigone.to.it/ \
  --comune Vigone \
  --years 2023 2024 \
  --input-dir ./vigone_csv \
  --output-dir ./vigone_output \
  --workspace ./workspace \
  --max-pages 500 \
  --max-pdfs 2000
```

### Advanced Usage (with LLM)

```bash
# Set OpenAI API key
export OPENAI_API_KEY="sk-..."

# Run with LLM extraction
python -m comune_extractor run \
  --base-url https://comune.vigone.to.it/ \
  --comune Vigone \
  --years 2023 2024 \
  --input-dir ./vigone_csv \
  --output-dir ./vigone_output \
  --workspace ./workspace \
  --use-llm \
  --openai-model gpt-4o-mini \
  --concurrency-download 8 \
  --concurrency-extract 4
```

### Google Colab

Open `estrazione_dati_comune.ipynb` in Google Colab for interactive usage (uses v2.0 package).

## ✨ Key Features (v2.0)

### 🗄️ SQLite Catalog
- **Three tables**: pdfs, texts, llm_cache
- **SHA1 deduplication** - same PDF from different URLs = 1 download
- **Metadata tracking**: URL, filename, year, size, extractor, timestamps
- **Cache persistence** across runs

### 📄 Dual PDF Extraction Strategy
- **PyMuPDF (fitz)** as primary extractor (3x faster)
- **pdfplumber** as fallback if PyMuPDF fails
- **Disk caching** of extracted text
- **Fast first-page extraction** for year detection

### 📅 Automatic Year Detection
1. Try regex on URL (e.g., `/2023/bilancio.pdf`)
2. Try regex on filename (e.g., `bilancio_2023.pdf`)
3. Extract first 2 pages, search for year pattern
4. Save PDFs in `data/{comune}/{year}/pdf/` or `unknown/pdf/`

### 🔍 BM25 Indexing (not TF-IDF)
- **rank_bm25** library for state-of-the-art ranking
- **Incremental updates** - add documents without full rebuild
- **Disk persistence** with pickle
- **Year filtering** - only index documents with detected_year in target years

### 🎯 Simplified Query Generation
- **1-2 queries per cell** (not 8-20 Google-style queries)
- **Canonical query** + optional variant with synonyms
- **Preserves categorization** logic from v1
- **Full audit trail** in queries_generated.csv

### 🤖 Optional LLM Extraction
- **OpenAI Responses API** with Structured Outputs (strict=true)
- **Intelligent chunking**: find year + keyword positions, extract 1500-3000 chars
- **JSON schema**: {value, unit, year, evidence, confidence}
- **SQLite + JSON caching** - never call API twice for same request
- **Confidence validation**: >= 0.7 and year must match
- **Graceful fallback** to heuristics if no API key or LLM fails

### 🕷️ Advanced Crawler
- **Sitemap.xml support** - try first from robots.txt or /sitemap.xml
- **BFS traversal** limited to domain
- **Politeness**: crawl-delay from robots.txt, configurable default
- **Focus on PDFs**, HTML optional

### 🇮🇹 Italian Number Normalization
- Handles `1.234,56` → 1234.56
- Handles `1 234,56` → 1234.56
- Regex extraction from text with context scoring

### 📁 Folder Structure
Auto-created workspace layout:
```
data/{comune}/{anno}/pdf/     # Year-specific PDFs
data/{comune}/{anno}/text/    # Extracted text
data/{comune}/{anno}/llm/     # LLM cache
data/{comune}/index/          # BM25 index files
data/{comune}/unknown/pdf/    # PDFs without detected year
data/{comune}/catalog.sqlite  # SQLite catalog
```

## 📤 Output Files

All outputs saved to `output_dir`:

1. **`*_filled.csv`** - Original CSVs with filled cells (or 'NOT_FOUND')
2. **`sources_long.csv`** - Full traceability (indicator, year, value, url, snippet, confidence, method)
3. **`queries_generated.csv`** - Query audit (indicator, category, year, query_1, query_2)
4. **`run_report.md`** - Comprehensive report with:
   - Comune, domain, years
   - PDFs found/downloaded, cache hit rates
   - Texts extracted, cache hit rates
   - Documents indexed per year
   - Cells filled, coverage %
   - NOT_FOUND list (top 50)
   - Time per step (crawl/download/extract/index/fill)

## 📖 Usage

### Command Line Interface

```bash
# See all options
python -m comune_extractor run --help

# Basic extraction
python -m comune_extractor run \
  --base-url https://comune.vigone.to.it/ \
  --comune Vigone \
  --years 2023 2024 \
  --input-dir ./vigone_csv \
  --output-dir ./vigone_output \
  --workspace ./workspace

# With custom crawl limits
python -m comune_extractor run \
  --base-url https://comune.vigone.to.it/ \
  --comune Vigone \
  --years 2023 2024 \
  --input-dir ./vigone_csv \
  --output-dir ./vigone_output \
  --max-pages 1000 \
  --max-pdfs 3000 \
  --concurrency-download 12

# With LLM extraction
python -m comune_extractor run \
  --base-url https://comune.vigone.to.it/ \
  --comune Vigone \
  --years 2023 2024 \
  --input-dir ./vigone_csv \
  --output-dir ./vigone_output \
  --use-llm \
  --openai-api-key sk-... \
  --openai-model gpt-4o-mini \
  --llm-confidence-threshold 0.7

# Load from YAML config
python -m comune_extractor run --config config.yaml
```

### Python API

```python
from comune_extractor import Config, Pipeline

# Create configuration
config = Config(
    base_url='https://comune.vigone.to.it/',
    comune='Vigone',
    years=[2023, 2024],
    input_dir='./vigone_csv',
    output_dir='./vigone_output',
    workspace='./workspace',
    max_pages=500,
    max_pdfs=2000,
    use_llm=False
)

# Run pipeline
pipeline = Pipeline(config)
pipeline.run()
```

### YAML Configuration

Create `config.yaml`:

```yaml
base_url: https://comune.vigone.to.it/
comune: Vigone
years: [2023, 2024]
input_dir: ./vigone_csv
output_dir: ./vigone_output
workspace: ./workspace
max_pages: 500
max_pdfs: 2000
concurrency_download: 8
concurrency_extract: 4
use_llm: false
allow_external: false
```

Then run:

```bash
python -m comune_extractor run --config config.yaml
```

## 🛠️ Installation

### Requirements

- Python 3.10+
- pip

### Install Dependencies

```bash
pip install -r requirements.txt
```

### Core Dependencies

- **pandas** - CSV manipulation
- **requests** - HTTP client
- **beautifulsoup4** - HTML parsing
- **PyMuPDF (fitz)** - Primary PDF extraction (NEW in v2.0)
- **pdfplumber** - Fallback PDF extraction
- **rank-bm25** - BM25 indexing (NEW in v2.0, replaces scikit-learn TF-IDF)
- **PyYAML** - YAML config support (NEW in v2.0)
- **tqdm** - Progress bars
- **lxml** - XML/sitemap parsing

### Optional Dependencies

- **openai** - LLM extraction (NEW in v2.0, optional)

## 🏗️ Architecture (v2.0)

```
comune_extractor/
├── __init__.py         # Package exports
├── __main__.py         # CLI entrypoint
├── config.py           # Config dataclass (env/cli/yaml)
├── paths.py            # Folder layout management
├── catalog.py          # SQLite catalog (pdfs/texts/llm_cache)
├── robots.py           # robots.txt parser + politeness
├── crawler.py          # Sitemap + BFS crawler
├── pdf_store.py        # Download with SHA1 dedup
├── pdf_text.py         # PyMuPDF primary, pdfplumber fallback
├── year_detect.py      # Year detection (URL/filename/text)
├── indexer.py          # BM25 index with disk persistence
├── retrieval.py        # Query retrieval on index
├── extract_heuristics.py  # Regex + Italian number normalization
├── query_builder.py    # 1-2 queries per cell (not 8-20)
├── csv_io.py           # CSV I/O + missing cell detection
├── llm_extract.py      # Optional OpenAI integration
├── external_sources.py # Templates for ISTAT/MEF/ISPRA/BDAP
├── reporting.py        # run_report.md generation
└── pipeline.py         # End-to-end orchestration
```

### Data Flow

```
1. Setup
   └─> Config → ensure directories → init SQLite catalog

2. Crawl
   ├─> Load robots.txt → extract sitemap URLs
   ├─> Process sitemap for PDFs
   └─> BFS crawl if needed (up to max_pages/max_pdfs)

3. Download PDFs (parallel)
   ├─> Check catalog by URL (cache hit?)
   ├─> Download to temp → compute SHA1
   ├─> Check catalog by SHA1 (dedup?)
   ├─> Detect year (URL → filename → first 2 pages)
   └─> Move to data/{comune}/{year}/pdf/{sha1}_{name}.pdf

4. Extract Text (parallel)
   ├─> Check catalog (text exists?)
   ├─> Try PyMuPDF → fallback pdfplumber
   └─> Save to data/{comune}/{year}/text/{sha1}.txt

5. Build Index
   ├─> Try load existing index
   ├─> If not exist: gather all texts for target years
   ├─> Build BM25 index
   └─> Save to data/{comune}/index/

6. Fill CSVs
   ├─> Load CSV → detect missing cells
   ├─> Generate 1-2 queries per cell
   └─> For each cell:
       ├─> Retrieve top_k docs (BM25)
       ├─> Try LLM extraction (if enabled)
       ├─> Fallback to heuristic extraction
       ├─> Try external sources (if enabled)
       └─> Update cell (value or 'NOT_FOUND')

7. Output
   ├─> Save filled CSVs
   ├─> Save sources_long.csv
   ├─> Save queries_generated.csv
   └─> Generate run_report.md
```

## 📋 Configuration Options

All configurable via CLI arguments, environment variables, or YAML file.

### Core Settings
- `base_url` - Municipality website URL (required)
- `comune` - Municipality name (required)
- `years` - List of years to extract (required, e.g., [2023, 2024])

### Directories
- `input_dir` - Input CSV directory (default: ./input)
- `output_dir` - Output directory (default: ./output)
- `workspace` - Workspace for data/cache (default: ./workspace)

### Crawler Settings
- `max_pages` - Max pages to crawl (default: 500)
- `max_pdfs` - Max PDFs to download (default: 2000)
- `respect_robots` - Respect robots.txt (default: true)
- `crawl_delay` - Delay between requests in seconds (default: 1.0)
- `user_agent` - Custom user agent string

### Processing Settings
- `concurrency_download` - Parallel downloads (default: 8)
- `concurrency_extract` - Parallel text extractions (default: 4)
- `top_k` - Top K documents to retrieve (default: 10)
- `min_score` - Minimum BM25 score threshold (default: 0.0)

### LLM Settings (Optional)
- `use_llm` - Enable LLM extraction (default: false)
- `openai_api_key` - OpenAI API key (or set OPENAI_API_KEY env var)
- `openai_model` - Model to use (default: gpt-4o-mini)
- `llm_confidence_threshold` - Min confidence for LLM results (default: 0.7)
- `llm_max_chunks_per_doc` - Max chunks per document (default: 3)
- `llm_max_docs` - Max documents to process with LLM (default: 3)
- `llm_chunk_size` - Chunk size in chars (default: 2000)

### External Sources (Optional)
- `allow_external` - Enable external data sources (default: false)

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
# Install package in development mode
pip install -e .

# Run all tests
pytest tests/ -v

# Run specific test modules
pytest tests/test_numbers_it.py -v
pytest tests/test_year_detect.py -v
pytest tests/test_cache_behavior.py -v

# Run with coverage
pytest tests/ --cov=comune_extractor --cov-report=html
```

### Test Coverage

**New in v2.0:**
- `test_numbers_it.py` - Italian number parsing and normalization
- `test_year_detect.py` - Year detection from URLs, filenames, text
- `test_cache_behavior.py` - Verify catalog caching works correctly

**Existing from v1:**
- URL normalization and validation
- Query categorization and building
- CSV missing cell detection
- Value extraction with confidence scoring

## 🔒 Legal & Privacy

### robots.txt Compliance
- **Default: Respects robots.txt** including User-agent directives and Crawl-delay
- Can be disabled with `--no-respect-robots` (not recommended)
- Always identifies with user agent: `comune_extractor/2.0 (Educational/Research)`

### Data Privacy
- **No external API calls by default** - Everything runs locally with BM25
- **LLM is opt-in** - Only enabled with `--use-llm` flag
- **No data sent to third parties** unless LLM enabled
- **Full traceability** - Every value linked to source document + method (heuristic/llm/external)
- **Cached downloads** - Respects website bandwidth

### Responsible Use
- Use politeness delays (default 1.0s, configurable)
- Respect crawl limits (max_pages, max_pdfs)
- Review robots.txt manually for sensitive sites
- This tool is for educational/research purposes on public data
- Always verify extracted values manually

## ⚠️ Limitations & Considerations

- **Extraction accuracy** depends on document quality and BM25 relevance
- **Year detection** may fail for documents without clear year indicators  
- **LLM costs** - OpenAI API usage incurs costs (disabled by default)
- **Performance** scales with site size and number of CSVs/years
- **Italian language focus** - Optimized for Italian municipalities
- **Manual validation recommended** - Always verify critical values

## 🤝 Contributing

Contributions welcome! Areas for improvement:
- Additional query templates for specific indicators
- Better year detection heuristics
- OCR support for scanned PDFs
- More sophisticated NLP for value extraction
- Multi-language support
- Additional external source integrations (ISTAT, MEF, ISPRA APIs)

## 📄 License

Open source project for Italian public administration transparency and civic tech.

## 🆕 What's New in v2.0

### Breaking Changes
- **Package renamed**: `municipality_extractor` → `comune_extractor`
- **BM25 instead of TF-IDF**: Better ranking, different index format
- **SQLite catalog**: Replaces simple file-based caching
- **Simplified queries**: 1-2 per cell instead of 8-20

### Major Features
1. **PyMuPDF primary extraction** - 3x faster than pdfplumber-only
2. **SQLite catalog** - Professional-grade deduplication and caching
3. **Automatic year detection** - From URLs, filenames, or document content
4. **BM25 indexing** - State-of-the-art ranking (replaces TF-IDF)
5. **Optional LLM extraction** - OpenAI API with structured outputs
6. **Comprehensive caching** - Second run: 0 redownloads, 0 re-extractions
7. **Enhanced reporting** - Detailed run_report.md with cache hit rates

### Migration from v1 (municipality_extractor)

**CLI Changes:**
```bash
# Old (v1)
PYTHONPATH=src python -m municipality_extractor \
  --base-url URL --comune NAME --input-dir DIR --output-dir DIR

# New (v2)
python -m comune_extractor run \
  --base-url URL --comune NAME --years 2023 2024 \
  --input-dir DIR --output-dir DIR --workspace WORKSPACE
```

**Python API Changes:**
```python
# Old (v1)
from municipality_extractor import RunConfig, run_pipeline
config = RunConfig(base_url=..., comune=..., years_to_fill=[...])
run_pipeline(config)

# New (v2)
from comune_extractor import Config, Pipeline
config = Config(base_url=..., comune=..., years=[...])
Pipeline(config).run()
```

**Data Migration:**
- v1 cache is not compatible with v2 SQLite catalog
- Run fresh extraction with v2 (caching will work on subsequent runs)
- v1 package (`municipality_extractor`) remains in `src/` for reference

### Performance Improvements
- **PDF extraction**: 3x faster (PyMuPDF vs pdfplumber-only)
- **Query generation**: 90% reduction (1-2 vs 8-20 queries)
- **Caching**: Perfect cache hits on second run (0 redownloads)
- **Indexing**: Incremental updates, disk persistence

## 📞 Support

For issues, questions, or suggestions, please open an issue on GitHub.

---

**comune_extractor v2.0** - Production-ready data extraction for Italian municipalities