# agents/validator_agent.py
from agno.agent import Agent
from agno.models.google import Gemini
from tools.duckdb_tools import execute_query
from core.config import settings
from core.exceptions import SQLGenerationError
from core.logger import get_logger

logger = get_logger(__name__)

DESCRIPTION = "An agent that executes SQL queries, validates results, and coordinates query corrections on failure."

INSTRUCTIONS = [
    "You are a SQL Validation and Debugging Agent.",
    "Your responsibility is to execute generated SQL queries using the `execute_query` tool.",
    "If execution succeeds, provide the raw results.",
    "If execution fails, capture the database error message to help correct the query."
]

def get_validator_agent() -> Agent:
    """
    Returns the Validator Agent.
    """
    return Agent(
        name="Validator Agent",
        description=DESCRIPTION,
        model=Gemini(id=settings.gemini_default_model),
        tools=[execute_query],
        instructions=INSTRUCTIONS,
        debug_mode=settings.debug_mode,
        markdown=True
    )

def validate_and_execute_query(
    question: str,
    initial_sql: str,
    schema_context: str,
    sql_writer_agent: Agent,
    max_retries: int = settings.max_sql_retries,
    return_sql_only: bool = False,
    include_sql: bool = False,                     
) -> list[dict] | tuple[list[dict], str] | tuple[str, str]:                             
    """
    Executes the generated SQL. If it fails, runs a retry loop:
    1. Captures the DuckDB error message.
    2. Sends the question + failed SQL + error message back to the SQL Writer Agent.
    3. Re-runs the corrected SQL query.
    Repeats up to max_retries. Raises SQLGenerationError on final failure.

    If return_sql_only=True, returns the validated SQL string instead of the result set.
    """
    current_sql = initial_sql
    
    for attempt in range(1, max_retries + 1):
        logger.info(f"SQL Execution Attempt {attempt}/{max_retries}: {current_sql}")
        try:
            results = execute_query(current_sql)
            logger.info("SQL query executed successfully.")
            if return_sql_only:                       
                return current_sql
            if include_sql:
                return results, current_sql  # ← tuple only when requested
            return results                   # ← default: list[dict], nothing breaks
        
        except SQLGenerationError as e:
            error_msg = str(e)
            logger.warning(f"Execution failed on attempt {attempt}: {error_msg}")
            
            if attempt == max_retries:
                logger.error("Reached maximum SQL query execution retries.")
                raise SQLGenerationError(
                    f"Failed to generate a valid SQL query after {max_retries} attempts.\n"
                    f"Last SQL attempted: {current_sql}\n"
                    f"Database Error: {error_msg}"
                ) from e
            
            retry_prompt = (
                f"The previous SQL query you wrote failed to execute.\n"
                f"User Question: {question}\n"
                f"Schema Context: {schema_context}\n"
                f"Failed SQL: {current_sql}\n"
                f"Database Error: {error_msg}\n\n"
                f"Please correct the query and output ONLY the raw, corrected SQL statement. "
                f"Do not include markdown code block syntax."
            )
            
            logger.info("Requesting corrected SQL from SQL Writer Agent...")
            writer_response = sql_writer_agent.run(retry_prompt)
            current_sql = writer_response.content.strip()
            
    raise SQLGenerationError("Failed to validate query (unexpected loop exit).")
