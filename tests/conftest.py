"""Shared test fixtures and utilities."""

import pytest
import tempfile
from pathlib import Path
from municipality_extractor.config import RunConfig


@pytest.fixture
def temp_dir():
    """Create a temporary directory for tests."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def sample_config(temp_dir):
    """Create a sample configuration for tests."""
    return RunConfig(
        base_url='https://www.comune.example.it',
        comune='Example',
        years_to_fill=[2023, 2024],
        input_dir=temp_dir / 'input',
        output_dir=temp_dir / 'output',
        max_pages=10,  # Small for tests
        politeness_delay=0.1,  # Fast for tests
        respect_robots=False  # Don't check robots.txt in tests
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
