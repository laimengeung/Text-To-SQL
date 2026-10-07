from database.connection import get_duckdb_connection
from core.exceptions import SQLGenerationError
from core.logger import get_logger

logger = get_logger(__name__)

# Returns list[dict], which can serialize to JSON, and it self-describing as well
def execute_query(sql: str) -> list[dict]:
    """
    Executes a SQL query against the DuckDB database and returns the result as a list of dicts.
    Handles DDL/DML statements that return no results safely.
    Raises SQLGenerationError if the SQL execution fails.
    """    
    try:
        conn = get_duckdb_connection()
        logger.info(f"Executing query: {sql}")

        relation = conn.execute(sql)
        # Check if the query returned any columns (DDL like CREATE VIEW returns no description)    
        if relation.description is None:
            return []

        df = relation.df()
        return df.to_dict(orient="records")    

    except Exception as e:
        logger.error(f"SQL execution failed for: {sql}. Error: {e}")
        raise SQLGenerationError(f"Database error executing SQL: {e}") from e
