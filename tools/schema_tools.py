from database.connection import get_duckdb_connection
from core.exceptions import SchemaIntrospectionError
from core.logger import get_logger

logger = get_logger(__name__)

def introspect_schema() -> dict:
    """
    Introspects the DuckDB database to extract information about all tables and views:
    names, column names, column types, and sample rows.
    Returns a dictionary mapping table name to column information and sample rows.
    Raises SchemaIntrospectionError if introspection fails.
    """
    try:
        conn = get_duckdb_connection()
        schema = {}
        
        # 1. Get all tables and views
        tables_res = conn.execute("SHOW TABLES").fetchall()
        tables = [row[0] for row in tables_res]
        
        for table in tables:
            # 2. Get column names and types
            columns_res = conn.execute(f"PRAGMA table_info('{table}')").fetchall()
            # PRAGMA returns columns: (cid, name, type, notnull, dflt_value, pk)
            columns = [{"name": row[1], "type": row[2]} for row in columns_res]
            
            # 3. Fetch up to 3 sample rows to provide context for the LLM
            try:
                sample_df = conn.execute(f"SELECT * FROM {table} LIMIT 3").df()
                sample_rows = sample_df.to_dict(orient="records")
            except Exception as sample_err:
                logger.warning(f"Could not fetch sample rows for table '{table}': {sample_err}")
                sample_rows = []
                
            schema[table] = {
                "columns": columns,
                "sample_rows": sample_rows
            }
            
        return schema
        
    except Exception as e:
        logger.error(f"Schema introspection failed: {e}")
        raise SchemaIntrospectionError(f"Failed to introspect DuckDB schema: {e}") from e
