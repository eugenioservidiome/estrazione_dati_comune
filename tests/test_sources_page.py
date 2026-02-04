"""Tests for sources CSV including page numbers."""

import pytest
import pandas as pd
from pathlib import Path
from comune_extractor.csv_io import create_sources_csv


class TestSourcesIncludePage:
    """Test that sources_long.csv includes page numbers."""
    
    def test_sources_csv_has_page_no_column(self, tmp_path):
        """CRITICAL: sources_long.csv must include page_no column."""
        sources = [
            {
                'indicator': 'Delibere CC',
                'year': 2023,
                'value': 150,
                'url': 'http://example.com/doc.pdf',
                'filename': 'delibere_2023.pdf',
                'page_no': 5,
                'snippet': 'Il numero totale di delibere è 150',
                'confidence': 0.85,
                'method': 'heuristic',
                'doc_id': 'abc123'
            }
        ]
        
        output_path = tmp_path / "sources_long.csv"
        create_sources_csv(sources, output_path)
        
        # Load and verify
        df = pd.read_csv(output_path)
        
        assert 'page_no' in df.columns
        assert df.iloc[0]['page_no'] == 5
    
    def test_sources_csv_has_all_required_columns(self, tmp_path):
        """Sources CSV must have all required columns."""
        sources = [
            {
                'indicator': 'Spesa corrente',
                'year': 2023,
                'value': 1000000,
                'url': 'http://example.com/bilancio.pdf',
                'filename': 'bilancio_2023.pdf',
                'page_no': 12,
                'snippet': 'La spesa corrente ammonta a € 1.000.000',
                'confidence': 0.92,
                'method': 'heuristic',
                'doc_id': 'sha1_abc123'
            }
        ]
        
        output_path = tmp_path / "sources_long.csv"
        create_sources_csv(sources, output_path)
        
        df = pd.read_csv(output_path)
        
        # Check all required columns exist
        required = ['indicator', 'year', 'value', 'url', 'filename', 'page_no', 
                   'snippet', 'confidence', 'method', 'doc_id']
        for col in required:
            assert col in df.columns, f"Missing required column: {col}"
    
    def test_sources_csv_preserves_snippet(self, tmp_path):
        """Snippet should be preserved in sources CSV."""
        snippet = 'Raccolta differenziata: 65,5% sul totale dei rifiuti'
        
        sources = [
            {
                'indicator': 'Raccolta differenziata %',
                'year': 2023,
                'value': 65.5,
                'url': 'http://example.com/ambiente.pdf',
                'filename': 'rapporto_ambiente.pdf',
                'page_no': 8,
                'snippet': snippet,
                'confidence': 0.78,
                'method': 'heuristic',
                'doc_id': 'xyz789'
            }
        ]
        
        output_path = tmp_path / "sources_long.csv"
        create_sources_csv(sources, output_path)
        
        df = pd.read_csv(output_path)
        assert df.iloc[0]['snippet'] == snippet
    
    def test_sources_csv_includes_doc_id(self, tmp_path):
        """doc_id (SHA1) should be included for traceability."""
        doc_id = 'sha1_abcdef1234567890'
        
        sources = [
            {
                'indicator': 'Test',
                'year': 2023,
                'value': 100,
                'url': 'http://example.com/test.pdf',
                'filename': 'test.pdf',
                'page_no': 1,
                'snippet': 'test snippet',
                'confidence': 0.9,
                'method': 'heuristic',
                'doc_id': doc_id
            }
        ]
        
        output_path = tmp_path / "sources_long.csv"
        create_sources_csv(sources, output_path)
        
        df = pd.read_csv(output_path)
        assert df.iloc[0]['doc_id'] == doc_id
    
    def test_sources_csv_handles_missing_fields(self, tmp_path):
        """Should handle sources with missing optional fields."""
        sources = [
            {
                'indicator': 'Test',
                'year': 2023,
                'value': 100
                # Missing url, filename, page_no, snippet, etc.
            }
        ]
        
        output_path = tmp_path / "sources_long.csv"
        create_sources_csv(sources, output_path)
        
        df = pd.read_csv(output_path)
        
        # Should still have all columns (filled with empty strings)
        required = ['indicator', 'year', 'value', 'url', 'filename', 'page_no', 
                   'snippet', 'confidence', 'method', 'doc_id']
        for col in required:
            assert col in df.columns
    
    def test_sources_csv_multiple_entries(self, tmp_path):
        """Should handle multiple source entries."""
        sources = [
            {
                'indicator': 'Delibere CC',
                'year': 2023,
                'value': 150,
                'url': 'http://example.com/doc1.pdf',
                'filename': 'doc1.pdf',
                'page_no': 5,
                'snippet': 'snippet 1',
                'confidence': 0.85,
                'method': 'heuristic',
                'doc_id': 'abc123'
            },
            {
                'indicator': 'Spesa corrente',
                'year': 2023,
                'value': 500000,
                'url': 'http://example.com/doc2.pdf',
                'filename': 'doc2.pdf',
                'page_no': 12,
                'snippet': 'snippet 2',
                'confidence': 0.92,
                'method': 'llm',
                'doc_id': 'def456'
            }
        ]
        
        output_path = tmp_path / "sources_long.csv"
        create_sources_csv(sources, output_path)
        
        df = pd.read_csv(output_path)
        
        assert len(df) == 2
        assert df.iloc[0]['page_no'] == 5
        assert df.iloc[1]['page_no'] == 12
        assert df.iloc[0]['method'] == 'heuristic'
        assert df.iloc[1]['method'] == 'llm'
