"""Test Italian number parsing and normalization."""

import pytest
from src.comune_extractor.extract_heuristics import normalize_italian_number


def test_normalize_basic_integer():
    """Test basic integer parsing."""
    assert normalize_italian_number("1234") == 1234.0


def test_normalize_italian_decimal():
    """Test Italian decimal format (comma as decimal separator)."""
    assert normalize_italian_number("1234,56") == 1234.56


def test_normalize_thousands_with_dots():
    """Test thousands separator with dots."""
    assert normalize_italian_number("1.234.567") == 1234567.0


def test_normalize_thousands_with_dots_and_decimal():
    """Test full Italian format: dots for thousands, comma for decimal."""
    assert normalize_italian_number("1.234.567,89") == 1234567.89


def test_normalize_thousands_with_spaces():
    """Test thousands separator with spaces."""
    assert normalize_italian_number("1 234 567") == 1234567.0


def test_normalize_thousands_spaces_and_decimal():
    """Test spaces for thousands, comma for decimal."""
    assert normalize_italian_number("1 234,56") == 1234.56


def test_normalize_with_whitespace():
    """Test number with surrounding whitespace."""
    assert normalize_italian_number("  1234,56  ") == 1234.56


def test_normalize_small_decimal():
    """Test small decimal number."""
    assert normalize_italian_number("0,5") == 0.5


def test_normalize_invalid_returns_none():
    """Test that invalid input returns None."""
    assert normalize_italian_number("abc") is None
    assert normalize_italian_number("") is None


def test_normalize_mixed_formats():
    """Test various mixed formats."""
    assert normalize_italian_number("12.345,67") == 12345.67
    assert normalize_italian_number("999.999,99") == 999999.99
    assert normalize_italian_number("5,00") == 5.0
