from typing import Text
class TextToSQLException(Exception):
    """Base exception class for all errors in the Text-to-SQL system."""
    pass

class SchemaIntrospectionError(TextToSQLException):
    """Raised when the Schema Agent fails to read or introspect the database schema."""
    pass

class SQLGenerationError(TextToSQLException):
    """Raised when the system fails to generate or correct the SQL query after max retries."""
    pass

class VisualizationError(TextToSQLException):
    """Raised when the Visualization Agent fails to generate or render the Plotly chart."""
    pass

class DatabaseConnectionError(TextToSQLException):
    """Raised when connection to DuckDB or Supabase Postgres fails."""
    pass    