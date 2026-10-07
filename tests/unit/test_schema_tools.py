# tests/unit/test_schema_tools.py
import pytest
from core.config import settings
from database.connection import get_duckdb_connection, close_duckdb_connection
from tools.schema_tools import introspect_schema

@pytest.fixture(autouse=True)
def use_in_memory_db(monkeypatch):
    """
    Forces the DuckDB file path to be in-memory for unit tests.
    Closes the connection after each test run.
    """
    monkeypatch.setattr(settings, "duckdb_file_path", ":memory:")
    yield
    close_duckdb_connection()

def test_introspect_schema_success():
    """Verify that introspect_schema correctly extracts table structure and sample rows."""
    conn = get_duckdb_connection()
    # Set up some dummy tables
    conn.execute("CREATE TABLE users (id INTEGER, name VARCHAR)")
    conn.execute("INSERT INTO users VALUES (1, 'Alice'), (2, 'Bob')")
    
    schema = introspect_schema()
    
    assert "users" in schema
    assert "columns" in schema["users"]
    assert "sample_rows" in schema["users"]
    
    # Check schema column details
    cols = schema["users"]["columns"]
    assert len(cols) == 2
    assert cols[0] == {"name": "id", "type": "INTEGER"}
    assert cols[1] == {"name": "name", "type": "VARCHAR"}
    
    # Check sample rows
    rows = schema["users"]["sample_rows"]
    assert len(rows) == 2
    assert rows[0] == {"id": 1, "name": "Alice"}
    assert rows[1] == {"id": 2, "name": "Bob"}
