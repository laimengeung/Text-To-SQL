# tools/plotly_tools.py
import pandas as pd
from core.config import settings
from core.exceptions import VisualizationError
from core.logger import get_logger
from visualization.structured import generate_plotly_chart_structured
from visualization.code_gen import safe_exec_plotly


logger = get_logger(__name__)

_latest_fig = None  # module-level cache

def get_latest_fig():
    """Called by orchestrator after visualization agent runs."""
    return _latest_fig

def generate_plotly_chart(
    data: list[dict],
    chart_type: str = "bar",
    x_col: str = None,
    y_col: str = None,
    title: str = "Chart",
    code: str = None
) -> str:
    """
    Generates a Plotly chart from data and saves it to 'output.html'.
    Routes to structured or code_gen mode based on configuration.
    Returns the path to the generated HTML file.
    """
    global _latest_fig
    
    if not data:
        raise VisualizationError("Data is empty. Cannot generate visualization.")
        
    mode = settings.visualization_mode.lower().strip()
    logger.info(f"Generating chart using mode: {mode}")
    
    try:
        if mode == "code_gen":
            if not code:
                raise VisualizationError("Code parameter is required for code_gen mode.")
            df = pd.DataFrame(data)
            fig = safe_exec_plotly(code, df)
        else:
            # Default to structured mode
            if not x_col or not y_col:
                raise VisualizationError("x_col and y_col are required for structured visualization mode.")
            fig = generate_plotly_chart_structured(chart_type, x_col, y_col, title, data)
            
        _latest_fig = fig   # store for orchestrator to retrieve

        output_path = "output.html"
        fig.write_html(output_path, include_plotlyjs="cdn")
        logger.info(f"Chart successfully saved to {output_path}")
        return output_path
    except Exception as e:
        logger.error(f"Failed to generate Plotly chart: {e}")
        raise VisualizationError(f"Plotly generation tool error: {e}") from e
