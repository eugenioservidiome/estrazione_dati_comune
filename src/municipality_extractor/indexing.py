"""TF-IDF indexing and document retrieval."""

import logging
from typing import Dict, List, Optional, Tuple

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

logger = logging.getLogger(__name__)

# Minimal Italian stopwords list
ITALIAN_STOPWORDS = {
    'il', 'lo', 'la', 'i', 'gli', 'le',  # Articles
    'un', 'uno', 'una',  # Indefinite articles
    'di', 'a', 'da', 'in', 'con', 'su', 'per', 'tra', 'fra',  # Prepositions
    'e', 'o', 'ma', 'se', 'che',  # Conjunctions
    'questo', 'quello', 'questi', 'quelli', 'questa', 'quella',  # Demonstratives
    'del', 'dello', 'della', 'dei', 'degli', 'delle',  # Contracted prepositions
    'al', 'allo', 'alla', 'ai', 'agli', 'alle',
    'dal', 'dallo', 'dalla', 'dai', 'dagli', 'dalle',
    'nel', 'nello', 'nella', 'nei', 'negli', 'nelle',
    'sul', 'sullo', 'sulla', 'sui', 'sugli', 'sulle',
    'è', 'sono', 'ha', 'hanno', 'sia', 'essere',  # Common verbs
}


