"""Value extraction with confidence scoring."""

import logging
import re
from typing import Dict, List, Optional, Tuple

from .utils import parse_italian_number, extract_year_from_text

logger = logging.getLogger(__name__)


def extract_value_from_text(
    text: str,
    keywords: List[str],
    year: Optional[int] = None,
    context_window: int = 500,
    min_keywords: int = 1
) -> Dict:
    """Extract numeric value from text with confidence scoring.
    
    Searches for numeric values near keywords and year mentions.
    Returns the best match with confidence score based on:
    - Keyword presence and proximity
    - Year presence in context
    - Value format validity
    
    Args:
        text: Text to search for values
        keywords: List of keywords to search for
        year: Expected year (optional, increases confidence if found)
        context_window: Character window around value to extract
        min_keywords: Minimum keyword matches required
        
    Returns:
        Dict with keys:
            - value: Extracted numeric value (float or None)
            - confidence: Confidence score 0-1 (0 if no value found)
            - snippet: Context text around value
            - keywords_found: List of keywords found in snippet
            - year_found: Whether year was found in snippet (bool)
    """
    if not text or not keywords:
        return {
            'value': None,
            'confidence': 0.0,
            'snippet': '',
            'keywords_found': [],
            'year_found': False
        }
    
    text_lower = text.lower()
    
    # Find all numeric values in text
    candidates = _find_numeric_candidates(text)
    
    if not candidates:
        return {
            'value': None,
            'confidence': 0.0,
            'snippet': '',
            'keywords_found': [],
            'year_found': False
        }
    
    # Score each candidate
    best_candidate = None
    best_score = 0.0
    
    for value, position in candidates:
        # Extract context window around value
        start = max(0, position - context_window // 2)
        end = min(len(text), position + context_window // 2)
        snippet = text[start:end]
        snippet_lower = snippet.lower()
        
        # Count keyword matches
        keywords_found = [kw for kw in keywords if kw.lower() in snippet_lower]
        
        # Check for year
        year_found = False
        if year:
            year_found = extract_year_from_text(snippet, [year]) is not None
        
        # Calculate confidence score
        score = _calculate_confidence(
            keywords_found=keywords_found,
            total_keywords=len(keywords),
            year_found=year_found,
            year_expected=year is not None,
            value=value,
            snippet=snippet
        )
        
        if score > best_score:
            best_score = score
            best_candidate = {
                'value': value,
                'confidence': score,
                'snippet': snippet.strip(),
                'keywords_found': keywords_found,
                'year_found': year_found
            }
    
    # Check minimum requirements
    if best_candidate:
        kw_count = len(best_candidate['keywords_found'])
        year_ok = not year or best_candidate['year_found']
        
        # Require minimum conditions
        if kw_count < min_keywords:
            logger.debug(f"Candidate rejected: only {kw_count} keywords (need {min_keywords})")
            return {
                'value': None,
                'confidence': 0.0,
                'snippet': '',
                'keywords_found': [],
                'year_found': False
            }
        
        if year and not year_ok:
            logger.debug(f"Candidate rejected: year {year} not found in context")
            return {
                'value': None,
                'confidence': 0.0,
                'snippet': '',
                'keywords_found': [],
                'year_found': False
            }
        
        return best_candidate
    
    return {
        'value': None,
        'confidence': 0.0,
        'snippet': '',
        'keywords_found': [],
        'year_found': False
    }


def _find_numeric_candidates(text: str) -> List[Tuple[float, int]]:
    """Find all numeric value candidates in text.
    
    Args:
        text: Text to search
        
    Returns:
        List of (value, position) tuples
    """
    candidates = []
    
    # Pattern for Italian numbers: optional sign, digits with . as thousands separator,
    # optional , as decimal separator, optional currency/percentage
    # Examples: 1.234,56 €  -123,45  12,5%  1234
    # Use word boundaries to avoid partial matches
    pattern = r'\b[€$£]?\s*[+-]?\s*\d{1,3}(?:\.\d{3})*(?:,\d+)?(?:\s*[€$£%])?\b'
    
    for match in re.finditer(pattern, text):
        value_str = match.group(0)
        position = match.start()
        
        # Try to parse
        value = parse_italian_number(value_str)
        
        if value is not None:
            # Filter out unrealistic values (like years)
            if 1900 <= value <= 2100:
                # Likely a year, skip
                continue
            
            # Filter out very small values that are likely noise
            if abs(value) < 0.01:
                continue
            
            candidates.append((value, position))
    
    logger.debug(f"Found {len(candidates)} numeric candidates")
    return candidates


def _calculate_confidence(
    keywords_found: List[str],
    total_keywords: int,
    year_found: bool,
    year_expected: bool,
    value: float,
    snippet: str
) -> float:
    """Calculate confidence score for extracted value.
    
    Score is based on:
    - Keyword match rate (0-0.4 points)
    - Year presence (0-0.3 points)
    - Value validity (0-0.2 points)
    - Context quality (0-0.1 points)
    
    Args:
        keywords_found: List of keywords found
        total_keywords: Total keywords searched for
        year_found: Whether year was found
        year_expected: Whether year was expected
        value: Extracted value
        snippet: Context snippet
        
    Returns:
        Confidence score 0-1
    """
    score = 0.0
    
    # Component 1: Keyword matches (up to 0.4)
    if total_keywords > 0:
        keyword_ratio = len(keywords_found) / total_keywords
        score += keyword_ratio * 0.4
    
    # Component 2: Year presence (up to 0.3)
    if year_expected:
        if year_found:
            score += 0.3
    else:
        # No year expected, give partial credit
        score += 0.15
    
    # Component 3: Value validity (up to 0.2)
    # Prefer reasonable values
    if value is not None:
        if 0 <= abs(value) <= 1_000_000_000:  # Up to 1 billion
            score += 0.2
        else:
            score += 0.1  # Suspicious value
    
    # Component 4: Context quality (up to 0.1)
    # Prefer longer, more detailed snippets
    if len(snippet) > 200:
        score += 0.1
    elif len(snippet) > 100:
        score += 0.05
    
    return min(score, 1.0)  # Cap at 1.0


def extract_multiple_values(
    text: str,
    keyword_groups: Dict[str, List[str]],
    year: Optional[int] = None,
    context_window: int = 500
) -> Dict[str, Dict]:
    """Extract multiple values from text using different keyword groups.
    
    Useful for extracting multiple related values from the same document.
    
    Args:
        text: Text to search
        keyword_groups: Dict mapping names to keyword lists
        year: Expected year (optional)
        context_window: Context window size
        
    Returns:
        Dict mapping names to extraction results
    """
    results = {}
    
    for name, keywords in keyword_groups.items():
        result = extract_value_from_text(
            text=text,
            keywords=keywords,
            year=year,
            context_window=context_window
        )
        results[name] = result
    
    return results
