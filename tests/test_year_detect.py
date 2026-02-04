"""Test year detection from URLs, filenames, and text."""

import pytest
from pathlib import Path
from src.comune_extractor.year_detect import (
    detect_year_from_url,
    detect_year_from_filename,
    detect_year_from_text
)


def test_detect_year_from_url_simple():
    """Test simple year in URL."""
    url = "https://example.com/bilancio_2023.pdf"
    assert detect_year_from_url(url) == 2023


def test_detect_year_from_url_path():
    """Test year in URL path."""
    url = "https://example.com/documenti/2024/bilancio.pdf"
    assert detect_year_from_url(url) == 2024


def test_detect_year_from_url_multiple():
    """Test multiple years in URL - should return most recent."""
    url = "https://example.com/2020/confronto_2023.pdf"
    assert detect_year_from_url(url) == 2023


def test_detect_year_from_url_no_year():
    """Test URL without year."""
    url = "https://example.com/bilancio.pdf"
    assert detect_year_from_url(url) is None


def test_detect_year_from_url_out_of_range():
    """Test year outside valid range (1990-2030)."""
    url = "https://example.com/storia_1850.pdf"
    assert detect_year_from_url(url) is None


def test_detect_year_from_filename():
    """Test year detection from filename."""
    assert detect_year_from_filename("bilancio_2023.pdf") == 2023
    assert detect_year_from_filename("doc_2024_finale.pdf") == 2024
    assert detect_year_from_filename("documento.pdf") is None


def test_detect_year_from_text_simple():
    """Test year detection from text content."""
    text = "Bilancio comunale anno 2023. Spese totali: €1.234.567"
    year = detect_year_from_text(text)
    assert year == 2023


def test_detect_year_from_text_multiple():
    """Test multiple years - should return most frequent."""
    text = """
    Confronto bilancio 2022 e 2023.
    Anno 2023: spese €100.000
    Anno 2023: entrate €150.000
    Anno 2022: spese €90.000
    """
    year = detect_year_from_text(text)
    assert year == 2023  # More frequent


def test_detect_year_from_text_no_year():
    """Test text without year."""
    text = "Documento generico senza anno."
    assert detect_year_from_text(text) is None


def test_detect_year_from_text_old_years():
    """Test that old years are filtered out."""
    text = "Storia del comune dal 1850 al 1900."
    assert detect_year_from_text(text) is None


def test_detect_year_valid_range():
    """Test years at boundaries of valid range."""
    assert detect_year_from_url("https://example.com/doc_1990.pdf") == 1990
    assert detect_year_from_url("https://example.com/doc_2030.pdf") == 2030
    assert detect_year_from_url("https://example.com/doc_1989.pdf") is None
    assert detect_year_from_url("https://example.com/doc_2031.pdf") is None
