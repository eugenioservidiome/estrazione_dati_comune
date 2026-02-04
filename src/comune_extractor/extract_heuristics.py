"""Heuristic extraction with regex and Italian number normalization."""

import re
from typing import Optional, Tuple, List, Dict


def normalize_italian_number(text: str) -> Optional[float]:
    """
    Normalize Italian number format to float.
    Handles: 1.234,56 -> 1234.56, 1234,56 -> 1234.56
    """
    # Remove whitespace
    text = text.strip()
    
    # Pattern: optional digits with dots/spaces as thousands separator, comma as decimal
    # Examples: 1.234,56 or 1 234,56 or 1234,56
    
    # Remove thousands separators (dots and spaces between digits)
    text = re.sub(r'(?<=\d)[.\s](?=\d)', '', text)
    
    # Replace comma with dot for decimal
    text = text.replace(',', '.')
    
    try:
        return float(text)
    except ValueError:
        return None


def extract_number_with_context(text: str, keywords: List[str], 
                                context_window: int = 200) -> List[Tuple[float, str, int]]:
    """
    Extract numbers near keywords with context.
    Returns list of (value, snippet, position).
    """
    results = []
    text_lower = text.lower()
    
    # Find keyword positions
    keyword_positions = []
    for keyword in keywords:
        keyword_lower = keyword.lower()
        pos = 0
        while True:
            pos = text_lower.find(keyword_lower, pos)
            if pos == -1:
                break
            keyword_positions.append(pos)
            pos += len(keyword_lower)
    
    # For each keyword position, look for numbers nearby
    for kw_pos in keyword_positions:
        start = max(0, kw_pos - context_window)
        end = min(len(text), kw_pos + context_window)
        context = text[start:end]
        
        # Find numbers in context
        # Pattern: optional sign, digits with possible Italian separators
        number_pattern = r'[-+]?\d[\d\.\s,]*\d|\d'
        
        for match in re.finditer(number_pattern, context):
            number_text = match.group()
            value = normalize_italian_number(number_text)
            
            if value is not None:
                # Get snippet around the number
                match_start = start + match.start()
                snippet_start = max(0, match_start - 50)
                snippet_end = min(len(text), match_start + 50)
                snippet = text[snippet_start:snippet_end]
                
                results.append((value, snippet, match_start))
    
    return results


def score_extraction(value: float, snippet: str, keywords: List[str],
                    expected_range: Optional[Tuple[float, float]] = None) -> float:
    """
    Score an extraction result.
    Higher score = more confident.
    """
    score = 0.0
    snippet_lower = snippet.lower()
    
    # Keyword proximity bonus
    for keyword in keywords:
        if keyword.lower() in snippet_lower:
            score += 1.0
    
    # Range check
    if expected_range:
        min_val, max_val = expected_range
        if min_val <= value <= max_val:
            score += 2.0
        else:
            score -= 1.0
    
    # Penalize very small or very large numbers (likely noise)
    if value < 0.01 or value > 1e12:
        score -= 1.0
    
    return score


def extract_value_heuristic(text: str, keywords: List[str],
                           expected_range: Optional[Tuple[float, float]] = None,
                           top_k: int = 3) -> List[Dict]:
    """
    Extract value using heuristics.
    Returns list of candidates with scores.
    """
    extractions = extract_number_with_context(text, keywords)
    
    # Score each extraction
    scored = []
    for value, snippet, pos in extractions:
        score = score_extraction(value, snippet, keywords, expected_range)
        scored.append({
            'value': value,
            'snippet': snippet,
            'position': pos,
            'score': score
        })
    
    # Sort by score
    scored.sort(key=lambda x: x['score'], reverse=True)
    
    return scored[:top_k]

