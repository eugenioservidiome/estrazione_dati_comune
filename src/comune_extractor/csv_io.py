"""CSV I/O: load CSVs, detect missing cells, write outputs."""

import pandas as pd
from pathlib import Path
from typing import List, Tuple, Dict


def load_csv(csv_path: Path) -> pd.DataFrame:
    """Load CSV file."""
    return pd.read_csv(csv_path)


def load_multiple_csvs(input_dir: Path) -> Dict[str, pd.DataFrame]:
    """Load all CSV files from directory."""
    csvs = {}
    for csv_file in input_dir.glob("*.csv"):
        name = csv_file.stem
        csvs[name] = load_csv(csv_file)
    return csvs


def detect_missing_cells(df: pd.DataFrame, years: List[int]) -> List[Tuple[int, str, int]]:
    """
    Detect missing cells in dataframe.
    Returns list of (row_idx, indicator, year).
    """
    missing = []
    indicator_col = df.columns[0]
    
    for idx, row in df.iterrows():
        indicator = row[indicator_col]
        
        for year in years:
            year_col = str(year)
            if year_col in df.columns:
                value = row[year_col]
                if pd.isna(value) or value == '' or value == 'NOT_FOUND':
                    missing.append((idx, indicator, year))
    
    return missing


def save_csv(df: pd.DataFrame, output_path: Path):
    """Save DataFrame to CSV."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(output_path, index=False)


def save_filled_csv(df: pd.DataFrame, output_path: Path):
    """Save filled CSV with suffix."""
    stem = output_path.stem
    if not stem.endswith('_filled'):
        stem += '_filled'
    output_path = output_path.parent / f"{stem}.csv"
    save_csv(df, output_path)


def create_sources_csv(sources: List[Dict], output_path: Path):
    """Create sources_long.csv with extraction metadata."""
    df = pd.DataFrame(sources)
    
    # Expected columns: indicator, year, value, url, filename, page_no, snippet, confidence, method, doc_id
    expected_cols = ['indicator', 'year', 'value', 'url', 'filename', 'page_no', 
                     'snippet', 'confidence', 'method', 'doc_id']
    for col in expected_cols:
        if col not in df.columns:
            df[col] = ''
    
    df = df[expected_cols]
    save_csv(df, output_path)


def create_queries_csv(queries: List[Dict], output_path: Path):
    """Create queries_generated.csv with audit trail."""
    df = pd.DataFrame(queries)
    
    # Expected columns: indicator, category, year, query_1, query_2
    expected_cols = ['indicator', 'category', 'year', 'query_1', 'query_2']
    for col in expected_cols:
        if col not in df.columns:
            df[col] = ''
    
    df = df[expected_cols]
    save_csv(df, output_path)


def update_dataframe_cell(df: pd.DataFrame, row_idx: int, year: int, value: any) -> pd.DataFrame:
    """Update a cell in the dataframe."""
    year_col = str(year)
    
    # Ensure column exists
    if year_col not in df.columns:
        df[year_col] = ''
    
    df.at[row_idx, year_col] = value
    return df
