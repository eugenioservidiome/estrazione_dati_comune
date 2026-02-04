"""Tests for utility functions."""

import pytest
from municipality_extractor.utils import (
    normalize_url,
    same_domain,
    is_useful_extension,
    parse_italian_number,
    extract_year_from_text,
    url_to_cache_key
)


class TestNormalizeUrl:
    """Test URL normalization."""
    
    def test_adds_https_if_missing(self):
        result = normalize_url('comune.example.it', 'https://example.it')
        assert result is not None
        assert result.startswith('https://')
    
    def test_removes_fragment(self):
        url = normalize_url('https://example.it/page#section')
        assert '#' not in url
    
    def test_filters_mailto(self):
        assert normalize_url('mailto:test@example.it') is None
    
    def test_filters_tel(self):
        assert normalize_url('tel:+39123456') is None
    
    def test_filters_javascript(self):
        assert normalize_url('javascript:void(0)') is None
    
    def test_handles_relative_with_base(self):
        result = normalize_url('/page', 'https://example.it')
        assert result == 'https://example.it/page/'
    
    def test_preserves_query_string(self):
        url = normalize_url('https://example.it/page?id=123')
        assert 'id=123' in url


class TestSameDomain:
    """Test domain comparison."""
    
    def test_same_domain_true(self):
        assert same_domain('https://example.it/page1', 'https://example.it/page2')
    
    def test_same_domain_false(self):
        assert not same_domain('https://example.it', 'https://other.it')
    
    def test_handles_subdomain_as_different(self):
        assert not same_domain('https://example.it', 'https://sub.example.it')


class TestIsUsefulExtension:
    """Test extension filtering."""
    
    def test_html_is_useful(self):
        assert is_useful_extension('https://example.it/page.html')
    
    def test_pdf_is_useful(self):
        assert is_useful_extension('https://example.it/doc.pdf')
    
    def test_image_not_useful(self):
        assert not is_useful_extension('https://example.it/img.jpg')
    
    def test_css_not_useful(self):
        assert not is_useful_extension('https://example.it/style.css')
    
    def test_no_extension_is_useful(self):
        assert is_useful_extension('https://example.it/page')


class TestParseItalianNumber:
    """Test Italian number parsing."""
    
    def test_simple_integer(self):
        assert parse_italian_number('123') == 123.0
    
    def test_with_decimal_comma(self):
        assert parse_italian_number('123,45') == 123.45
    
    def test_with_thousands_separator(self):
        assert parse_italian_number('1.234') == 1234.0
    
    def test_with_both_separators(self):
        assert parse_italian_number('1.234,56') == 1234.56
    
    def test_with_percentage_sign(self):
        result = parse_italian_number('12,5%')
        assert result == 12.5
    
    def test_with_euro_sign(self):
        assert parse_italian_number('€1.234,56') == 1234.56
    
    def test_negative_number(self):
        assert parse_italian_number('-123,45') == -123.45
    
    def test_positive_sign(self):
        assert parse_italian_number('+123,45') == 123.45
    
    def test_invalid_returns_none(self):
        assert parse_italian_number('abc') is None
    
    def test_empty_returns_none(self):
        assert parse_italian_number('') is None


class TestExtractYearFromText:
    """Test year extraction."""
    
    def test_extract_single_year(self):
        assert extract_year_from_text('Dati del 2023') == 2023
    
    def test_extract_first_year_if_multiple(self):
        assert extract_year_from_text('Dati 2023 e 2024') == 2023
    
    def test_filter_by_valid_years(self):
        result = extract_year_from_text('Anno 2020 e 2023', valid_years=[2023, 2024])
        assert result == 2023
    
    def test_no_year_returns_none(self):
        assert extract_year_from_text('Nessun anno qui') is None
    
    def test_year_outside_range_ignored(self):
        # extract_year_from_text only extracts years 2000-2099
        assert extract_year_from_text('Anno 1999') is None
        # But years in range work
        assert extract_year_from_text('Anno 2023') == 2023


class TestUrlToCacheKey:
    """Test URL to cache key conversion."""
    
    def test_generates_40_char_hash(self):
        key = url_to_cache_key('https://example.it/page')
        assert len(key) == 40
    
    def test_same_url_same_key(self):
        url = 'https://example.it/page'
        assert url_to_cache_key(url) == url_to_cache_key(url)
    
    def test_different_url_different_key(self):
        key1 = url_to_cache_key('https://example.it/page1')
        key2 = url_to_cache_key('https://example.it/page2')
        assert key1 != key2
