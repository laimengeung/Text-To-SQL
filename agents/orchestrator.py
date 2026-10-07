# agents/orchestrator.py
from agno.agent import Agent
from agno.models.google import Gemini
from core.config import settings
from core.exceptions import (
    TextToSQLException,
    SchemaIntrospectionError,
    SQLGenerationError,
    VisualizationError,
    DatabaseConnectionError
)
from core.logger import get_logger
from memory.supabase_memory import get_supabase_db

# Import other agents (matching local filenames)
from agents.schema_agents import get_schema_agent
from agents.sql_writer import get_sql_writer_agent
from agents.validator_agent import validate_and_execute_query
from agents.response_agent import get_response_agent
from agents.visualization_agent import get_visualization_agent


logger = get_logger(__name__)

DESCRIPTION = "The central Orchestrator that coordinates the Text-to-SQL pipeline and manages conversation memory."

INSTRUCTIONS = [
    "You are the central Orchestrator of a Text-to-SQL agentic AI system.",
    "Your responsibility is to manage conversation memory and coordinate sub-agents.",
    "This agent is primarily used as a session container to load/save memory from Supabase."
]

def get_orchestrator_agent(session_id: str = "cli_session", user_id: str = "cli_user") -> Agent:
    """
    Returns the Orchestrator Agent instance, wired with Supabase Postgres db.
    """
    agent_db = get_supabase_db()
    return Agent(
        name="Orchestrator Agent",
        description=DESCRIPTION,
        model=Gemini(id=settings.gemini_default_model),
        instructions=INSTRUCTIONS,
        db=agent_db,
        session_id=session_id,
        user_id=user_id,
        add_history_to_context=True,
        # debug_mode=settings.debug_mode,
        markdown=True
    )

