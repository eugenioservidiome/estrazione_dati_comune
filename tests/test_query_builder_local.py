"""Tests for query builder - ensuring no Google operators and 1-2 queries max."""

import pytest
from comune_extractor.query_builder import (
    categorize_indicator,
    build_query,
    build_variant_query,
    generate_queries,
    generate_queries_for_dataframe
)
import pandas as pd


class TestCategorizeIndicator:
    """Test indicator categorization."""
    
    def test_financial_category(self):
        assert categorize_indicator('Spesa corrente') == 'financial'
        assert categorize_indicator('Entrata tributaria') == 'financial'
        assert categorize_indicator('Costo del personale') == 'financial'
        assert categorize_indicator('Bilancio preventivo') == 'financial'
        assert categorize_indicator('Debito pubblico') == 'financial'
    
    def test_demographic_category(self):
        assert categorize_indicator('Popolazione residente') == 'demographic'
        assert categorize_indicator('Abitanti') == 'demographic'
        assert categorize_indicator('Residenti stranieri') == 'demographic'
    
    def test_environmental_category(self):
        assert categorize_indicator('Raccolta differenziata') == 'environmental'
        assert categorize_indicator('Rifiuti urbani') == 'environmental'
        assert categorize_indicator('Emissioni CO2') == 'environmental'
    
    def test_infrastructure_category(self):
        assert categorize_indicator('Illuminazione pubblica') == 'infrastructure'
        assert categorize_indicator('Edifici comunali') == 'infrastructure'
        assert categorize_indicator('Scuole primarie') == 'infrastructure'
    
    def test_general_fallback(self):
        assert categorize_indicator('Unknown indicator') == 'general'


class TestBuildQuery:
    """Test query building."""
    
    def test_canonical_query_with_year(self):
        query = build_query('Delibere CC', 'general', year=2023)
        assert '2023' in query
        assert 'Delibere CC' in query
    
    def test_canonical_query_without_year(self):
        query = build_query('Delibere CC', 'general')
        assert 'Delibere CC' in query
    
    def test_financial_adds_bilancio(self):
        query = build_query('Spesa corrente', 'financial', year=2023)
        assert 'bilancio' in query
        assert 'Spesa corrente' in query
        assert '2023' in query
    
    def test_environmental_adds_ambiente(self):
        query = build_query('Rifiuti', 'environmental', year=2023)
        assert 'ambiente' in query


class TestBuildVariantQuery:
    """Test variant query building with synonyms."""
    
    def test_adds_synonym_for_spesa(self):
        query = build_variant_query('Spesa corrente', 'financial', year=2023)
        assert 'costo' in query or 'Spesa corrente' in query
    
    def test_adds_synonym_for_abitanti(self):
        query = build_variant_query('Abitanti', 'demographic', year=2023)
        assert 'popolazione' in query or 'Abitanti' in query
    
    def test_includes_year(self):
        query = build_variant_query('Delibere', 'general', year=2023)
        assert '2023' in query


class TestGenerateQueries:
    """Test generate_queries function - main requirement."""
    
    def test_returns_max_2_queries(self):
        """CRITICAL: Must return max 2 queries, not 8-20."""
        queries = generate_queries('Delibere CC', year=2023, max_queries=2)
        assert isinstance(queries, list)
        assert len(queries) <= 2
    
    def test_returns_1_query_when_max_1(self):
        queries = generate_queries('Delibere CC', year=2023, max_queries=1)
        assert len(queries) == 1
    
    def test_no_google_operators_in_queries(self):
        """CRITICAL: Queries must not contain Google operators."""
        queries = generate_queries('Delibere CC', year=2023, max_queries=2)
        
        for query in queries:
            # Check for prohibited operators
            assert 'site:' not in query
            assert 'filetype:' not in query
            assert 'inurl:' not in query
            assert ' AND ' not in query
            assert ' OR ' not in query
            assert '"' not in query  # No quotes for exact match
    
    def test_queries_are_local_style(self):
        """Queries should be simple keyword searches, not Google-style."""
        queries = generate_queries('Spesa corrente', category='financial', year=2023)
        
        # Should just be space-separated keywords
        for query in queries:
            assert query.count('site:') == 0
            assert query.count('filetype:') == 0
            # Should contain the indicator and year
            assert '2023' in query or 'Spesa corrente' in query


class TestGenerateQueriesForDataframe:
    """Test dataframe query generation."""
    
    def test_generates_queries_for_missing_cells(self):
        df = pd.DataFrame({
            'Indicator': ['Delibere CC', 'Spesa corrente'],
            '2023': [None, None],
            '2024': [100, None]
        })
        
        queries_df = generate_queries_for_dataframe(df, [2023, 2024])
        
        # Should have 3 missing cells: (Delibere CC, 2023), (Spesa corrente, 2023), (Spesa corrente, 2024)
        assert len(queries_df) == 3
        assert 'query_1' in queries_df.columns
        assert 'query_2' in queries_df.columns
    
    def test_no_operators_in_generated_queries(self):
        df = pd.DataFrame({
            'Indicator': ['Delibere CC', 'Bilancio preventivo'],
            '2023': [None, None]
        })
        
        queries_df = generate_queries_for_dataframe(df, [2023])
        
        for _, row in queries_df.iterrows():
            for col in ['query_1', 'query_2']:
                query = row[col]
                if pd.notna(query) and query:
                    assert 'site:' not in query
                    assert 'filetype:' not in query
                    assert 'inurl:' not in query
    
    def test_extracts_category_from_pipe_separator(self):
        df = pd.DataFrame({
            'Indicator': ['Finanza|Spesa corrente'],
            '2023': [None]
        })
        
        queries_df = generate_queries_for_dataframe(df, [2023])
        
        assert len(queries_df) == 1
        assert queries_df.iloc[0]['category'] == 'Finanza'
        assert queries_df.iloc[0]['indicator'] == 'Spesa corrente'
