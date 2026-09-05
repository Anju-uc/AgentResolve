"""
Evidence Scoring & Attribution Normalization module for AgentResolve.

Centralized evidence weights configuration and score normalization routines.

SCORING SPECIFICATION (per rules.md section 13 & 14):
- Scores are deterministic heuristic points, NOT probabilities.
- Point values reflect evidence factors triggered by fired rules.
- Total attribution normalized to sum to 100 points across fired categories.
- Primary fault = highest-scoring category.
- Contributing factors = remaining fired categories sorted descending.
"""

from typing import List, Dict, Tuple, Optional

from app.models.result import (
    RuleResult,
    FaultCategory,
    FaultAttribution,
)


# Centralized Evidence Factor Point Table (hand-selected heuristics)
EVIDENCE_WEIGHTS: Dict[str, int] = {
    "explicit_constraint": 30,
    "agent_access": 20,
    "agent_violation": 30,
    "validation_skipped": 20,
    "merchant_inconsistency": 40,
    "post_purchase_change": 40,
    "missing_constraint": 50,
}


def calculate_rule_raw_points(rule_result: RuleResult) -> int:
    """
    Calculates the raw points for a fired rule based on its
    triggered evidence factor keys.

    Args:
        rule_result: Executed RuleResult.

    Returns:
        Integer raw point sum.
    """
    if not rule_result.fired:
        return 0

    points = 0

    for factor_key in rule_result.evidence_factors:
        points += EVIDENCE_WEIGHTS.get(factor_key, 10)

    # Ensure minimum points if fired without explicit factors
    if points == 0 and rule_result.fired:
        points = rule_result.raw_points or 30

    return points


def calculate_attribution_scores(
    all_rule_results: List[RuleResult]
) -> Tuple[Optional[FaultAttribution], List[FaultAttribution]]:
    """
    Computes normalized attribution scores across all fired fault categories.

    Formula:
    raw_category_points = sum(points for category factors)
    total_points = sum(raw_category_points across all fired categories)
    attribution_score = round(
        (raw_category_points / total_points) * 100
    )

    Args:
        all_rule_results: List of RuleResults from all 5 fault checks.

    Returns:
        Tuple (primary_fault, contributing_factors).

        If no rules fired, returns:
        NO_FAULT_DETECTED with score 100 and [].
    """

    fired_rules = [r for r in all_rule_results if r.fired]

    if not fired_rules:
        # NO_FAULT_DETECTED
        primary = FaultAttribution(
            category=FaultCategory.NO_FAULT_DETECTED,
            score=100,
            raw_points=0,
        )

        return primary, []

    # Calculate raw points for each fired rule
    category_raw_points: Dict[FaultCategory, int] = {}

    for r in fired_rules:
        pts = calculate_rule_raw_points(r)
        category_raw_points[r.category] = pts

    total_points = sum(category_raw_points.values())

    if total_points == 0:
        total_points = 1  # Guard against division by zero

    # Compute normalized scores
    attributions: List[FaultAttribution] = []

    for cat, pts in category_raw_points.items():
        # Normalized score percentage (0 - 100)
        norm_score = int(round((pts / total_points) * 100))

        attributions.append(
            FaultAttribution(
                category=cat,
                score=norm_score,
                raw_points=pts,
            )
        )

    # Sort attributions descending by score
    attributions.sort(
        key=lambda x: (x.score, x.raw_points),
        reverse=True
    )

    # Adjust rounding artifacts to ensure exact sum of 100
    if len(attributions) > 1:
        current_sum = sum(a.score for a in attributions)
        diff = 100 - current_sum

        if diff != 0:
            # Adjust primary (top) attribution
            attributions[0] = FaultAttribution(
                category=attributions[0].category,
                score=attributions[0].score + diff,
                raw_points=attributions[0].raw_points,
            )

    primary_fault = attributions[0]

    contributing_factors = (
        attributions[1:]
        if len(attributions) > 1
        else []
    )

    return primary_fault, contributing_factors