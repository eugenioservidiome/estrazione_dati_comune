"""BM25 indexing with incremental updates and disk persistence.
Now supports page-level chunking instead of document-level indexing.
"""

import pickle
from pathlib import Path
from typing import List, Dict, Optional, Any
from rank_bm25 import BM25Okapi
from tqdm import tqdm


def simple_tokenize(text: str) -> List[str]:
    """
    Simple tokenization for Italian text.
    Converts to lowercase and splits on non-word characters.
    Suitable for BM25 indexing with minimal preprocessing.
    """
    import re
    text = text.lower()
    tokens = re.findall(r'\w+', text)
    return tokens


class BM25Index:
    """BM25 index with disk persistence. Now supports page-level chunks."""
    
    def __init__(self, index_dir: Path):
        self.index_dir = index_dir
        self.index_dir.mkdir(parents=True, exist_ok=True)
        
        self.bm25: Optional[BM25Okapi] = None
        self.chunks: List[Dict] = []  # metadata for each chunk (was documents)
        self.tokenized_corpus: List[List[str]] = []
    
    def build_index(self, chunks: List[Dict[str, Any]]):
        """
        Build BM25 index from page chunks.
        Each chunk should have: {sha1, text, year, url, filename, page_no, doc_kind(optional)}
        """
        self.chunks = chunks
        self.tokenized_corpus = []
        
        print(f"Tokenizing {len(chunks)} chunks...")
        for chunk in tqdm(chunks, desc="Tokenizing"):
            tokens = simple_tokenize(chunk.get('text', ''))
            self.tokenized_corpus.append(tokens)
        
        print("Building BM25 index...")
        self.bm25 = BM25Okapi(self.tokenized_corpus)
        print(f"Index built with {len(self.chunks)} chunks")
    
    def add_chunks(self, new_chunks: List[Dict[str, Any]]):
        """Add new chunks to existing index (incremental)."""
        if not self.bm25:
            # No existing index, just build fresh
            self.build_index(new_chunks)
            return
        
        # Add to existing index
        for chunk in tqdm(new_chunks, desc="Adding chunks"):
            tokens = simple_tokenize(chunk.get('text', ''))
            self.chunks.append(chunk)
            self.tokenized_corpus.append(tokens)
        
        # Rebuild BM25 (there's no true incremental add in rank_bm25)
        print("Rebuilding BM25 index...")
        self.bm25 = BM25Okapi(self.tokenized_corpus)
    
    def search(self, query: str, top_k: int = 8, year_filter: Optional[int] = None) -> List[Dict]:
        """
        Search index and return top_k chunk results (default 8, not 5).
        Optionally filter by year.
        """
        if not self.bm25:
            return []
        
        query_tokens = simple_tokenize(query)
        scores = self.bm25.get_scores(query_tokens)
        
        # Create results with scores
        results = []
        for idx, score in enumerate(scores):
            chunk = self.chunks[idx]
            
            # Apply year filter if specified
            if year_filter is not None and chunk.get('year') != year_filter:
                continue
            
            results.append({
                **chunk,
                'score': float(score)
            })
        
        # Sort by score descending
        results.sort(key=lambda x: x['score'], reverse=True)
        
        return results[:top_k]
    
    def save(self):
        """Save index to disk."""
        index_file = self.index_dir / "bm25_index.pkl"
        chunks_file = self.index_dir / "chunks.pkl"  # was documents.pkl
        corpus_file = self.index_dir / "corpus.pkl"
        
        with open(index_file, 'wb') as f:
            pickle.dump(self.bm25, f)
        
        with open(chunks_file, 'wb') as f:
            pickle.dump(self.chunks, f)
        
        with open(corpus_file, 'wb') as f:
            pickle.dump(self.tokenized_corpus, f)
        
        print(f"Index saved to {self.index_dir}")
    
    def load(self) -> bool:
        """Load index from disk. Returns True if successful."""
        index_file = self.index_dir / "bm25_index.pkl"
        chunks_file = self.index_dir / "chunks.pkl"  # was documents.pkl
        corpus_file = self.index_dir / "corpus.pkl"
        
        # For backward compatibility, also check for old documents.pkl
        if not chunks_file.exists():
            old_docs_file = self.index_dir / "documents.pkl"
            if old_docs_file.exists():
                chunks_file = old_docs_file
        
        if not (index_file.exists() and chunks_file.exists() and corpus_file.exists()):
            return False
        
        try:
            with open(index_file, 'rb') as f:
                self.bm25 = pickle.load(f)
            
            with open(chunks_file, 'rb') as f:
                loaded = pickle.load(f)
                # Convert old documents to chunks format if needed
                if loaded and isinstance(loaded[0], dict):
                    # If old format doesn't have page_no, add it
                    for item in loaded:
                        if 'page_no' not in item:
                            item['page_no'] = 0  # Mark as whole-document chunk
                self.chunks = loaded
            
            with open(corpus_file, 'rb') as f:
                self.tokenized_corpus = pickle.load(f)
            
            print(f"Index loaded from {self.index_dir} ({len(self.chunks)} chunks)")
            return True
        except Exception as e:
            print(f"Failed to load index: {e}")
            return False
    
    def get_stats(self) -> Dict:
        """Get index statistics."""
        return {
            'total_chunks': len(self.chunks),
            'indexed': self.bm25 is not None,
        }
    
    # Backward compatibility
    @property
    def documents(self):
        """Backward compatibility: documents -> chunks"""
        return self.chunks
