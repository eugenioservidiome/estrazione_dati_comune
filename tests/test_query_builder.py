"""Tests for query builder."""

import pytest
from municipality_extractor.query_builder import (
    categorize_cell,
    build_queries,
    _remove_search_operators,
    _expand_with_synonyms
)


class TestCategorizeCell:
    """Test cell categorization."""
    
    def test_delibere_consiglio(self):
        assert categorize_cell('Delibere Consiglio Comunale') == 'DELIBERE_CC'
    
    def test_delibere_giunta(self):
        assert categorize_cell('Delibere Giunta Comunale') == 'DELIBERE_GC'
    
    def test_personale(self):
        assert categorize_cell('Numero dipendenti') == 'PERSONALE'
    
    def test_personale_eta_genere(self):
        assert categorize_cell('Dipendenti per età e genere') == 'PERSONALE_ETA_GENERE'
    
    def test_patrimonio(self):
        assert categorize_cell('Patrimonio netto') == 'PATRIMONIO_NETTO'
    
    def test_debiti(self):
        assert categorize_cell('Debiti verso fornitori') == 'DEBITI'
    
    def test_rifiuti_differenziata(self):
        assert categorize_cell('Raccolta differenziata %') == 'RIFIUTI_RD'
    
    def test_rifiuti_frazione(self):
        assert categorize_cell('Raccolta carta') == 'RIFIUTI_FRAZIONE'
    
    def test_biblioteca(self):
        assert categorize_cell('Prestiti biblioteca') == 'BIBLIOTECA'
    
    def test_generic_fallback(self):
        assert categorize_cell('Campo sconosciuto') == 'GENERIC'
    
    def test_uses_section_context(self):
        # Without section context: generic
        assert categorize_cell('Numero') == 'GENERIC'
        # With section context: delibere
        assert categorize_cell('Numero', 'Deliberazioni CC') == 'DELIBERE_CC'


class TestRemoveSearchOperators:
    """Test search operator removal."""
    
    def test_removes_site_operator(self):
        result = _remove_search_operators('site:example.it test query')
        assert 'site:' not in result
        assert 'test query' in result
    
    def test_removes_filetype_operator(self):
        result = _remove_search_operators('test filetype:pdf')
        assert 'filetype:' not in result
        assert 'test' in result
    
    def test_removes_inurl_operator(self):
        result = _remove_search_operators('test inurl:delibere')
        assert 'inurl:' not in result
    
    def test_removes_and_or(self):
        result = _remove_search_operators('test AND query OR other')
        assert 'AND' not in result
        assert 'OR' not in result
    
    def test_removes_quotes(self):
        result = _remove_search_operators('"test query"')
        assert '"' not in result
        assert 'test query' in result


class TestExpandWithSynonyms:
    """Test synonym expansion."""
    
    def test_expands_delibere(self):
        result = _expand_with_synonyms('delibere comunali')
        assert 'deliberazioni' in result or 'delibere' in result
    
    def test_expands_personale(self):
        result = _expand_with_synonyms('personale comunale')
        assert 'dipendenti' in result or 'personale' in result
    
    def test_no_match_returns_original(self):
        original = 'campo sconosciuto'
        result = _expand_with_synonyms(original)
        assert original in result


class TestBuildQueries:
    """Test query building."""
    
    def test_returns_list_of_queries(self):
        queries = build_queries(
            category='DELIBERE_CC',
            domain='comune.example.it',
            comune='Example',
            year=2023
        )
        assert isinstance(queries, list)
        assert len(queries) > 0
    
    def test_query_has_required_fields(self):
        queries = build_queries(
            category='DELIBERE_CC',
            domain='comune.example.it',
            comune='Example',
            year=2023
        )
        assert all('audit_query' in q for q in queries)
        assert all('semantic_query' in q for q in queries)
        assert all('priority' in q for q in queries)
        assert all('category' in q for q in queries)
    
    def test_replaces_placeholders(self):
        queries = build_queries(
            category='DELIBERE_CC',
            domain='comune.example.it',
            comune='Example',
            year=2023
        )
        # Check that domain is replaced
        assert any('comune.example.it' in q['audit_query'] for q in queries)
        # Check that year is replaced
        assert any('2023' in q['audit_query'] for q in queries)
    
    def test_semantic_query_has_no_operators(self):
        queries = build_queries(
            category='DELIBERE_CC',
            domain='comune.example.it',
            comune='Example',
            year=2023
        )
        for q in queries:
            assert 'site:' not in q['semantic_query']
            assert 'filetype:' not in q['semantic_query']
    
    def test_sorted_by_priority_descending(self):
        queries = build_queries(
            category='DELIBERE_CC',
            domain='comune.example.it',
            comune='Example',
            year=2023
        )
        priorities = [q['priority'] for q in queries]
        assert priorities == sorted(priorities, reverse=True)
    
    def test_external_queries_blocked_by_default(self):
        queries = build_queries(
            category='ISTAT_POPOLAZIONE',
            domain='comune.example.it',
            comune='Example',
            year=2023,
            allow_external=False
        )
        assert len(queries) == 0
    
    def test_external_queries_allowed_when_enabled(self):
        queries = build_queries(
            category='ISTAT_POPOLAZIONE',
            domain='comune.example.it',
            comune='Example',
            year=2023,
            allow_external=True
        )
        assert len(queries) > 0
        assert any('istat.it' in q['audit_query'] for q in queries)
    
    def test_handles_extra_params(self):
        queries = build_queries(
            category='GENERIC',
            domain='comune.example.it',
            comune='Example',
            year=2023,
            extra_params={'LABEL': 'test_label'}
        )
        assert any('test_label' in q['audit_query'] for q in queries)
