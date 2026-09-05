"""
LLM Module Package for AgentResolve.
"""

from app.llm.explainer import generate_explanation, format_deterministic_fallback_explanation

__all__ = [
    "generate_explanation",
    "format_deterministic_fallback_explanation",
]
