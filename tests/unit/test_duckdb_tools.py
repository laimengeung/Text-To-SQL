# tests/unit/test_duckdb_tools.py
import pytest
import os
import tempfile
from core.exceptions import SQLGenerationError
from core.config import settings
from database.connection import get_duckdb_connection, close_duckdb_connection
from database.registry import register_csv, list_registered_tables
from tools.duckdb_tools import execute_query

@pytest.fixture(autouse=True)
def use_in_memory_db(monkeypatch):
    """
    Forces the DuckDB file path to be in-memory for unit tests.
    Closes the connection after each test run.
    """
    monkeypatch.setattr(settings, "duckdb_file_path", ":memory:")
    yield
    close_duckdb_connection()

def test_execute_query_success():
    """Verify executing a valid SQL query returns correct results."""
    conn = get_duckdb_connection()
    conn.execute("CREATE TABLE test_table (id INTEGER, name VARCHAR)")
    conn.execute("INSERT INTO test_table VALUES (1, 'Alice'), (2, 'Bob')")
    
    result = execute_query("SELECT * FROM test_table ORDER BY id")
    assert isinstance(result, list)
    assert len(result) == 2
    assert result[0] == {"id": 1, "name": "Alice"}
    assert result[1] == {"id": 2, "name": "Bob"}

def test_execute_query_failure():
    """Verify executing an invalid SQL query raises SQLGenerationError."""
    with pytest.raises(SQLGenerationError) as exc_info:
        execute_query("SELECT * FROM non_existent_table")
    assert "Database error executing SQL" in str(exc_info.value)

def test_execute_query_no_results():
    """Verify executing a DDL statement (e.g. CREATE TABLE) returns an empty list."""
    result = execute_query("CREATE TABLE ddl_table (id INTEGER)")
    assert result == []

def test_register_csv_success():
    """Verify registering a CSV creates a queryable view in DuckDB."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
        f.write("id,value\n1,100\n2,200\n")
        csv_path = f.name
        
    try:
        register_csv(csv_path, "temp_csv_table")
        tables = list_registered_tables()
        assert "temp_csv_table" in tables
        
        result = execute_query("SELECT * FROM temp_csv_table ORDER BY id")
        assert len(result) == 2
        assert result[0] == {"id": 1, "value": 100}
    finally:
        if os.path.exists(csv_path):
            os.remove(csv_path)

def test_register_csv_not_found():
    """Verify registering a non-existent CSV raises FileNotFoundError."""
    with pytest.raises(FileNotFoundError):
        register_csv("non_existent_file.csv", "error_table")
