"""Generate 1-2 queries per cell (not 8-20), preserve categorization."""

import pandas as pd
from typing import List, Dict, Tuple


def categorize_indicator(indicator: str, category: str = None) -> str:
    """Categorize indicator to determine query strategy."""
    indicator_lower = indicator.lower()
    
    # Financial indicators
    if any(word in indicator_lower for word in ['spesa', 'entrata', 'costo', 'budget', 'bilancio', 'debito']):
        return 'financial'
    
    # Population/demographic
    if any(word in indicator_lower for word in ['popolazione', 'abitanti', 'residenti', 'demografic']):
        return 'demographic'
    
    # Environmental
    if any(word in indicator_lower for word in ['rifiuti', 'raccolta', 'ambiente', 'emissioni', 'acqua']):
        return 'environmental'
    
    # Infrastructure
    if any(word in indicator_lower for word in ['strada', 'illuminazione', 'edifici', 'scuole']):
        return 'infrastructure'
    
    return category or 'general'


def build_query(indicator: str, category: str, year: int = None) -> str:
    """Build canonical query for an indicator."""
    parts = [indicator]
    
    if year:
        parts.append(str(year))
    
    # Add category context if relevant
    if category == 'financial':
        parts.append('bilancio')
    elif category == 'environmental':
        parts.append('ambiente')
    
    return ' '.join(parts)


def build_variant_query(indicator: str, category: str, year: int = None) -> str:
    """Build variant query with synonyms."""
    indicator_lower = indicator.lower()
    
    # Simple synonym expansion
    synonyms = {
        'spesa': 'costo',
        'abitanti': 'popolazione',
        'rifiuti': 'raccolta differenziata',
        'entrata': 'introito',
    }
    
    variant = indicator
    for key, value in synonyms.items():
        if key in indicator_lower and value not in indicator_lower:
            variant = variant + ' ' + value
            break
    
    parts = [variant]
    if year:
        parts.append(str(year))
    
    return ' '.join(parts)


def generate_queries(indicator: str, category: str = None, year: int = None,
                    max_queries: int = 2) -> List[str]:
    """
    Generate 1-2 queries per indicator (NOT 8-20).
    """
    cat = categorize_indicator(indicator, category)
    
    queries = []
    
    # 1. Canonical query
    queries.append(build_query(indicator, cat, year))
    
    # 2. Variant with synonyms (only if max_queries > 1)
    if max_queries > 1:
        variant = build_variant_query(indicator, cat, year)
        if variant != queries[0]:  # Only add if different
            queries.append(variant)
    
    return queries[:max_queries]


def generate_queries_for_dataframe(df: pd.DataFrame, years: List[int]) -> pd.DataFrame:
    """
    Generate queries for missing cells in dataframe.
    Returns DataFrame with columns: indicator, category, year, query_1, query_2
    """
    records = []
    
    # Assume first column is indicator/category
    indicator_col = df.columns[0]
    
    for idx, row in df.iterrows():
        indicator = row[indicator_col]
        
        # Try to extract category if it's a multi-level indicator
        if '|' in str(indicator):
            parts = str(indicator).split('|')
            category = parts[0].strip()
            indicator_name = parts[-1].strip()
        else:
            category = None
            indicator_name = str(indicator)
        
        for year in years:
            year_col = str(year)
            
            # Check if cell is missing
            if year_col not in df.columns or pd.isna(row[year_col]) or row[year_col] == '':
                queries = generate_queries(indicator_name, category, year, max_queries=2)
                
                record = {
                    'indicator': indicator_name,
                    'category': category or '',
                    'year': year,
                    'query_1': queries[0] if len(queries) > 0 else '',
                    'query_2': queries[1] if len(queries) > 1 else '',
                }
                records.append(record)
    
    return pd.DataFrame(records)
