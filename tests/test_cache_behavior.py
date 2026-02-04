"""Test cache behavior - verify second run doesn't redownload/re-extract."""

import pytest
import tempfile
import shutil
from pathlib import Path
from src.comune_extractor.catalog import Catalog


@pytest.fixture
def temp_catalog():
    """Create temporary catalog for testing."""
    temp_dir = tempfile.mkdtemp()
    db_path = Path(temp_dir) / "test_catalog.sqlite"
    catalog = Catalog(db_path)
    
    yield catalog
    
    # Cleanup
    shutil.rmtree(temp_dir)


def test_catalog_initialization(temp_catalog):
    """Test that catalog initializes correctly."""
    stats = temp_catalog.get_stats()
    assert stats['pdfs'] == 0
    assert stats['texts'] == 0
    assert stats['llm_cache'] == 0


def test_pdf_cache_by_url(temp_catalog):
    """Test PDF caching by URL."""
    # Add PDF
    temp_catalog.add_pdf(
        url="https://example.com/test.pdf",
        sha1="abc123",
        original_name="test.pdf",
        local_path="/tmp/test.pdf",
        detected_year=2023,
        content_type="application/pdf",
        size_bytes=1000
    )
    
    # Check it exists by URL
    result = temp_catalog.pdf_exists("https://example.com/test.pdf")
    assert result is not None
    assert result['sha1'] == "abc123"
    assert result['detected_year'] == 2023
    
    # Check non-existent URL
    result = temp_catalog.pdf_exists("https://example.com/other.pdf")
    assert result is None


def test_pdf_cache_by_sha1(temp_catalog):
    """Test PDF caching by SHA1 (deduplication)."""
    # Add PDF
    temp_catalog.add_pdf(
        url="https://example.com/test.pdf",
        sha1="abc123",
        original_name="test.pdf",
        local_path="/tmp/test.pdf",
        detected_year=2023,
        content_type="application/pdf",
        size_bytes=1000
    )
    
    # Check it exists by SHA1
    result = temp_catalog.pdf_exists_by_sha1("abc123")
    assert result is not None
    assert result['url'] == "https://example.com/test.pdf"
    
    # Add same PDF from different URL (deduplication)
    temp_catalog.add_pdf(
        url="https://example.com/mirror/test.pdf",
        sha1="abc123",  # Same SHA1
        original_name="test.pdf",
        local_path="/tmp/test.pdf",
        detected_year=2023,
        content_type="application/pdf",
        size_bytes=1000
    )
    
    # Should still be 1 PDF
    stats = temp_catalog.get_stats()
    assert stats['pdfs'] == 1  # Replaced, not added
    
    # But new URL should be in catalog
    result = temp_catalog.pdf_exists("https://example.com/mirror/test.pdf")
    assert result is not None


def test_text_cache(temp_catalog):
    """Test text extraction caching."""
    # Add PDF first
    temp_catalog.add_pdf(
        url="https://example.com/test.pdf",
        sha1="abc123",
        original_name="test.pdf",
        local_path="/tmp/test.pdf",
        detected_year=2023,
        content_type="application/pdf",
        size_bytes=1000
    )
    
    # Check text doesn't exist yet
    result = temp_catalog.text_exists("abc123")
    assert result is None
    
    # Add text
    temp_catalog.add_text(
        sha1="abc123",
        text_path="/tmp/test.txt",
        extractor="pymupdf",
        pages=5,
        text_len=1500
    )
    
    # Check text now exists
    result = temp_catalog.text_exists("abc123")
    assert result is not None
    assert result['extractor'] == "pymupdf"
    assert result['pages'] == 5
    
    # Stats should reflect both PDF and text
    stats = temp_catalog.get_stats()
    assert stats['pdfs'] == 1
    assert stats['texts'] == 1


def test_llm_cache(temp_catalog):
    """Test LLM result caching."""
    # Check cache doesn't exist
    result = temp_catalog.get_llm_cache("test_key")
    assert result is None
    
    # Add to cache
    temp_catalog.add_llm_cache(
        key="test_key",
        json_path="/tmp/llm_result.json",
        model="gpt-4o-mini"
    )
    
    # Check cache exists
    result = temp_catalog.get_llm_cache("test_key")
    assert result is not None
    assert result['model'] == "gpt-4o-mini"
    assert result['json_path'] == "/tmp/llm_result.json"


def test_get_pdfs_by_year(temp_catalog):
    """Test filtering PDFs by year."""
    # Add PDFs with different years
    temp_catalog.add_pdf(
        url="https://example.com/2023.pdf",
        sha1="abc123",
        original_name="2023.pdf",
        local_path="/tmp/2023.pdf",
        detected_year=2023,
        content_type="application/pdf",
        size_bytes=1000
    )
    
    temp_catalog.add_pdf(
        url="https://example.com/2024.pdf",
        sha1="def456",
        original_name="2024.pdf",
        local_path="/tmp/2024.pdf",
        detected_year=2024,
        content_type="application/pdf",
        size_bytes=1000
    )
    
    temp_catalog.add_pdf(
        url="https://example.com/unknown.pdf",
        sha1="ghi789",
        original_name="unknown.pdf",
        local_path="/tmp/unknown.pdf",
        detected_year=None,
        content_type="application/pdf",
        size_bytes=1000
    )
    
    # Get PDFs by year
    pdfs_2023 = temp_catalog.get_pdfs_by_year(2023)
    assert len(pdfs_2023) == 1
    assert pdfs_2023[0]['sha1'] == "abc123"
    
    pdfs_2024 = temp_catalog.get_pdfs_by_year(2024)
    assert len(pdfs_2024) == 1
    assert pdfs_2024[0]['sha1'] == "def456"
    
    pdfs_unknown = temp_catalog.get_pdfs_by_year(None)
    assert len(pdfs_unknown) == 1
    assert pdfs_unknown[0]['sha1'] == "ghi789"
    
    # Get all PDFs
    all_pdfs = temp_catalog.get_all_pdfs()
    assert len(all_pdfs) == 3
