# v2.1 Optimization Summary

## Implementation Complete ✅

All required optimizations from the problem statement have been implemented and tested.

### A) Page-Level Chunking (DONE)

**Files Modified:**
- `src/comune_extractor/pdf_text.py`: Added `extract_text_per_page()`, `save_page_texts()`, `load_page_texts()`
- `src/comune_extractor/indexer.py`: Updated to work with page chunks instead of whole documents
- `src/comune_extractor/retrieval.py`: Updated to retrieve chunks with page_no
- `src/comune_extractor/pipeline.py`: Modified `_build_index()` to create chunks from pages

**Impact:**
- PDFs are now indexed per-page instead of as whole documents
- Default `top_k=8` chunks (more granular than 5-10 whole documents)
- Better precision: relevant pages surface faster in retrieval
- Backward compatible: old indexes auto-convert on load

### B) Query Simplification (VERIFIED)

**Status:** Already implemented correctly in v2.0
- `src/comune_extractor/query_builder.py` generates 1-2 queries max
- No Google operators (site:, filetype:, inurl:, AND, OR)
- Pure local keyword search

### C) Memoization & Early Stopping (DONE)

**Files Modified:**
- `src/comune_extractor/pipeline.py`: Added `extraction_cache` dict in `_fill_csvs()`
- Cache key: `(sha1, page_no, normalized_indicator, year)`
- Early stopping: confidence >= 0.75 (with LLM) or >= 0.85 (heuristic only)

**Impact:**
- Avoid re-extracting same values from same pages
- Stop searching when high-confidence match found
- Significant speed improvement expected

### D) Improved Heuristic Extraction (DONE)

**Files Modified:**
- `src/comune_extractor/extract_heuristics.py`:
  - `normalize_italian_number()`: Added support for negatives, €, percentages
  - `extract_number_with_context()`: Increased window to 300 chars, find keywords first
  - `score_extraction()`: Year proximity optional (0.5 bonus), keyword density prioritized
  - `extract_value_heuristic()`: Pass year parameter for optional scoring
- Snippet limited to 240 chars

**Impact:**
- Works even when year not near the value (common in Italian budgets)
- Better number parsing: handles `(1.234,56)`, `€ 1.234,56`, `12,5%`
- More readable snippets in sources

### E) Enhanced Source Traceability (DONE)

**Files Modified:**
- `src/comune_extractor/csv_io.py`: Updated `create_sources_csv()` columns
- `src/comune_extractor/pipeline.py`: Pass page_no, filename, doc_id to sources

**New columns in sources_long.csv:**
- `page_no`: Page number where value was found
- `filename`: Original PDF filename
- `doc_id`: SHA1 hash for document identification
- `snippet`: 240-char excerpt (was 200)

**Impact:**
- Full traceability: url + filename + page_no + snippet
- Easy to verify extracted values manually

### F) Fixed Reporting Metrics (DONE)

**Files Modified:**
- `src/comune_extractor/reporting.py`: 
  - Show "total_chunks" instead of "total_docs"
  - Add memoization cache hits metric
  - Update headers to clarify chunk-based indexing

**Impact:**
- Clearer metrics showing page chunks indexed
- Cache hit tracking for optimization analysis

## Testing

**76 tests passing:**
- 7 tests for page chunking (`test_chunking.py`)
- 16 tests for query building (`test_query_builder_local.py`)
- 19 tests for extraction without year (`test_extraction_without_year.py`)
- 7 tests for sources with page_no (`test_sources_page.py`)
- 27 existing tests (numbers, year detection, caching)

**Run tests:**
```bash
cd /home/runner/work/estrazione_dati_comune/estrazione_dati_comune
PYTHONPATH=/home/runner/work/estrazione_dati_comune/estrazione_dati_comune/src \
  python -m pytest tests/test_chunking.py tests/test_query_builder_local.py \
  tests/test_extraction_without_year.py tests/test_sources_page.py \
  tests/test_numbers_it.py tests/test_year_detect.py tests/test_cache_behavior.py -v
```

## Key Benefits

### 1. Speed Improvements
- **Memoization**: Avoid re-extraction of same (doc, page, indicator, year)
- **Early stopping**: Stop at confidence 0.75-0.85 instead of checking all chunks
- **Target**: <120s fill time (vs 722s baseline)

### 2. Coverage Improvements
- **Keyword-first extraction**: Works without year proximity
- **Page-level chunks**: More precise retrieval
- **Better number parsing**: Handles more Italian formats
- **Target**: >=10% coverage (vs 0.7% baseline)

### 3. Traceability
- **Page numbers**: Know exactly which page contains the value
- **Snippets**: 240-char context showing the match
- **doc_id**: SHA1 for document identification

## Acceptance Criteria Status

✅ 1. **Chunking**: PDFs indexed per-page, retrieval returns chunks with page_no
✅ 2. **Queries**: 1-2 queries max, no Google operators
✅ 3. **Extraction**: Works on chunks, memoization, early stopping
✅ 4. **Heuristics**: Keyword-first, year optional, better number parsing
✅ 5. **Sources**: url+filename+page_no+snippet in sources_long.csv
✅ 6. **Reporting**: Shows chunks, cache hits, coherent metrics
✅ 7. **Tests**: 76 tests passing

## Ready for Testing

The implementation is complete and ready for real-world testing on Vigone dataset:

**Expected improvements:**
- Fill time: 722s → <120s (6x faster)
- Coverage: 1/137 (0.7%) → >=10/137 (7%+) or 10x improvement

**To run:**
```bash
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

Check:
- `vigone_output/run_report.md`: Time and coverage metrics
- `vigone_output/sources_long.csv`: Verify page_no, snippet, doc_id present
- `vigone_output/queries_generated.csv`: Verify no Google operators
