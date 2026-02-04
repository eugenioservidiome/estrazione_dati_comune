"""Heuristic extraction with regex and Italian number normalization.
Updated to find keywords first, then numbers nearby (not just year proximity).
"""

import re
from typing import Optional, Tuple, List, Dict


def normalize_italian_number(text: str) -> Optional[float]:
    """
    Normalize Italian number format to float.
    Handles: 
    - 1.234,56 -> 1234.56
    - 1234,56 -> 1234.56
    - (1.234,56) -> -1234.56 (negatives in parentheses)
    - € 1.234,56 or 1.234,56 € -> 1234.56
    - 12,5% -> 0.125
    """
    # Remove whitespace and currency symbols
    text = text.strip()
    text = re.sub(r'[€\s]', '', text)
    
    # Handle percentage
    is_percentage = text.endswith('%')
    if is_percentage:
        text = text[:-1].strip()
    
    # Handle negatives in parentheses
    is_negative = False
    if text.startswith('(') and text.endswith(')'):
        is_negative = True
        text = text[1:-1].strip()
    
    # Check for explicit negative sign
    if text.startswith('-') or text.startswith('+'):
        if text.startswith('-'):
            is_negative = True
        text = text[1:].strip()
    
    # Pattern: optional digits with dots/spaces as thousands separator, comma as decimal
    # Examples: 1.234,56 or 1 234,56 or 1234,56
    
    # Remove thousands separators (dots and spaces between digits)
    text = re.sub(r'(?<=\d)[.\s](?=\d)', '', text)
    
    # Replace comma with dot for decimal
    text = text.replace(',', '.')
    
    try:
        value = float(text)
        if is_negative:
            value = -value
        if is_percentage:
            value = value / 100.0
        return value
    except ValueError:
        return None


def extract_number_with_context(text: str, keywords: List[str], 
                                context_window: int = 300) -> List[Tuple[float, str, int]]:
    """
    Extract numbers near keywords with context.
    Updated: Find keyword positions first, then look for numbers nearby.
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
            keyword_positions.append((pos, keyword))
            pos += len(keyword_lower)
    
    # For each keyword position, look for numbers nearby
    for kw_pos, kw in keyword_positions:
        start = max(0, kw_pos - context_window)
        end = min(len(text), kw_pos + context_window)
        context = text[start:end]
        
        # Find numbers in context
        # Pattern: optional sign, digits with possible Italian separators, optional € or %
        number_pattern = r'[€]?\s*[-+]?\(?\d[\d\.\s,]*\d?\)?\s*[€%]?|\(?\d\)?\s*[€%]?'
        
        for match in re.finditer(number_pattern, context):
            number_text = match.group()
            value = normalize_italian_number(number_text)
            
            if value is not None:
                # Get snippet around the number (max 240 chars centered on match)
                match_start = start + match.start()
                snippet_start = max(0, match_start - 120)
                snippet_end = min(len(text), match_start + 120)
                snippet = text[snippet_start:snippet_end].strip()
                
                # Truncate snippet if too long
                if len(snippet) > 240:
                    snippet = snippet[:240] + "..."
                
                results.append((value, snippet, match_start))
    
    return results


def score_extraction(value: float, snippet: str, keywords: List[str],
                    expected_range: Optional[Tuple[float, float]] = None,
                    year: Optional[int] = None) -> float:
    """
    Score an extraction result.
    Higher score = more confident.
    Updated: Don't rely only on year proximity. Score based on keyword density.
    """
    score = 0.0
    snippet_lower = snippet.lower()
    
    # Keyword proximity bonus (main signal)
    keyword_count = 0
    for keyword in keywords:
        if keyword.lower() in snippet_lower:
            keyword_count += 1
            score += 1.5  # Increased weight for keyword matches
    
    # Bonus for multiple keywords
    if keyword_count > 1:
        score += 1.0
    
    # Year proximity bonus (optional, not mandatory)
    if year:
        year_str = str(year)
        if year_str in snippet:
            score += 0.5
    
    # Range check
    if expected_range:
        min_val, max_val = expected_range
        if min_val <= value <= max_val:
            score += 2.0
        else:
            score -= 1.0
    
    # Penalize very small or very large numbers (likely noise)
    if value < 0.01 or value > 1e12:
        score -= 1.5
    
    return score


def extract_value_heuristic(text: str, keywords: List[str],
                           expected_range: Optional[Tuple[float, float]] = None,
                           year: Optional[int] = None,
                           top_k: int = 3) -> List[Dict]:
    """
    Extract value using heuristics from a single chunk.
    Returns list of candidates with scores.
    Updated: Pass year for optional scoring bonus.
    """
    extractions = extract_number_with_context(text, keywords)
    
    # Score each extraction
    scored = []
    for value, snippet, pos in extractions:
        score = score_extraction(value, snippet, keywords, expected_range, year)
        scored.append({
            'value': value,
            'snippet': snippet,
            'position': pos,
            'score': score
        })
    
    # Sort by score
    scored.sort(key=lambda x: x['score'], reverse=True)
    
    return scored[:top_k]

