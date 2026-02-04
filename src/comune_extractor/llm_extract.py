"""Optional LLM extraction with OpenAI Responses API and JSON cache."""

import json
import hashlib
from pathlib import Path
from typing import Optional, Dict, List, Any
import re


class LLMExtractor:
    """Extract values using OpenAI API with structured outputs."""
    
    def __init__(self, catalog, api_key: Optional[str], model: str = "gpt-4o-mini",
                 confidence_threshold: float = 0.7):
        self.catalog = catalog
        self.api_key = api_key
        self.model = model
        self.confidence_threshold = confidence_threshold
        self.enabled = api_key is not None
        
        if self.enabled:
            try:
                from openai import OpenAI
                self.client = OpenAI(api_key=api_key)
            except ImportError:
                self.enabled = False
                self.client = None
    
    def extract_value(self, text: str, indicator: str, year: int,
                     llm_dir: Path) -> Optional[Dict[str, Any]]:
        """
        Extract value using LLM with caching.
        Returns {value, unit, year, evidence, confidence} or None.
        """
        if not self.enabled:
            return None
        
        # Create cache key
        cache_key = self._make_cache_key(text, indicator, year, self.model)
        
        # Check cache
        cached = self.catalog.get_llm_cache(cache_key)
        if cached:
            json_path = Path(cached['json_path'])
            if json_path.exists():
                with open(json_path, 'r') as f:
                    return json.load(f)
        
        # Call LLM
        try:
            result = self._call_llm(text, indicator, year)
            
            if result and result.get('confidence', 0) >= self.confidence_threshold:
                # Validate year match
                if result.get('year') == year:
                    # Save to cache
                    json_path = llm_dir / f"{cache_key}.json"
                    json_path.parent.mkdir(parents=True, exist_ok=True)
                    
                    with open(json_path, 'w') as f:
                        json.dump(result, f, indent=2)
                    
                    self.catalog.add_llm_cache(cache_key, str(json_path), self.model)
                    
                    return result
        except Exception as e:
            pass
        
        return None
    
    def _make_cache_key(self, text: str, indicator: str, year: int, model: str) -> str:
        """Create cache key from inputs."""
        content = f"{text[:1000]}|{indicator}|{year}|{model}"
        return hashlib.sha256(content.encode()).hexdigest()
    
    def _call_llm(self, text: str, indicator: str, year: int) -> Optional[Dict]:
        """Call OpenAI API with structured output."""
        if not self.client:
            return None
        
        # Limit text length (10k chars ≈ 2.5k tokens, well under API limits)
        MAX_LLM_TEXT_LENGTH = 10000
        if len(text) > MAX_LLM_TEXT_LENGTH:
            text = text[:MAX_LLM_TEXT_LENGTH]
        
        prompt = f"""Extract the value for the following indicator from the text.

Indicator: {indicator}
Year: {year}

Text:
{text}

Extract:
- value (numeric)
- unit (e.g., "euro", "abitanti", "tonnellate")
- year (must match {year})
- evidence (short quote from text)
- confidence (0.0-1.0)

Return JSON with these exact fields. If not found, return null for value."""
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a data extraction assistant. Extract structured information from Italian municipal documents."},
                    {"role": "user", "content": prompt}
                ],
                response_format={"type": "json_object"},
                temperature=0.0
            )
            
            content = response.choices[0].message.content
            result = json.loads(content)
            
            # Validate and normalize
            if result.get('value') is not None:
                return {
                    'value': float(result['value']),
                    'unit': result.get('unit', ''),
                    'year': int(result.get('year', year)),
                    'evidence': result.get('evidence', '')[:200],
                    'confidence': float(result.get('confidence', 0.5))
                }
        except Exception as e:
            pass
        
        return None
    
    def select_chunks(self, text: str, keywords: List[str], year: int,
                     max_chunks: int = 3, chunk_size: int = 2000) -> List[str]:
        """
        Select relevant chunks from text for LLM processing.
        Find positions with year + keywords, extract surrounding context.
        """
        chunks = []
        text_lower = text.lower()
        year_str = str(year)
        
        # Find positions with year
        year_positions = []
        pos = 0
        while True:
            pos = text_lower.find(year_str, pos)
            if pos == -1:
                break
            year_positions.append(pos)
            pos += len(year_str)
        
        # For each year position, check if keywords nearby
        scored_positions = []
        for y_pos in year_positions:
            start = max(0, y_pos - 500)
            end = min(len(text), y_pos + 500)
            context = text_lower[start:end]
            
            # Count keyword matches
            score = sum(1 for kw in keywords if kw.lower() in context)
            if score > 0:
                scored_positions.append((y_pos, score))
        
        # Sort by score and take top positions
        scored_positions.sort(key=lambda x: x[1], reverse=True)
        
        for pos, score in scored_positions[:max_chunks]:
            start = max(0, pos - chunk_size // 2)
            end = min(len(text), pos + chunk_size // 2)
            chunk = text[start:end]
            chunks.append(chunk)
        
        return chunks
