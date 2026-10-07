from agno.db.postgres import PostgresDb
from core.config import settings

def get_supabase_db() -> PostgresDb:
    """
    Returns an instance of PostgresDb configured with the Supabase connection string.
    This acts as the agent db backend to persist conversation history.
    """
    return PostgresDb(
        db_url=settings.supabase_connection_string,
        session_table="agent_sessions",
        memory_table="agent_memories"
    )
