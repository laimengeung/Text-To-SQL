# visualization/code_gen.py
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from core.exceptions import VisualizationError
from core.logger import get_logger

logger = get_logger(__name__)

def safe_exec_plotly(code: str, df: pd.DataFrame) -> go.Figure:
    """
    Executes generated Plotly code inside a sandbox with restricted builtins.
    Expects the code to define a 'fig' variable containing the Plotly Figure.
    """
    # Define restricted, safe builtins
    safe_builtins = {
        "abs": abs,
        "len": len,
        "range": range,
        "list": list,
        "dict": dict,
        "set": set,
        "str": str,
        "int": int,
        "float": float,
        "round": round,
        "sum": sum,
        "min": min,
        "max": max,
        "enumerate": enumerate,
        "zip": zip,
        "bool": bool,
    }
    
    # Execution context
    exec_globals = {
        "__builtins__": safe_builtins,
        "pd": pd,
        "px": px,
        "go": go,
        "df": df,
    }
    
    exec_locals = {}
    
    try:
        logger.info("Executing Plotly code generation in sandbox...")
        exec(code, exec_globals, exec_locals)
        
        # Verify that 'fig' exists in locals/globals and is a Figure
        fig = exec_locals.get("fig") or exec_globals.get("fig")
        if fig is None:
            raise VisualizationError("The generated Python code did not define a 'fig' variable.")
            
        if not isinstance(fig, go.Figure):
            raise VisualizationError(f"The 'fig' variable must be a Plotly Figure, got: {type(fig)}")
            
        return fig
    except Exception as e:
        logger.error(f"Error running sandboxed Python code: {e}")
        raise VisualizationError(f"Failed to execute visualization code: {e}") from e