class DocumentIndex:
    """TF-IDF based document index for retrieval."""
    
    def __init__(
        self,
        max_features: int = 5000,
        ngram_range: Tuple[int, int] = (1, 3),
        use_stopwords: bool = True
    ):
        """Initialize document index.
        
        Args:
            max_features: Maximum number of TF-IDF features
            ngram_range: N-gram range for TF-IDF (min, max)
            use_stopwords: Whether to use Italian stopwords
        """
        self.max_features = max_features
        self.ngram_range = ngram_range
        
        self.vectorizer: Optional[TfidfVectorizer] = None
        self.doc_vectors: Optional[np.ndarray] = None
        self.documents: List[Dict] = []  # List of {doc_id, text, metadata}
        self.doc_id_to_idx: Dict[str, int] = {}  # Map doc_id to index
        
        # Stopwords
        self.stopwords = ITALIAN_STOPWORDS if use_stopwords else None
    
    def build_index(self, documents: List[Dict]) -> None:
        """Build TF-IDF index from documents.
        
        Args:
            documents: List of document dicts with keys:
                - doc_id: Unique document identifier (required)
                - text: Document text content (required)
                - Any other metadata fields (optional)
                
        Raises:
            ValueError: If documents is empty or missing required fields
        """
        if not documents:
            raise ValueError("Cannot build index from empty document list")
        
        # Validate documents
        for i, doc in enumerate(documents):
            if 'doc_id' not in doc:
                raise ValueError(f"Document {i} missing 'doc_id' field")
            if 'text' not in doc:
                raise ValueError(f"Document {i} missing 'text' field")
        
        # Store documents and build mapping
        self.documents = documents
        self.doc_id_to_idx = {doc['doc_id']: i for i, doc in enumerate(documents)}
        
        # Extract texts
        texts = [doc['text'] for doc in documents]
        
        # Handle small corpus by adjusting max_df
        # max_df should be at least 2 documents, but as a fraction should be < 1.0
        corpus_size = len(texts)
        if corpus_size < 2:
            max_df = 1.0
        elif corpus_size < 10:
            # For small corpus, be more lenient
            max_df = 0.95
        else:
            max_df = 0.85
        
        logger.info(f"Building TF-IDF index for {corpus_size} documents")
        logger.info(f"Parameters: max_features={self.max_features}, ngram_range={self.ngram_range}, max_df={max_df}")
        
        # Build TF-IDF vectorizer
        try:
            self.vectorizer = TfidfVectorizer(
                max_features=self.max_features,
                ngram_range=self.ngram_range,
                max_df=max_df,
                min_df=1,  # At least 1 document
                stop_words=list(self.stopwords) if self.stopwords else None,
                lowercase=True,
                token_pattern=r'\b\w+\b'
            )
            
            self.doc_vectors = self.vectorizer.fit_transform(texts)
            
            logger.info(f"Index built successfully: {self.doc_vectors.shape[0]} documents, "
                       f"{self.doc_vectors.shape[1]} features")
            
        except ValueError as e:
            # Handle edge cases like all documents identical
            logger.warning(f"TF-IDF failed with error: {e}. Using simpler vectorizer.")
            
            # Fallback: simpler vectorizer
            self.vectorizer = TfidfVectorizer(
                max_features=min(1000, self.max_features),
                ngram_range=(1, 1),  # Only unigrams
                max_df=1.0,
                min_df=1,
                lowercase=True,
                token_pattern=r'\b\w+\b'
            )
            
            self.doc_vectors = self.vectorizer.fit_transform(texts)
            logger.info(f"Fallback index built: {self.doc_vectors.shape[0]} documents, "
                       f"{self.doc_vectors.shape[1]} features")
    
    def search(
        self,
        query: str,
        top_k: int = 10,
        min_score: float = 0.0
    ) -> List[Dict]:
        """Search for documents matching the query.
        
        Args:
            query: Search query string
            top_k: Number of top results to return
            min_score: Minimum cosine similarity score (0-1)
            
        Returns:
            List of result dicts with keys:
                - doc_id: Document identifier
                - score: Cosine similarity score (0-1)
                - text: Document text
                - All other metadata from original document
                
        Raises:
            ValueError: If index not built yet
        """
        if self.vectorizer is None or self.doc_vectors is None:
            raise ValueError("Index not built yet. Call build_index() first.")
        
        if not query.strip():
            logger.warning("Empty query provided")
            return []
        
        # Vectorize query
        try:
            query_vector = self.vectorizer.transform([query])
        except Exception as e:
            logger.error(f"Failed to vectorize query: {e}")
            return []
        
        # Compute cosine similarities
        similarities = cosine_similarity(query_vector, self.doc_vectors)[0]
        
        # Get top-k indices
        top_indices = np.argsort(similarities)[::-1][:top_k]
        
        # Build results
        results = []
        for idx in top_indices:
            score = float(similarities[idx])
            
            # Filter by minimum score
            if score < min_score:
                continue
            
            # Get document
            doc = self.documents[idx].copy()
            doc['score'] = score
            results.append(doc)
        
        logger.debug(f"Query '{query[:50]}...' returned {len(results)} results")
        return results
    
    def get_document(self, doc_id: str) -> Optional[Dict]:
        """Get a document by its ID.
        
        Args:
            doc_id: Document identifier
            
        Returns:
            Document dict or None if not found
        """
        idx = self.doc_id_to_idx.get(doc_id)
        if idx is None:
            return None
        return self.documents[idx].copy()


def build_tfidf_index(
    documents: List[Dict],
    max_features: int = 5000,
    ngram_range: Tuple[int, int] = (1, 3)
) -> DocumentIndex:
    """Build a TF-IDF index from documents.
    
    Convenience function that creates and builds an index in one call.
    
    Args:
        documents: List of document dicts (must have 'doc_id' and 'text' keys)
        max_features: Maximum TF-IDF features
        ngram_range: N-gram range
        
    Returns:
        Built DocumentIndex
    """
    index = DocumentIndex(max_features=max_features, ngram_range=ngram_range)
    index.build_index(documents)
    return index


def search_documents(
    index: DocumentIndex,
    query: str,
    top_k: int = 10
) -> List[Dict]:
    """Search documents using TF-IDF index.
    
    Convenience function for searching.
    
    Args:
        index: Built DocumentIndex
        query: Search query
        top_k: Number of results to return
        
    Returns:
        List of results with scores and metadata
    """
    return index.search(query, top_k=top_k)
