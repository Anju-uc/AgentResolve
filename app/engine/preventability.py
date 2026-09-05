"""
Preventability Evaluation module for AgentResolve.

Determines whether a disputed transaction issue was preventable prior to purchase.

PREVENTABILITY RATINGS (per rules.md section 15):
- HIGH: Issue was knowable before purchase and an available validation/action could have caught it.
        (e.g., AGENT_MISJUDGMENT, MERCHANT_DATA_ERROR at checkout)
- LOW : Issue became knowable only after purchase.
        (e.g., EXTERNAL_CHANGE post-purchase delivery delay)
- N/A : Used for NO_FAULT_DETECTED, USER_POST_PURCHASE_CHANGE, USER_AMBIGUITY, or INSUFFICIENT_EVIDENCE.
"""

from typing import List, Optional
from app.models.result import (
    PreventabilityRating,
    FaultAttribution,
    FaultCategory,
    RuleResult,
)


def determine_preventability(
    primary_fault: Optional[FaultAttribution],
    all_fired_rules: List[RuleResult],
    is_insufficient_evidence: bool = False
) -> PreventabilityRating:
    """
    Evaluates preventability rating based on primary fault category and fired rule evidence.

    Args:
        primary_fault: Primary FaultAttribution (if any).
        all_fired_rules: List of all fired RuleResult objects.
        is_insufficient_evidence: True if analysis status is INSUFFICIENT_EVIDENCE.

    Returns:
        PreventabilityRating: HIGH, LOW, or N/A.
    """
    if is_insufficient_evidence or primary_fault is None:
        return PreventabilityRating.NOT_APPLICABLE

    primary_cat = primary_fault.category

    # Check primary fault category
    if primary_cat == FaultCategory.AGENT_MISJUDGMENT:
        return PreventabilityRating.HIGH

    elif primary_cat == FaultCategory.MERCHANT_DATA_ERROR:
        # Merchant error knowable if price or listing spec differed at selection/checkout
        return PreventabilityRating.HIGH

    elif primary_cat == FaultCategory.EXTERNAL_CHANGE:
        # External changes occur post-purchase
        return PreventabilityRating.LOW

    elif primary_cat in [
        FaultCategory.USER_AMBIGUITY,
        FaultCategory.USER_POST_PURCHASE_CHANGE,
        FaultCategory.NO_FAULT_DETECTED,
    ]:
        return PreventabilityRating.NOT_APPLICABLE

    return PreventabilityRating.NOT_APPLICABLE
