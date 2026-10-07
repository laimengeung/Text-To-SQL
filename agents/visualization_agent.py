# agents/visualization_agent.py
from agno.agent import Agent
from agno.models.google import Gemini
from tools.plotly_tools import generate_plotly_chart
from core.config import settings

DESCRIPTION = "An agent that generates interactive Plotly visualizations from query results, supporting structured and code-gen modes."

BASE_INSTRUCTIONS = [
    "You are a Data Visualization Expert specializing in Plotly.",
    "Your responsibility is to create interactive, beautiful, dark-themed charts using the `generate_plotly_chart` tool.",
    "Analyze the query results (data) and the user's visualization request to identify the appropriate x and y fields."
]

def get_visualization_agent() -> Agent:
    """
    Returns the configured Visualization Agent.
    Dynamically appends instructions based on the active visualization mode.
    """
    mode = settings.visualization_mode.lower().strip()
    instructions = list(BASE_INSTRUCTIONS)
    
    if mode == "code_gen":
        instructions.extend([
            "CRITICAL: You are running in 'code_gen' mode.",
            "You MUST write Python code to build the visualization and pass it in the `code` argument of the `generate_plotly_chart` tool.",
            "The execution environment has pre-loaded variables: `df` (Pandas DataFrame of the data), `pd` (Pandas), `px` (Plotly Express), and `go` (Plotly Graph Objects).",
            "Your python code must define a variable named `fig` containing the final Plotly Figure.",
            "Ensure the code is safe, clean, and does not contain file-writing or imports.",
            "Example code shape: \n"
            "fig = px.bar(df, x='region', y='revenue', title='Revenue by Region', template='plotly_dark')"
        ])
    else:
        instructions.extend([
            "CRITICAL: You are running in 'structured' mode.",
            "You MUST call `generate_plotly_chart` with: `chart_type`, `x_col`, `y_col`, and `title`.",
            "Identify the correct column names from the data keys for the x and y axes.",
            "Supported chart types: 'bar', 'line', 'scatter', 'pie'."
        ])
        
    return Agent(
        name="Visualization Agent",
        description=DESCRIPTION,
        model=Gemini(id=settings.gemini_default_model),
        tools=[generate_plotly_chart],
        instructions=instructions,
        debug_mode=True,
        markdown=True
    )
