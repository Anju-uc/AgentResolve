"""Evaluation package for AgentResolve."""

from evaluation.metrics import (
    compute_metrics,
    format_confusion_matrix,
)


def run_evaluation(*args, **kwargs):
    """
    Lazy wrapper around evaluation.evaluate.run_evaluation.

    This prevents evaluation.evaluate from being imported before
    Python executes it with `python -m evaluation.evaluate`.
    """
    from evaluation.evaluate import run_evaluation as _run_evaluation

    return _run_evaluation(*args, **kwargs)


__all__ = [
    "compute_metrics",
    "format_confusion_matrix",
    "run_evaluation",
]