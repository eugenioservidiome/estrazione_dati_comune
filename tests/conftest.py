"""Shared test fixtures and utilities."""

import pytest
import tempfile
from pathlib import Path

# Import from new package
from comune_extractor.config import Config


@pytest.fixture
def temp_dir():
    """Create a temporary directory for tests."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def sample_config(temp_dir):
    """Create a sample configuration for tests."""
    return Config(
        base_url='https://www.comune.example.it',
        comune='Example',
        years=[2023, 2024],
        input_dir=temp_dir / 'input',
        output_dir=temp_dir / 'output',
        workspace=temp_dir / 'workspace',
        max_pages=10,
        crawl_delay=0.1,
        respect_robots=False
    )


@pytest.fixture
def sample_html_doc():
    """Sample HTML document for testing."""
    return {
        'url': 'https://www.comune.example.it/page1',
        'text': 'Nel 2023 il comune ha approvato 45 delibere del consiglio comunale.',
        'type': 'html'
    }


@pytest.fixture
def sample_pdf_doc():
    """Sample PDF document for testing."""
    return {
        'url': 'https://www.comune.example.it/doc.pdf',
        'text': 'Delibera n. 12 del 2024. Il patrimonio netto ammonta a 1.234.567,89 euro.',
        'type': 'pdf'
    }
