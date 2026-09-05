"""
Unit Tests for Evidence Scoring & Attribution Normalization (Phase 7).
"""

from app.models.result import RuleResult, FaultCategory
from app.engine.scoring import calculate_attribution_scores


def test_scoring_single_fault_normalization():
    """Test single fired rule normalizes to 100/100 score."""
    rule_res = RuleResult(
        category=FaultCategory.AGENT_MISJUDGMENT,
        fired=True,
        evidence=[],
        evidence_factors=["explicit_constraint", "agent_access", "agent_violation", "validation_skipped"],
        raw_points=100
    )
    primary, contribs = calculate_attribution_scores([rule_res])
    
    assert primary is not None
    assert primary.category == FaultCategory.AGENT_MISJUDGMENT
    assert primary.score == 100
    assert contribs == []


def test_scoring_multi_fault_normalization():
    """Test multi-fault normalization sums to exactly 100."""
    rule_1 = RuleResult(
        category=FaultCategory.AGENT_MISJUDGMENT,
        fired=True,
        evidence=[],
        evidence_factors=["explicit_constraint", "agent_access", "agent_violation", "validation_skipped"],
        raw_points=100
    )
    rule_2 = RuleResult(
        category=FaultCategory.MERCHANT_DATA_ERROR,
        fired=True,
        evidence=[],
        evidence_factors=["merchant_inconsistency"],
        raw_points=40
    )
    
    primary, contribs = calculate_attribution_scores([rule_1, rule_2])
    
    assert primary.category == FaultCategory.AGENT_MISJUDGMENT
    assert len(contribs) == 1
    assert contribs[0].category == FaultCategory.MERCHANT_DATA_ERROR
    
    total_score = primary.score + sum(c.score for c in contribs)
    assert total_score == 100
    assert primary.score > contribs[0].score


def test_scoring_no_rules_fired_returns_no_fault():
    """Test when no rules fire, returns NO_FAULT_DETECTED with score 100."""
    primary, contribs = calculate_attribution_scores([])
    assert primary.category == FaultCategory.NO_FAULT_DETECTED
    assert primary.score == 100
    assert contribs == []
