"""Query retrieval on BM25 index."""

from typing import List, Dict, Optional
from .indexer import BM25Index


class Retriever:
    """Retrieve relevant documents from BM25 index."""
    
    def __init__(self, index: BM25Index):
        self.index = index
    
    def retrieve(self, query: str, top_k: int = 10, year: Optional[int] = None,
                 min_score: float = 0.0) -> List[Dict]:
        """
        Retrieve top_k documents for query.
        Optionally filter by year and minimum score.
        """
        results = self.index.search(query, top_k=top_k, year_filter=year)
        
        # Filter by minimum score
        if min_score > 0:
            results = [r for r in results if r['score'] >= min_score]
        
        return results
    
    def retrieve_multi_query(self, queries: List[str], top_k: int = 10,
                            year: Optional[int] = None, min_score: float = 0.0) -> List[Dict]:
        """
        Retrieve documents for multiple queries and merge results.
        Deduplicates by sha1 and keeps highest score.
        """
        all_results = {}
        
        for query in queries:
            results = self.retrieve(query, top_k=top_k, year=year, min_score=min_score)
            
            for result in results:
                sha1 = result['sha1']
                if sha1 not in all_results or result['score'] > all_results[sha1]['score']:
                    all_results[sha1] = result
        
        # Sort by score
        merged = list(all_results.values())
        merged.sort(key=lambda x: x['score'], reverse=True)
        
        return merged[:top_k]
