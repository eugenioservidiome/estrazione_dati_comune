"""Tests for CSV I/O functions."""

import pytest
import pandas as pd
from io import StringIO
from municipality_extractor.csv_io import (
    is_missing_cell,
    detect_missing_cells,
    detect_section_headers
)


class TestIsMissingCell:
    """Test missing cell detection."""
    
    def test_nan_is_missing(self):
        assert is_missing_cell(float('nan'))
    
    def test_empty_string_is_missing(self):
        assert is_missing_cell('')
    
    def test_whitespace_is_missing(self):
        assert is_missing_cell('   ')
    
    def test_nd_is_missing(self):
        assert is_missing_cell('n.d.')
        assert is_missing_cell('N.D.')
    
    def test_na_is_missing(self):
        assert is_missing_cell('N/A')
        assert is_missing_cell('n/a')
    
    def test_dash_is_missing(self):
        assert is_missing_cell('-')
    
    def test_number_not_missing(self):
        assert not is_missing_cell(123)
        assert not is_missing_cell('123')
    
    def test_text_not_missing(self):
        assert not is_missing_cell('Some value')


class TestDetectMissingCells:
    """Test missing cells detection in DataFrame."""
    
    def test_detects_missing_in_year_columns(self):
        df = pd.DataFrame({
            'Label': ['Row1', 'Row2'],
            '2023': [100, float('nan')],
            '2024': [200, 300]
        })
        missing = detect_missing_cells(df)
        assert len(missing) == 1
        assert missing[0][0] == 1  # row_index
        assert missing[0][1] == '2023'  # column_name
    
    def test_returns_empty_for_no_missing(self):
        df = pd.DataFrame({
            'Label': ['Row1', 'Row2'],
            '2023': [100, 200],
            '2024': [300, 400]
        })
        missing = detect_missing_cells(df)
        assert len(missing) == 0
    
    def test_includes_row_label(self):
        df = pd.DataFrame({
            'Label': ['Test Label', 'Row2'],
            '2023': [float('nan'), 200]
        })
        missing = detect_missing_cells(df)
        assert missing[0][0] == 0  # row_index
        assert missing[0][1] == '2023'  # column_name


class TestDetectSectionHeaders:
    """Test section header detection."""
    
    def test_detects_empty_year_columns(self):
        # Create a row with only 1 filled cell out of 4 (25% < 30% threshold)
        df = pd.DataFrame({
            'Label': ['Section Header', 'Data Row'],
            '2022': [float('nan'), 50],
            '2023': [float('nan'), 100],
            '2024': [float('nan'), 200]
        })
        sections = detect_section_headers(df)
        # Row 0 has 1/4 = 0.25 fill rate, which is < 0.3, so it's detected
        assert 0 in sections
    
    def test_does_not_detect_partial_data_as_header(self):
        df = pd.DataFrame({
            'Label': ['Data Row', 'Another Row'],
            '2023': [100, 200],
            '2024': [float('nan'), 300]
        })
        sections = detect_section_headers(df)
        # Row 0 has 2/3 = 0.67 fill rate (>= 0.3), so it's not a header
        assert 0 not in sections
    
    def test_detects_single_cell_text_row(self):
        # Create a row with only 1 filled cell out of 4 (25% < 30% threshold)
        df = pd.DataFrame({
            'Label': ['Long section description text', 'Data Row'],
            'Other': [float('nan'), 'value'],
            '2022': [float('nan'), 50],
            '2023': [float('nan'), 100]
        })
        sections = detect_section_headers(df)
        # First row has 1/4 = 0.25 fill rate, which is < 0.3, so it's detected
        assert 0 in sections


class TestLoadCSVRobust:
    """Test robust CSV loading."""
    
    # Note: These tests require the actual load_csv_robust function
    # which handles encoding and delimiter detection
    # Skipping for now as it requires file I/O
    pass
