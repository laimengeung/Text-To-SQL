# agents/sql_writer_agent.py
from agno.agent import Agent
from agno.models.google import Gemini
from core.config import settings

DESCRIPTION = "An agent specialized in generating DuckDB-compatible SQL queries from natural language and schema definitions."

INSTRUCTIONS = [
    "You are a Senior SQL Developer specializing in DuckDB SQL dialect.",
    "Your sole task is to generate a syntactically correct DuckDB SQL query matching the user's natural language question and database schema.",
    "CRITICAL: Do NOT wrap your query in markdown formatting (e.g., do not output ```sql ... ```). Output ONLY the raw SQL query as plain text.",
    "Ensure all tables, views, and columns match the provided schema exactly.",
    "If error feedback from a previous run is provided, analyze the error and correct your SQL query accordingly."
]

def get_sql_writer_agent() -> Agent:
    """
    Returns an instance of the SQL Writer Agent.
    """
    return Agent(
        name="SQL Writer Agent",
        description=DESCRIPTION,
        model=Gemini(id=settings.gemini_default_model),
        instructions=INSTRUCTIONS,
        debug_mode=settings.debug_mode,
        markdown=False  # Must be False to prevent markdown wrapper formatting
    )
