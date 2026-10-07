import os
import duckdb

from core.config import settings
from core.exceptions import DatabaseConnectionError
from core.logger import get_logger

logger = get_logger(__name__)

# duckdb.DuckDBPyConnection is the class we get from duckdb.connect()
_connection: duckdb.DuckDBPyConnection | None = None

def get_duckdb_connection() -> duckdb.DuckDBPyConnection:
    """
    Returns a shared, cached DuckDB connection.
    Creates parent directories if using a file path.
    Raises DatabaseConnectionError on failure.
    """
    global _connection
    if _connection is None:
        try:
            db_path = settings.duckdb_file_path
            
            # Ensure the directory exists if it's a file database
            if db_path != ":memory:":
                db_dir = os.path.dirname(db_path)
                if db_dir:
                    os.makedirs(db_dir, exist_ok=True)
            
            logger.info(f"Establishing DuckDB connection to: {db_path}")
            _connection = duckdb.connect(database=db_path)
        except Exception as e:
            logger.error(f"Failed to open DuckDB connection: {e}")
            raise DatabaseConnectionError(f"Could not connect to DuckDB at '{settings.duckdb_file_path}': {e}") from e
    
    return _connection

def close_duckdb_connection() -> None:
    """Closes the shared DuckDB connection if open."""
    global _connection
    if _connection is not None:
        try:
            logger.info("Closing DuckDB connection.")
            _connection.close()
        except Exception as e:
            logger.warning(f"Error while closing DuckDB connection: {e}")
        finally:
            _connection = None
            