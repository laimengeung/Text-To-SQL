import os
from database.connection import get_duckdb_connection

from core.exceptions import DatabaseConnectionError
from core.logger import get_logger

logger = get_logger(__name__)

# Register CSV & Parquet are the same, except for FROM read_csv_auto/read_parquet
def register_csv(file_path: str, table_name: str) -> None:
    """
    Registers a local CSV file as a queryable View in DuckDB.
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"CSV file not found at: {file_path}")
        
    try:
        conn = get_duckdb_connection()
        # Normalize backslashes to forward slashes for DuckDB SQL compatibility on Windows
        normalized_path = file_path.replace("\\", "/")
        
        query = f"CREATE OR REPLACE TABLE {table_name} AS SELECT * FROM read_csv_auto('{normalized_path}')"
        logger.info(f"Registering CSV: {table_name} -> {normalized_path}")
        conn.execute(query)
    except Exception as e:
        logger.error(f"Failed to register CSV view for '{table_name}': {e}")
        raise DatabaseConnectionError(f"Failed to register CSV view: {e}") from e

def register_parquet(file_path: str, table_name: str) -> None:
    """
    Registers a local Parquet file as a queryable View in DuckDB.
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Parquet file not found at: {file_path}")
        
    try:
        conn = get_duckdb_connection()
        normalized_path = file_path.replace("\\", "/")
        
        query = f"CREATE OR REPLACE TABLE {table_name} AS SELECT * FROM read_parquet('{normalized_path}')"
        logger.info(f"Registering Parquet: {table_name} -> {normalized_path}")
        conn.execute(query)
    except Exception as e:
        logger.error(f"Failed to register Parquet view for '{table_name}': {e}")
        raise DatabaseConnectionError(f"Failed to register Parquet view: {e}") from e

def list_registered_tables() -> list[str]:
    """
    Returns a list of all registered tables and views in DuckDB.
    """
    try:
        conn = get_duckdb_connection()
        result = conn.execute("SHOW TABLES").fetchall()
        # result returns list[tuple]. Ex: [('users',), ('orders',), ('products',)]
        return [row[0] for row in result]
    except Exception as e:
        logger.error(f"Failed to list registered tables: {e}")
        raise DatabaseConnectionError(f"Failed to list tables: {e}") from e
