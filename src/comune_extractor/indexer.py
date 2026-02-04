"""BM25 indexing with incremental updates and disk persistence."""

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
    """BM25 index with disk persistence."""
    
    def __init__(self, index_dir: Path):
        self.index_dir = index_dir
        self.index_dir.mkdir(parents=True, exist_ok=True)
        
        self.bm25: Optional[BM25Okapi] = None
        self.documents: List[Dict] = []  # metadata for each doc
        self.tokenized_corpus: List[List[str]] = []
    
    def build_index(self, documents: List[Dict[str, Any]]):
        """
        Build BM25 index from documents.
        Each document should have: {sha1, text, year, url, ...}
        """
        self.documents = documents
        self.tokenized_corpus = []
        
        print(f"Tokenizing {len(documents)} documents...")
        for doc in tqdm(documents, desc="Tokenizing"):
            tokens = simple_tokenize(doc.get('text', ''))
            self.tokenized_corpus.append(tokens)
        
        print("Building BM25 index...")
        self.bm25 = BM25Okapi(self.tokenized_corpus)
        print(f"Index built with {len(self.documents)} documents")
    
    def add_documents(self, new_documents: List[Dict[str, Any]]):
        """Add new documents to existing index (incremental)."""
        if not self.bm25:
            # No existing index, just build fresh
            self.build_index(new_documents)
            return
        
        # Add to existing index
        for doc in tqdm(new_documents, desc="Adding documents"):
            tokens = simple_tokenize(doc.get('text', ''))
            self.documents.append(doc)
            self.tokenized_corpus.append(tokens)
        
        # Rebuild BM25 (there's no true incremental add in rank_bm25)
        print("Rebuilding BM25 index...")
        self.bm25 = BM25Okapi(self.tokenized_corpus)
    
    def search(self, query: str, top_k: int = 10, year_filter: Optional[int] = None) -> List[Dict]:
        """
        Search index and return top_k results.
        Optionally filter by year.
        """
        if not self.bm25:
            return []
        
        query_tokens = simple_tokenize(query)
        scores = self.bm25.get_scores(query_tokens)
        
        # Create results with scores
        results = []
        for idx, score in enumerate(scores):
            doc = self.documents[idx]
            
            # Apply year filter if specified
            if year_filter is not None and doc.get('year') != year_filter:
                continue
            
            results.append({
                **doc,
                'score': float(score)
            })
        
        # Sort by score descending
        results.sort(key=lambda x: x['score'], reverse=True)
        
        return results[:top_k]
    
    def save(self):
        """Save index to disk."""
        index_file = self.index_dir / "bm25_index.pkl"
        docs_file = self.index_dir / "documents.pkl"
        corpus_file = self.index_dir / "corpus.pkl"
        
        with open(index_file, 'wb') as f:
            pickle.dump(self.bm25, f)
        
        with open(docs_file, 'wb') as f:
            pickle.dump(self.documents, f)
        
        with open(corpus_file, 'wb') as f:
            pickle.dump(self.tokenized_corpus, f)
        
        print(f"Index saved to {self.index_dir}")
    
    def load(self) -> bool:
        """Load index from disk. Returns True if successful."""
        index_file = self.index_dir / "bm25_index.pkl"
        docs_file = self.index_dir / "documents.pkl"
        corpus_file = self.index_dir / "corpus.pkl"
        
        if not (index_file.exists() and docs_file.exists() and corpus_file.exists()):
            return False
        
        try:
            with open(index_file, 'rb') as f:
                self.bm25 = pickle.load(f)
            
            with open(docs_file, 'rb') as f:
                self.documents = pickle.load(f)
            
            with open(corpus_file, 'rb') as f:
                self.tokenized_corpus = pickle.load(f)
            
            print(f"Index loaded from {self.index_dir} ({len(self.documents)} documents)")
            return True
        except Exception as e:
            print(f"Failed to load index: {e}")
            return False
    
    def get_stats(self) -> Dict:
        """Get index statistics."""
        return {
            'total_documents': len(self.documents),
            'indexed': self.bm25 is not None,
        }
