"""SQLite catalog for PDFs, texts, and LLM cache."""

import sqlite3
import hashlib
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Dict, List, Any
from contextlib import contextmanager


class Catalog:
    """SQLite catalog for tracking PDFs, extracted texts, and LLM cache."""
    
    def __init__(self, db_path: Path):
        self.db_path = db_path
        self._init_db()
    
    def _init_db(self):
        """Initialize database schema."""
        with self._conn() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS pdfs (
                    sha1 TEXT PRIMARY KEY,
                    url TEXT NOT NULL,
                    original_name TEXT,
                    local_path TEXT NOT NULL,
                    detected_year INTEGER,
                    downloaded_at TEXT NOT NULL,
                    content_type TEXT,
                    size_bytes INTEGER
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_pdfs_url ON pdfs(url)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_pdfs_year ON pdfs(detected_year)
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS texts (
                    sha1 TEXT PRIMARY KEY,
                    text_path TEXT NOT NULL,
                    extracted_at TEXT NOT NULL,
                    extractor TEXT NOT NULL,
                    pages INTEGER,
                    text_len INTEGER,
                    FOREIGN KEY (sha1) REFERENCES pdfs(sha1)
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS llm_cache (
                    key TEXT PRIMARY KEY,
                    json_path TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    model TEXT NOT NULL
                )
            """)
            
            conn.commit()
    
    @contextmanager
    def _conn(self):
        """Context manager for database connections."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()
    
    @staticmethod
    def compute_sha1(file_path: Path) -> str:
        """Compute SHA1 hash of a file."""
        sha1 = hashlib.sha1()
        with open(file_path, 'rb') as f:
            while chunk := f.read(8192):
                sha1.update(chunk)
        return sha1.hexdigest()
    
    def pdf_exists(self, url: str) -> Optional[Dict[str, Any]]:
        """Check if PDF from URL already exists in catalog."""
        with self._conn() as conn:
            row = conn.execute(
                "SELECT * FROM pdfs WHERE url = ?", (url,)
            ).fetchone()
            return dict(row) if row else None
    
    def pdf_exists_by_sha1(self, sha1: str) -> Optional[Dict[str, Any]]:
        """Check if PDF with SHA1 already exists in catalog."""
        with self._conn() as conn:
            row = conn.execute(
                "SELECT * FROM pdfs WHERE sha1 = ?", (sha1,)
            ).fetchone()
            return dict(row) if row else None
    
    def add_pdf(self, url: str, sha1: str, original_name: str, local_path: str,
                detected_year: Optional[int], content_type: str, size_bytes: int):
        """Add PDF to catalog."""
        with self._conn() as conn:
            conn.execute("""
                INSERT OR REPLACE INTO pdfs 
                (sha1, url, original_name, local_path, detected_year, downloaded_at, content_type, size_bytes)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (sha1, url, original_name, local_path, detected_year, 
                  datetime.now(timezone.utc).isoformat(), content_type, size_bytes))
            conn.commit()
    
    def update_pdf_year(self, sha1: str, detected_year: int):
        """Update detected year for a PDF."""
        with self._conn() as conn:
            conn.execute(
                "UPDATE pdfs SET detected_year = ? WHERE sha1 = ?",
                (detected_year, sha1)
            )
            conn.commit()
    
    def text_exists(self, sha1: str) -> Optional[Dict[str, Any]]:
        """Check if extracted text exists for PDF."""
        with self._conn() as conn:
            row = conn.execute(
                "SELECT * FROM texts WHERE sha1 = ?", (sha1,)
            ).fetchone()
            return dict(row) if row else None
    
    def add_text(self, sha1: str, text_path: str, extractor: str, 
                 pages: int, text_len: int):
        """Add extracted text to catalog."""
        with self._conn() as conn:
            conn.execute("""
                INSERT OR REPLACE INTO texts 
                (sha1, text_path, extracted_at, extractor, pages, text_len)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (sha1, text_path, datetime.now(timezone.utc).isoformat(), 
                  extractor, pages, text_len))
            conn.commit()
    
    def get_llm_cache(self, key: str) -> Optional[Dict[str, Any]]:
        """Get LLM cache entry."""
        with self._conn() as conn:
            row = conn.execute(
                "SELECT * FROM llm_cache WHERE key = ?", (key,)
            ).fetchone()
            return dict(row) if row else None
    
    def add_llm_cache(self, key: str, json_path: str, model: str):
        """Add LLM cache entry."""
        with self._conn() as conn:
            conn.execute("""
                INSERT OR REPLACE INTO llm_cache 
                (key, json_path, created_at, model)
                VALUES (?, ?, ?, ?)
            """, (key, json_path, datetime.now(timezone.utc).isoformat(), model))
            conn.commit()
    
    def get_pdfs_by_year(self, year: Optional[int]) -> List[Dict[str, Any]]:
        """Get all PDFs for a specific year."""
        with self._conn() as conn:
            if year is None:
                rows = conn.execute(
                    "SELECT * FROM pdfs WHERE detected_year IS NULL"
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM pdfs WHERE detected_year = ?", (year,)
                ).fetchall()
            return [dict(row) for row in rows]
    
    def get_all_pdfs(self) -> List[Dict[str, Any]]:
        """Get all PDFs from catalog."""
        with self._conn() as conn:
            rows = conn.execute("SELECT * FROM pdfs").fetchall()
            return [dict(row) for row in rows]
    
    def get_stats(self) -> Dict[str, int]:
        """Get catalog statistics."""
        with self._conn() as conn:
            pdf_count = conn.execute("SELECT COUNT(*) FROM pdfs").fetchone()[0]
            text_count = conn.execute("SELECT COUNT(*) FROM texts").fetchone()[0]
            llm_count = conn.execute("SELECT COUNT(*) FROM llm_cache").fetchone()[0]
            
            return {
                "pdfs": pdf_count,
                "texts": text_count,
                "llm_cache": llm_count,
            }
