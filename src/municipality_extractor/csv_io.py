"""CSV loading, section detection, and missing cell identification."""

import csv
import logging
from io import StringIO
from pathlib import Path
from typing import List, Optional, Tuple

import pandas as pd

logger = logging.getLogger(__name__)


def load_csv_robust(filepath: Path) -> Tuple[pd.DataFrame, str]:
    """Load CSV with automatic delimiter and encoding detection.
    
    Uses csv.Sniffer to detect delimiter (comma, semicolon, tab).
    Tries multiple encodings: utf-8, latin-1, cp1252.
    
    Args:
        filepath: Path to CSV file
        
    Returns:
        Tuple of (DataFrame, delimiter_used)
        
    Raises:
        ValueError: If file cannot be read with any encoding/delimiter
    """
    if not filepath.exists():
        raise ValueError(f"File not found: {filepath}")
    
    # Try common encodings
    encodings = ['utf-8', 'latin-1', 'cp1252', 'iso-8859-1']
    
    for encoding in encodings:
        try:
            # Read first few lines to detect delimiter
            with open(filepath, 'r', encoding=encoding) as f:
                sample = f.read(8192)  # Read first 8KB
                
            if not sample.strip():
                continue
            
            # Try to detect delimiter using csv.Sniffer
            try:
                sniffer = csv.Sniffer()
                delimiter = sniffer.sniff(sample).delimiter
                logger.info(f"Detected delimiter: '{delimiter}' with encoding: {encoding}")
            except csv.Error:
                # Sniffer failed, try common delimiters
                delimiters = [',', ';', '\t', '|']
                delimiter = None
                max_columns = 0
                
                for delim in delimiters:
                    lines = sample.split('\n')[:5]
                    avg_cols = sum(len(line.split(delim)) for line in lines if line) / max(1, len([l for l in lines if l]))
                    if avg_cols > max_columns:
                        max_columns = avg_cols
                        delimiter = delim
                
                if delimiter:
                    logger.info(f"Guessed delimiter: '{delimiter}' with encoding: {encoding}")
                else:
                    logger.warning(f"Could not detect delimiter for {filepath} with {encoding}")
                    continue
            
            # Try to load the CSV
            try:
                df = pd.read_csv(
                    filepath,
                    sep=delimiter,
                    encoding=encoding,
                    dtype=str,  # Load all as strings to preserve data
                    keep_default_na=False  # Don't convert to NaN yet
                )
                
                if df.empty or len(df.columns) == 1:
                    # Likely wrong delimiter
                    continue
                
                logger.info(f"Successfully loaded CSV with {len(df)} rows, {len(df.columns)} columns")
                return df, delimiter
                
            except Exception as e:
                logger.debug(f"Failed to parse with delimiter '{delimiter}': {e}")
                continue
                
        except UnicodeDecodeError:
            logger.debug(f"Encoding {encoding} failed for {filepath}")
            continue
        except Exception as e:
            logger.debug(f"Unexpected error with {encoding}: {e}")
            continue
    
    raise ValueError(f"Could not load CSV {filepath} with any encoding/delimiter combination")


def is_missing_cell(value: str) -> bool:
    """Check if a cell value is considered missing.
    
    A cell is missing if it:
    - Is empty string or only whitespace
    - Is a common missing value placeholder (NA, N/A, n.d., -, etc.)
    - Is the string "nan" (case-insensitive)
    
    Args:
        value: Cell value as string
        
    Returns:
        True if cell is missing, False otherwise
    """
    if not isinstance(value, str):
        value = str(value)
    
    # Check if empty or whitespace
    value_stripped = value.strip()
    if not value_stripped:
        return True
    
    # Common missing value indicators (case-insensitive)
    missing_indicators = {
        'na', 'n/a', 'n.a.', 'n.d.', 'nd', 'none', 'null', 'nan',
        '-', '--', '---', '?', 'unknown', 'n.r.', 'nr',
        'da compilare', 'mancante', 'non disponibile', 'non pervenuto'
    }
    
    if value_stripped.lower() in missing_indicators:
        return True
    
    # Check if it's just punctuation or special chars
    if all(c in '.,;:-_/\\|()[]{}!? \t\n' for c in value_stripped):
        return True
    
    return False


def detect_missing_cells(df: pd.DataFrame) -> List[Tuple[int, str]]:
    """Find all missing cells in a DataFrame.
    
    Args:
        df: DataFrame to check
        
    Returns:
        List of (row_index, column_name) tuples for missing cells
    """
    missing_cells = []
    
    for idx, row in df.iterrows():
        for col in df.columns:
            value = row[col]
            if is_missing_cell(value):
                missing_cells.append((idx, col))
    
    logger.info(f"Found {len(missing_cells)} missing cells in DataFrame")
    return missing_cells


def detect_section_headers(df: pd.DataFrame, filled_threshold: float = 0.3) -> List[int]:
    """Detect section header rows in a DataFrame.
    
    Section headers are detected using multiple heuristics:
    1. Rows with mostly empty cells (< filled_threshold filled)
    2. Rows where first cell contains section-like text (e.g., "SEZIONE", "PARTE")
    3. Rows that are formatted differently (all caps, different pattern)
    
    Args:
        df: DataFrame to analyze
        filled_threshold: Minimum fraction of cells that must be filled for non-header row
        
    Returns:
        List of row indices that are likely section headers
    """
    section_rows = []
    
    # Section keywords (Italian)
    section_keywords = [
        'sezione', 'parte', 'capitolo', 'titolo', 'categoria',
        'missione', 'programma', 'macroaggregato', 'articolo'
    ]
    
    for idx, row in df.iterrows():
        # Count filled cells
        filled_cells = sum(not is_missing_cell(str(val)) for val in row)
        fill_rate = filled_cells / len(row) if len(row) > 0 else 0
        
        # Heuristic 1: Low fill rate (mostly empty)
        if fill_rate < filled_threshold:
            first_cell = str(row.iloc[0]).strip() if len(row) > 0 else ""
            # But not completely empty
            if first_cell and not is_missing_cell(first_cell):
                section_rows.append(idx)
                logger.debug(f"Row {idx} detected as section (low fill rate: {fill_rate:.2f})")
                continue
        
        # Heuristic 2: First cell contains section keyword
        first_cell = str(row.iloc[0]).strip().lower() if len(row) > 0 else ""
        if any(keyword in first_cell for keyword in section_keywords):
            section_rows.append(idx)
            logger.debug(f"Row {idx} detected as section (keyword in first cell)")
            continue
        
        # Heuristic 3: All caps in first cell (common for headers)
        first_cell_original = str(row.iloc[0]).strip() if len(row) > 0 else ""
        if (len(first_cell_original) > 3 and 
            first_cell_original.isupper() and 
            fill_rate < 0.6):
            section_rows.append(idx)
            logger.debug(f"Row {idx} detected as section (all caps with low fill)")
            continue
    
    logger.info(f"Detected {len(section_rows)} section header rows")
    return section_rows


def get_section_for_row(row_idx: int, section_rows: List[int]) -> Optional[str]:
    """Get the section name for a given row.
    
    Args:
        row_idx: Row index to find section for
        section_rows: List of section header row indices
        
    Returns:
        Section name or None if no section
    """
    # Find the closest section header before this row
    relevant_sections = [s for s in section_rows if s < row_idx]
    
    if not relevant_sections:
        return None
    
    return str(relevant_sections[-1])
