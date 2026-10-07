# visualization/structured.py
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from core.exceptions import VisualizationError
from core.logger import get_logger

logger = get_logger(__name__)

def generate_plotly_chart_structured(
    chart_type: str,
    x_col: str,
    y_col: str,
    title: str,
    data: list[dict]
) -> go.Figure:
    """
    Deterministically generates a Plotly express chart of a given type.
    Supported chart types: bar, line, scatter, pie.
    """
    if not data:
        raise VisualizationError("Cannot generate chart: data is empty.")
        
    df = pd.DataFrame(data)
    
    # Verify columns exist
    if x_col not in df.columns:
        raise VisualizationError(f"X column '{x_col}' not found in data. Available columns: {list(df.columns)}")
    if y_col not in df.columns:
        raise VisualizationError(f"Y column '{y_col}' not found in data. Available columns: {list(df.columns)}")
        
    chart_type_clean = chart_type.lower().strip()
    
    try:
        if chart_type_clean == "bar":
            fig = px.bar(df, x=x_col, y=y_col, title=title)
        elif chart_type_clean == "line":
            fig = px.line(df, x=x_col, y=y_col, title=title)
        elif chart_type_clean == "scatter":
            fig = px.scatter(df, x=x_col, y=y_col, title=title)
        elif chart_type_clean == "pie":
            fig = px.pie(df, names=x_col, values=y_col, title=title)
        else:
            logger.warning(f"Unsupported chart type '{chart_type}'. Defaulting to bar chart.")
            fig = px.bar(df, x=x_col, y=y_col, title=title)
            
        # Customize styling for rich dark aesthetics
        fig.update_layout(
            template="plotly_dark",
            title_font=dict(size=18, family="Arial"),
            hovermode="closest",
            margin=dict(l=40, r=40, t=50, b=40)
        )
        return fig
    except Exception as e:
        logger.error(f"Error creating structured chart: {e}")
        raise VisualizationError(f"Failed to generate structured Plotly chart: {e}") from e
