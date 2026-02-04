"""Path management for folder layout: data/{comune}/{anno}/pdf/, text/, etc."""

from pathlib import Path
from typing import Optional


def get_pdf_dir(base_dir: Path, comune: str, year: Optional[int]) -> Path:
    """Get PDF directory for a specific year or unknown."""
    comune_lower = comune.lower()
    if year is None:
        return base_dir / comune_lower / "unknown" / "pdf"
    return base_dir / comune_lower / str(year) / "pdf"


def get_text_dir(base_dir: Path, comune: str, year: Optional[int]) -> Path:
    """Get text directory for a specific year or unknown."""
    comune_lower = comune.lower()
    if year is None:
        return base_dir / comune_lower / "unknown" / "text"
    return base_dir / comune_lower / str(year) / "text"


def get_llm_dir(base_dir: Path, comune: str, year: Optional[int]) -> Path:
    """Get LLM cache directory for a specific year or unknown."""
    comune_lower = comune.lower()
    if year is None:
        return base_dir / comune_lower / "unknown" / "llm"
    return base_dir / comune_lower / str(year) / "llm"


def get_index_dir(base_dir: Path, comune: str) -> Path:
    """Get index directory for BM25 indices."""
    comune_lower = comune.lower()
    return base_dir / comune_lower / "index"


def get_catalog_path(base_dir: Path, comune: str) -> Path:
    """Get SQLite catalog database path."""
    comune_lower = comune.lower()
    return base_dir / comune_lower / "catalog.sqlite"


def ensure_year_dirs(base_dir: Path, comune: str, years: list[int]):
    """Create all necessary directories for specified years."""
    for year in years:
        get_pdf_dir(base_dir, comune, year).mkdir(parents=True, exist_ok=True)
        get_text_dir(base_dir, comune, year).mkdir(parents=True, exist_ok=True)
        get_llm_dir(base_dir, comune, year).mkdir(parents=True, exist_ok=True)
    
    # Create unknown directories
    get_pdf_dir(base_dir, comune, None).mkdir(parents=True, exist_ok=True)
    get_text_dir(base_dir, comune, None).mkdir(parents=True, exist_ok=True)
    get_llm_dir(base_dir, comune, None).mkdir(parents=True, exist_ok=True)
    
    # Create index directory
    get_index_dir(base_dir, comune).mkdir(parents=True, exist_ok=True)
    
    # Create catalog parent directory
    get_catalog_path(base_dir, comune).parent.mkdir(parents=True, exist_ok=True)


def sanitize_filename(filename: str, max_length: int = 200) -> str:
    """Sanitize filename for safe storage."""
    # Remove or replace unsafe characters
    safe = "".join(c if c.isalnum() or c in ".-_" else "_" for c in filename)
    # Limit length
    if len(safe) > max_length:
        name, ext = safe.rsplit(".", 1) if "." in safe else (safe, "")
        safe = name[:max_length - len(ext) - 1] + "." + ext if ext else name[:max_length]
    return safe
