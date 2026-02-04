"""Tests for page-level PDF chunking."""

import pytest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from comune_extractor.pdf_text import (
    extract_text_per_page,
    save_page_texts,
    load_page_texts
)
from comune_extractor.indexer import BM25Index


class TestPDFPageExtraction:
    """Test per-page PDF text extraction."""
    
    @patch('fitz.open')
    def test_extract_text_per_page_pymupdf(self, mock_fitz_open):
        """Test that extract_text_per_page returns list of page texts."""
        # Mock a 3-page PDF
        mock_doc = MagicMock()
        mock_doc.__len__.return_value = 3
        mock_doc.__enter__.return_value = mock_doc
        mock_doc.__exit__.return_value = None
        
        mock_page1 = Mock()
        mock_page1.get_text.return_value = "Page 1 text"
        mock_page2 = Mock()
        mock_page2.get_text.return_value = "Page 2 text"
        mock_page3 = Mock()
        mock_page3.get_text.return_value = "Page 3 text"
        
        mock_doc.__iter__.return_value = iter([mock_page1, mock_page2, mock_page3])
        mock_fitz_open.return_value = mock_doc
        
        from comune_extractor.pdf_text import extract_text_per_page_pymupdf
        page_texts, page_count = extract_text_per_page_pymupdf(Path('/fake/test.pdf'))
        
        assert page_count == 3
        assert len(page_texts) == 3
        assert page_texts[0] == "Page 1 text"
        assert page_texts[1] == "Page 2 text"
        assert page_texts[2] == "Page 3 text"
    
    def test_save_and_load_page_texts(self, tmp_path):
        """Test saving and loading page texts."""
        sha1 = "abc123"
        page_texts = ["Page 1 content", "Page 2 content", "Page 3 content"]
        
        # Save
        save_page_texts(page_texts, tmp_path, sha1)
        
        # Check files created
        assert (tmp_path / f"{sha1}_page_1.txt").exists()
        assert (tmp_path / f"{sha1}_page_2.txt").exists()
        assert (tmp_path / f"{sha1}_page_3.txt").exists()
        
        # Load
        loaded = load_page_texts(tmp_path, sha1, 3)
        assert loaded == page_texts
    
    def test_load_page_texts_missing_file(self, tmp_path):
        """Test that load_page_texts returns None if a page is missing."""
        sha1 = "abc123"
        
        # Create only 2 pages
        (tmp_path / f"{sha1}_page_1.txt").write_text("Page 1")
        (tmp_path / f"{sha1}_page_2.txt").write_text("Page 2")
        
        # Try to load 3 pages
        loaded = load_page_texts(tmp_path, sha1, 3)
        assert loaded is None


class TestBM25IndexChunks:
    """Test BM25 index with page chunks."""
    
    def test_build_index_with_chunks(self, tmp_path):
        """Test that index can be built from page chunks."""
        chunks = [
            {
                'sha1': 'doc1',
                'text': 'bilancio consuntivo 2023',
                'year': 2023,
                'url': 'http://example.com/doc1.pdf',
                'filename': 'doc1.pdf',
                'page_no': 1,
                'total_pages': 2
            },
            {
                'sha1': 'doc1',
                'text': 'deliberazioni giunta comunale',
                'year': 2023,
                'url': 'http://example.com/doc1.pdf',
                'filename': 'doc1.pdf',
                'page_no': 2,
                'total_pages': 2
            },
            {
                'sha1': 'doc2',
                'text': 'raccolta differenziata rifiuti',
                'year': 2023,
                'url': 'http://example.com/doc2.pdf',
                'filename': 'doc2.pdf',
                'page_no': 1,
                'total_pages': 1
            }
        ]
        
        index = BM25Index(tmp_path)
        index.build_index(chunks)
        
        # Check that all chunks are indexed
        assert len(index.chunks) == 3
        assert index.bm25 is not None
    
    def test_search_returns_chunks_with_page_no(self, tmp_path):
        """Test that search returns chunks with page_no."""
        chunks = [
            {
                'sha1': 'doc1',
                'text': 'bilancio consuntivo 2023',
                'year': 2023,
                'url': 'http://example.com/doc1.pdf',
                'filename': 'doc1.pdf',
                'page_no': 1,
                'total_pages': 1
            }
        ]
        
        index = BM25Index(tmp_path)
        index.build_index(chunks)
        
        results = index.search('bilancio', top_k=1)
        
        assert len(results) > 0
        assert 'page_no' in results[0]
        assert results[0]['page_no'] == 1
    
    def test_search_default_top_k_is_8(self, tmp_path):
        """Test that default top_k for search is 8 (not 10)."""
        chunks = [
            {
                'sha1': f'doc{i}',
                'text': f'document {i} content',
                'year': 2023,
                'url': f'http://example.com/doc{i}.pdf',
                'filename': f'doc{i}.pdf',
                'page_no': 1,
                'total_pages': 1
            }
            for i in range(20)
        ]
        
        index = BM25Index(tmp_path)
        index.build_index(chunks)
        
        # Search without specifying top_k
        from comune_extractor.retrieval import Retriever
        retriever = Retriever(index)
        results = retriever.retrieve('document')
        
        # Should return 8 by default
        assert len(results) == 8


class TestBackwardCompatibility:
    """Test backward compatibility with old document format."""
    
    def test_load_old_documents_pkl(self, tmp_path):
        """Test that old documents.pkl can be loaded and converted to chunks."""
        import pickle
        
        # Create old-style documents (without page_no)
        old_docs = [
            {
                'sha1': 'doc1',
                'text': 'old document text',
                'year': 2023,
                'url': 'http://example.com/doc1.pdf',
                'filename': 'doc1.pdf'
            }
        ]
        
        # Save as old documents.pkl
        docs_file = tmp_path / "documents.pkl"
        with open(docs_file, 'wb') as f:
            pickle.dump(old_docs, f)
        
        # Create dummy bm25 and corpus files
        index_file = tmp_path / "bm25_index.pkl"
        corpus_file = tmp_path / "corpus.pkl"
        
        from rank_bm25 import BM25Okapi
        dummy_bm25 = BM25Okapi([['old', 'document', 'text']])
        dummy_corpus = [['old', 'document', 'text']]
        
        with open(index_file, 'wb') as f:
            pickle.dump(dummy_bm25, f)
        with open(corpus_file, 'wb') as f:
            pickle.dump(dummy_corpus, f)
        
        # Load index
        index = BM25Index(tmp_path)
        loaded = index.load()
        
        assert loaded is True
        assert len(index.chunks) == 1
        # Check that page_no was added for backward compatibility
        assert 'page_no' in index.chunks[0]
        assert index.chunks[0]['page_no'] == 0
