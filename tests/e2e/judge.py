# tests/e2e/judge.py
from agno.agent import Agent
from agno.models.google import Gemini
from core.config import settings

def llm_judge(question: str, result: str, criteria: str) -> bool:
    """
    Returns True if the LLM judge considers the result passing.
    """
    judge = Agent(
        model=Gemini(id=settings.gemini_default_model),
        instructions=[
            "You are an objective evaluator for a Text-to-SQL system.",
            "You will be given a user question, a result, and evaluation criteria.",
            "Reply with only 'pass' or 'fail' followed by one sentence explanation.",
            "Be strict — partial answers are a fail.",
        ],
        debug_mode=False,
    )
    verdict = judge.run(
        f"Question: {question}\n"
        f"Result: {result}\n"
        f"Criteria: {criteria}"
    ).content.strip().lower()
    
    return verdict.startswith("pass")