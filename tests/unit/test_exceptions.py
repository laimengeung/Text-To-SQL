# tests/unit/test_exceptions.py
from core.exceptions import (
    TextToSQLException,
    SchemaIntrospectionError,
    SQLGenerationError,
    VisualizationError,
    DatabaseConnectionError
)

def test_exception_inheritance():
    """Verify that all custom exceptions inherit from the base TextToSQLException."""
    assert issubclass(SchemaIntrospectionError, TextToSQLException)
    assert issubclass(SQLGenerationError, TextToSQLException)
    assert issubclass(VisualizationError, TextToSQLException)
    assert issubclass(DatabaseConnectionError, TextToSQLException)

def test_exception_messages():
    """Verify that exception messages are stored correctly."""
    err = SchemaIntrospectionError("Test error message")
    assert str(err) == "Test error message"
