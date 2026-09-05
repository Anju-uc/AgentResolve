"""
Unit Tests for Counterfactual Replay Simulation (Phase 9).
"""

from app.models.result import FaultAttribution, FaultCategory
from app.engine.counterfactual import simulate_counterfactual
from evaluation.evaluate import load_dataset


def test_counterfactual_replay_agent_misjudgment():
    """Test counterfactual replay for agent misjudgment (TXN_002)."""
    cases = {t.transaction_id: t for t in load_dataset("data/development_cases.json")}
    txn = cases["TXN_002"]
    
    primary = FaultAttribution(category=FaultCategory.AGENT_MISJUDGMENT, score=100)
    cf = simulate_counterfactual(txn, primary)
    
    assert cf.applicable is True
    assert cf.result == "PURCHASE_WOULD_HAVE_BEEN_BLOCKED"
    assert "would have been blocked" in cf.narrative.lower()


def test_counterfactual_replay_merchant_data_error():
    """Test counterfactual replay for merchant data error (TXN_003)."""
    cases = {t.transaction_id: t for t in load_dataset("data/development_cases.json")}
    txn = cases["TXN_003"]
    
    primary = FaultAttribution(category=FaultCategory.MERCHANT_DATA_ERROR, score=100)
    cf = simulate_counterfactual(txn, primary)
    
    assert cf.applicable is True
    assert "PRICE_DISCREPANCY" in cf.result


def test_counterfactual_insufficient_evidence_skipped():
    """Test counterfactual replay is skipped when evidence is incomplete."""
    cases = {t.transaction_id: t for t in load_dataset("data/development_cases.json")}
    txn = cases["TXN_012"]
    
    cf = simulate_counterfactual(txn, None, is_insufficient_evidence=True)
    assert cf.applicable is False
    assert "INSUFFICIENT_EVIDENCE" in cf.result
