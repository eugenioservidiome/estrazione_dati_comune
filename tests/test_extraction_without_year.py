"""Tests for heuristic extraction without year proximity requirement."""

import pytest
from comune_extractor.extract_heuristics import (
    normalize_italian_number,
    extract_number_with_context,
    score_extraction,
    extract_value_heuristic
)


class TestNormalizeItalianNumber:
    """Test Italian number normalization."""
    
    def test_basic_italian_format(self):
        assert normalize_italian_number('1.234,56') == 1234.56
        assert normalize_italian_number('1234,56') == 1234.56
    
    def test_with_spaces(self):
        assert normalize_italian_number('1 234,56') == 1234.56
    
    def test_negative_in_parentheses(self):
        assert normalize_italian_number('(1.234,56)') == -1234.56
    
    def test_explicit_negative(self):
        assert normalize_italian_number('-1.234,56') == -1234.56
    
    def test_with_euro_symbol(self):
        assert normalize_italian_number('€ 1.234,56') == 1234.56
        assert normalize_italian_number('1.234,56 €') == 1234.56
    
    def test_percentage(self):
        assert normalize_italian_number('12,5%') == 0.125
        assert normalize_italian_number('100%') == 1.0
    
    def test_invalid_returns_none(self):
        assert normalize_italian_number('abc') is None
        assert normalize_italian_number('') is None


class TestExtractValueWithoutYearProximity:
    """Test that extraction works even without year nearby."""
    
    def test_extracts_when_keyword_present_no_year(self):
        """CRITICAL: Must extract value near keyword even if year not nearby."""
        text = """
        Raccolta differenziata nel comune
        
        Il totale della raccolta differenziata è stato di 1.234,56 tonnellate.
        La percentuale rispetto ai rifiuti totali è del 65%.
        """
        
        keywords = ['raccolta differenziata', 'raccolta']
        
        # Extract WITHOUT specifying year
        results = extract_value_heuristic(text, keywords)
        
        # Should still find the number
        assert len(results) > 0
        # Should find either the tonnellate or percentage
        values = [r['value'] for r in results]
        assert 1234.56 in values or 0.65 in values
    
    def test_score_higher_with_multiple_keywords(self):
        """Scoring should prioritize keyword density over year."""
        snippet_with_keywords = "La spesa corrente per il bilancio comunale è 500.000"
        snippet_without_keywords = "Nel 2023 il valore è 500.000"
        
        keywords = ['spesa corrente', 'bilancio']
        
        score_with = score_extraction(500000, snippet_with_keywords, keywords, year=2023)
        score_without = score_extraction(500000, snippet_without_keywords, keywords, year=2023)
        
        # Keyword match should score higher than year match
        assert score_with > score_without
    
    def test_extracts_multiple_numbers_near_keyword(self):
        """Should find all numbers near keywords."""
        text = """
        Personale comunale:
        - Dipendenti a tempo indeterminato: 45
        - Dipendenti a tempo determinato: 12
        - Totale: 57
        """
        
        keywords = ['dipendenti', 'personale']
        
        results = extract_value_heuristic(text, keywords, top_k=5)
        
        # Should find multiple numbers
        assert len(results) >= 2
        values = [r['value'] for r in results]
        assert 45 in values or 12 in values or 57 in values
    
    def test_snippet_limited_to_240_chars(self):
        """Snippets should be max 240 characters."""
        long_text = "a" * 1000 + " spesa corrente " + "b" * 1000 + " 12345 " + "c" * 1000
        
        keywords = ['spesa corrente']
        results = extract_value_heuristic(long_text, keywords)
        
        if results:
            for result in results:
                # Snippet should be truncated
                assert len(result['snippet']) <= 243  # 240 + "..."


class TestScoreExtraction:
    """Test extraction scoring."""
    
    def test_keyword_in_snippet_increases_score(self):
        """Keywords should significantly boost score."""
        snippet = "La spesa corrente per il bilancio 2023 è 500.000"
        keywords = ['spesa corrente', 'bilancio']
        
        score = score_extraction(500000, snippet, keywords, year=2023)
        
        # Should have positive score due to keywords
        assert score > 0
    
    def test_year_optional_not_required(self):
        """Year proximity should be optional bonus, not requirement."""
        snippet_no_year = "La spesa corrente del comune è 500.000 euro"
        snippet_with_year = "La spesa corrente 2023 è 500.000 euro"
        
        keywords = ['spesa corrente']
        
        score_no_year = score_extraction(500000, snippet_no_year, keywords, year=2023)
        score_with_year = score_extraction(500000, snippet_with_year, keywords, year=2023)
        
        # Both should have positive scores
        assert score_no_year > 0
        assert score_with_year > 0
        # With year should be slightly higher, but not dramatically
        assert score_with_year > score_no_year
        # But the difference should be small (just 0.5 bonus)
        assert (score_with_year - score_no_year) <= 1.0
    
    def test_range_check_affects_score(self):
        """Value within expected range should boost score."""
        snippet = "La popolazione è 5000 abitanti"
        keywords = ['popolazione']
        
        score_in_range = score_extraction(5000, snippet, keywords, 
                                          expected_range=(1000, 100000))
        score_out_range = score_extraction(5000, snippet, keywords, 
                                           expected_range=(100000, 1000000))
        
        assert score_in_range > score_out_range
    
    def test_extreme_values_penalized(self):
        """Very small or large numbers should be penalized."""
        snippet = "Il valore è"
        keywords = ['valore']
        
        score_tiny = score_extraction(0.001, snippet, keywords)
        score_huge = score_extraction(1e13, snippet, keywords)
        score_normal = score_extraction(1000, snippet, keywords)
        
        assert score_normal > score_tiny
        assert score_normal > score_huge


class TestExtractValueHeuristic:
    """Test main extraction function."""
    
    def test_returns_top_k_results(self):
        """Should return top_k results sorted by score."""
        text = """
        Bilancio comunale 2023:
        - Entrate: 1.000.000
        - Uscite: 950.000
        - Avanzo: 50.000
        """
        
        keywords = ['bilancio']
        results = extract_value_heuristic(text, keywords, top_k=3)
        
        assert len(results) <= 3
        assert len(results) > 0
        
        # Results should be sorted by score descending
        if len(results) > 1:
            scores = [r['score'] for r in results]
            assert scores == sorted(scores, reverse=True)
    
    def test_year_parameter_passed_to_scoring(self):
        """Year should be passed to scoring for optional bonus."""
        text = "Spesa corrente 2023: 500.000 euro"
        keywords = ['spesa corrente']
        
        results_with_year = extract_value_heuristic(text, keywords, year=2023)
        results_without_year = extract_value_heuristic(text, keywords, year=None)
        
        # Both should find values
        assert len(results_with_year) > 0
        assert len(results_without_year) > 0
        
        # With year might have slightly higher scores
        if results_with_year and results_without_year:
            # But both should be valid extractions
            assert results_with_year[0]['value'] > 0
            assert results_without_year[0]['value'] > 0
