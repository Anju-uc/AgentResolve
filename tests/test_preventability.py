"""
Unit Tests for Preventability Evaluation (Phase 8).
"""

from app.models.result import FaultAttribution, FaultCategory, PreventabilityRating
from app.engine.preventability import determine_preventability


def test_preventability_high_for_agent_misjudgment():
    """Agent misjudgment is knowable before purchase -> HIGH preventability."""
    primary = FaultAttribution(category=FaultCategory.AGENT_MISJUDGMENT, score=100)
    rating = determine_preventability(primary, [])
    assert rating == PreventabilityRating.HIGH


def test_preventability_high_for_merchant_data_error():
    """Merchant data error at checkout -> HIGH preventability."""
    primary = FaultAttribution(category=FaultCategory.MERCHANT_DATA_ERROR, score=100)
    rating = determine_preventability(primary, [])
    assert rating == PreventabilityRating.HIGH


def test_preventability_low_for_external_change():
    """Post-purchase external change -> LOW preventability."""
    primary = FaultAttribution(category=FaultCategory.EXTERNAL_CHANGE, score=100)
    rating = determine_preventability(primary, [])
    assert rating == PreventabilityRating.LOW


def test_preventability_na_for_user_ambiguity_and_no_fault():
    """User ambiguity and no fault -> N/A preventability."""
    primary_amb = FaultAttribution(category=FaultCategory.USER_AMBIGUITY, score=100)
    assert determine_preventability(primary_amb, []) == PreventabilityRating.NOT_APPLICABLE
    
    primary_nf = FaultAttribution(category=FaultCategory.NO_FAULT_DETECTED, score=100)
    assert determine_preventability(primary_nf, []) == PreventabilityRating.NOT_APPLICABLE
