from agno.agent import Agent
from agno.models.google import Gemini
from tools.schema_tools import introspect_schema
from core.config import settings

DESCRIPTION = "Introspects the DuckDB database schema — tables, columns, types, and sample rows."

INSTRUCTIONS = [
    "You are a specialized Database Schema Agent.",
    "Your sole responsibility is to introspect the schema of the DuckDB database.",
    "You MUST always call the `introspect_schema` tool — never guess table names, columns, or types.",
    "Return the schema as a clean JSON structure showing tables, columns, data types, and row counts.",
    "If the database is empty or no tables are registered, say so clearly.",  # ← edge case
]

def get_schema_agent() -> Agent:
    """
    Returns an instance of the Schema Agent configured with the Gemini model.
    """
    return Agent(
        name="Schema Agent",
        description=DESCRIPTION,
        model=Gemini(id=settings.gemini_default_model),
        tools=[introspect_schema],
        instructions=INSTRUCTIONS,
        # debug_mode=settings.debug_mode,
        markdown=True
    )