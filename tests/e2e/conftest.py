# tests/e2e/conftest.py
import pytest
import os
from core.config import settings
from database.connection import close_duckdb_connection
from database.registry import register_csv as _register_csv, register_parquet as _register_parquet

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
FIXTURES_DIR = os.path.join(PROJECT_ROOT, "fixtures", "clean")
EDGE_CASES_DIR = os.path.join(PROJECT_ROOT, "fixtures", "dirty")

# ── Pytest fixture wrappers (for injection into test fixtures) ────────────────

@pytest.fixture
def register_csv():
    """Pytest fixture that wraps database.registry.register_csv."""
    return _register_csv

@pytest.fixture
def register_parquet():
    """Pytest fixture that wraps database.registry.register_parquet."""
    return _register_parquet

# ── Core session setup ────────────────────────────────────────────────────────

@pytest.fixture(autouse=True)
def use_in_memory_db(monkeypatch):
    """
    Forces DuckDB to be in-memory and registers all clean fixture CSVs
    before every E2E test, then tears down cleanly.
    """
    monkeypatch.setattr(settings, "duckdb_file_path", ":memory:")

    # Register all three clean fixture tables
    _register_csv(os.path.join(FIXTURES_DIR, "sales.csv"), "sales")
    _register_csv(os.path.join(FIXTURES_DIR, "employees.csv"), "employees")
    _register_csv(os.path.join(FIXTURES_DIR, "products.csv"), "products")

    yield
    close_duckdb_connection()