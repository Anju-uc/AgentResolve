"""
Forensic Engine Package for AgentResolve.
"""

from app.engine.helpers import (
    constraint_exists,
    agent_had_constraint,
    validation_was_performed,
    constraint_is_satisfied,
    constraint_is_violated,
    merchant_value_changed,
)
from app.engine.rules import (
    check_user_ambiguity,
    check_agent_misjudgment,
    check_merchant_data_error,
    check_external_change,
    check_user_post_purchase_change,
    run_all_rules,
)
from app.engine.scoring import (
    EVIDENCE_WEIGHTS,
    calculate_attribution_scores,
)
from app.engine.preventability import determine_preventability
from app.engine.counterfactual import simulate_counterfactual
from app.engine.analyzer import analyze_transaction

__all__ = [
    "constraint_exists",
    "agent_had_constraint",
    "validation_was_performed",
    "constraint_is_satisfied",
    "constraint_is_violated",
    "merchant_value_changed",
    "check_user_ambiguity",
    "check_agent_misjudgment",
    "check_merchant_data_error",
    "check_external_change",
    "check_user_post_purchase_change",
    "run_all_rules",
    "EVIDENCE_WEIGHTS",
    "calculate_attribution_scores",
    "determine_preventability",
    "simulate_counterfactual",
    "analyze_transaction",
]