def run_orchestrator_pipeline(
    question: str,
    session_id: str = "cli_session",
    user_id: str = "cli_user",
    progress_callback: callable = None,
    schema_cache: str = None
) -> str:
    """
    Orchestrates the entire execution pipeline deterministically:
    1. Loads session history from the Orchestrator's Supabase memory
    2. Introspects Database Schema (via Schema Agent)
    3. Generates SQL (via SQL Writer Agent, incorporating conversation history)
    4. Validates and executes (via Validator Agent retry loop)
    5. Formats natural language response (via Response Agent)
    6. Generates Plotly chart conditionally (via Visualization Agent)
    7. Persists new messages to Supabase memory
    """
    # logger.info(f"Starting Text-to-SQL pipeline for question: '{question}' (Session: {session_id})")
    
    # 0. Load the Orchestrator Agent to retrieve chat history
    orchestrator = get_orchestrator_agent(session_id=session_id, user_id=user_id)
    
    # Extract conversation history as context for the SQL Writer
    history_context = ""
    existing_session = orchestrator.get_session()
    if existing_session is not None:
        past_messages = existing_session.get_messages()
        if past_messages:
            history_context = "\n".join([
                f"{msg.role}: {msg.content}"
                for msg in past_messages
                if msg.content and msg.role in ("user", "assistant")
            ])

    # --- Intent Classification ---
    logger.info("Classifying user intent...")
    intent_agent = Agent(
        model=Gemini(id=settings.gemini_default_model),
        instructions=[
            "Classify the user's message into exactly one of three categories:",
            "- 'sql_query': the user wants to query or explore data and see results",
            "- 'sql_only': the user wants to see the SQL query itself, not the results",
            "- 'general': the user is chatting or asking about concepts unrelated to querying data",
            "Additionally, if the user's message contains any request to visualize, chart, plot, "
            "graph, or display data visually — append '_viz' to the category.",
            "Examples: 'show me a bar chart of revenue' → 'sql_query_viz'",
            "         'what is the total revenue?' → 'sql_query'",
            "         'give me the SQL for revenue by region' → 'sql_only'",
            "Reply with only the category string. No punctuation, no explanation.",
        ],
        debug_mode=False,  # keep this silent regardless of global debug_mode
    )
    intent_response = intent_agent.run(question)
    intent = intent_response.content.strip().lower()
    logger.info(f"Intent classified as: '{intent}'")

    # Check if visualization is requested
    is_viz_requested = intent.endswith("_viz")
    intent_base = intent.removesuffix("_viz")  # 'sql_query', 'sql_only', 'general'    

    try:
        # Step 1: Introspect Database Schema
            # Check for Schema Cache!
        if schema_cache:
            if progress_callback:
                progress_callback("🔍 Using cached schema")
            logger.info("Step 1: Using cached schema — skipping Schema Agent.")
            schema_context = schema_cache
        else:
            logger.info("Step 1: Running Schema Agent...")
            if progress_callback:
                progress_callback("🔍 Schema Agent — introspecting database...")
            schema_agent = get_schema_agent()
            schema_response = schema_agent.run("Introspect the database and return the schema.")
            schema_context = schema_response.content

        
        if intent == "general":
            logger.info("Non-SQL intent detected — answering directly without pipeline.")
            general_agent = Agent(
                model=Gemini(id=settings.gemini_default_model),
                instructions=[
                    "You are a helpful assistant embedded in a Text-to-SQL tool.",
                    "Answer the user's general question clearly and concisely.",
                    "If they seem to want to query data, remind them they can ask questions about their database.",
                ],
                debug_mode=settings.debug_mode,
                markdown=True,
            )
            general_prompt = (
                f"User Question: {question}\n"
                f"Database Schema:\n{schema_context}\n\n"
            )
            general_response = general_agent.run(general_prompt)
            return general_response.content, schema_context
        
        if intent == "sql_only":
            is_sql_only_requested = True
            
        else:
            is_sql_only_requested = False

        # Step 2: Generate Initial SQL (incorporating history context)
        logger.info("Step 2: Generating initial SQL...")
        if progress_callback:
            progress_callback("✍️  SQL Writer — generating query…")
        sql_writer = get_sql_writer_agent()
        sql_prompt = ""
        if history_context:
            sql_prompt += f"Conversation History:\n{history_context}\n\n"
        sql_prompt += (
            f"User Question: {question}\n"
            f"Database Schema:\n{schema_context}\n\n"
            f"Write the matching SQL query."
        )
        sql_response = sql_writer.run(sql_prompt)
        initial_sql = sql_response.content.strip()
        
        # Step 3: Validate & Execute Query (owns the retry loop)
        logger.info("Step 3: Validating and executing SQL...")
        if progress_callback:
            progress_callback("✅ Validator — executing SQL…")
        results, validated_sql = validate_and_execute_query(
            question=question,
            initial_sql=initial_sql,
            schema_context=schema_context,
            sql_writer_agent=sql_writer,
            return_sql_only=is_sql_only_requested,
            include_sql=True
        )

        # Step 4: Generate Natural Language Response
        logger.info("Step 4: Formatting response...")
        if progress_callback:
            progress_callback("💬 Response Agent — formatting answer…")
        response_agent = get_response_agent()
        response_prompt = (
            f"Original Question: {question}\n"
            f"Query Results:\n{results}\n\n"
            f"Synthesize a clear natural language answer."
            f"CRITICAL: DO NOT write or reference any SQL query."
        )
        final_answer_response = response_agent.run(response_prompt)
        final_answer_response_content = final_answer_response.content
        
        final_answer = (
            f"**SQL Query:**\n```sql\n{validated_sql}\n```"
            f"\n{final_answer_response_content}\n\n"
        )

        # Step 5: Conditional Visualization
        viz_info = ""
        if is_viz_requested:
            logger.info("Step 5: Invoking Visualization Agent...")
            if progress_callback:
                progress_callback("📊 Visualization Agent — building chart…")
            viz_agent = get_visualization_agent()
            viz_prompt = (
                f"User requested visualization for: '{question}'\n"
                f"Data to visualize:\n{results}\n\n"
                f"Generate the chart using the available tool."
            )
            viz_response = viz_agent.run(viz_prompt)

            from tools.plotly_tools import get_latest_fig
            fig = get_latest_fig()
            if fig:
                import streamlit as st
                # Only store if running in Streamlit context
                try:
                    st.session_state["latest_fig"] = fig
                except Exception:
                    pass  # CLI context — no Streamlit session state, ignore

            # The tool saves it to output.html.
            viz_info = "\n\n📊 *Chart saved to output.html*"

        # Step 6: Persist new conversation turn to Supabase agent_db
        orchestrator.run(f"User asked: {question}\n\nAnswer: {final_answer}")
            
        return f"{final_answer}{viz_info}", schema_context  # Also returns schema_context to use for cache
        
    except SchemaIntrospectionError as e:
        logger.error(f"Pipeline error at Schema Introspection: {e}")
        return "Could not read your database schema. Is your file formatted correctly?", schema_context
        
    except SQLGenerationError as e:
        logger.error(f"Pipeline error at SQL Generation: {e}")
        return "Could not generate valid SQL after 3 attempts. Try rephrasing.", schema_context
        
    except VisualizationError as e:
        logger.error(f"Pipeline error at Visualization: {e}"), schema_context
        # Return the answer but notify that viz failed
        return f"{final_answer}\n\n⚠️ *Could not generate the chart. Try specifying the chart type explicitly.*", schema_context
        
    except DatabaseConnectionError as e:
        logger.error(f"Pipeline error at Database Connection: {e}")
        return "Could not connect to the database. Check your DuckDB file path.", schema_context
        
    except Exception as e:
        logger.critical(f"Unhandled pipeline error: {e}", exc_info=True)
        return f"An unexpected error occurred: {str(e)}", schema_context
