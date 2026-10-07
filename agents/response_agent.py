from agno.agent import Agent
from agno.models.google import Gemini
from core.config import settings

DESCRIPTION = "An agent that formats raw database query results into a natural, user-friendly language response."

# INSTRUCTIONS = [
#     "You are a friendly Database Response Agent.",
#     "Your responsibility is to take raw database query results (represented as a list of dicts) and summarize them in clear, natural language.",
#     "Address the user's original question directly.",
#     "If the query results are empty, explain politely that no data was found matching their query.",
#     "Use clean markdown formatting, such as bold text, bullet lists, or tables, to make the data easy to read.",
#     "Do not invent facts; only report on what is present in the database results."
# ]

INSTRUCTIONS = [
    "You are a specialized Response Agent.",
    "You receive a user question, the executed SQL query, and the raw query results.",
    "Structure your response in this exact order:",
    "1. A 1-2 sentence plain English answer summarising the key insight from the results.",
    # "2. The SQL query wrapped in a ```sql code block.",
    "2. The query results as a Markdown table (max 10 rows). If more than 10 rows, show 10 and note the total count.",
    "If results are empty, say so clearly.",
    # "CRITICAL: NEVER modify or rewrite the SQL — show it exactly as executed.",
    "Never guess or add information not present in the results.",
]


def get_response_agent() -> Agent:
    """
    Returns an instance of the Response Agent
    """
    return Agent(
        name="Response Agent",
        description=DESCRIPTION,
        model=Gemini(id=settings.gemini_default_model),
        instructions=INSTRUCTIONS,
        # debug_mode=settings.debug_mode,
        markdown=True
    )
