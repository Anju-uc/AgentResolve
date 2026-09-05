"""
Unit Tests for LLM Explanation Adapter (Phase 14).

Verifies that the LLM is explanation-only and CANNOT mutate deterministic findings:
- Deterministic score and category remain authoritative
- Graceful fallback when API key is missing or service unavailable
- Verification of non-mutation guarantees
"""

from app.engine.analyzer import analyze_transaction
from app.llm.explainer import generate_explanation
from evaluation.evaluate import load_dataset


def test_llm_deterministic_fallback():
    """Test LLM adapter falls back cleanly without API key."""
    cases = {t.transaction_id: t for t in load_dataset("data/development_cases.json")}
    analysis = analyze_transaction(cases["TXN_002"])
    
    # Store initial deterministic values
    orig_cat = analysis.primary_fault.category
    orig_score = analysis.primary_fault.score
    
    # Run explanation generation using mock / fallback
    res = generate_explanation(analysis, provider="mock")
    
    assert res.explanation != ""
    assert res.explanation_status in ["DETERMINISTIC_FALLBACK", "MOCK"]
    
    # Verify strict non-mutation guarantee
    assert res.primary_fault.category == orig_cat
    assert res.primary_fault.score == orig_score


def test_llm_insufficient_evidence_explanation():
    """Test LLM explanation for INSUFFICIENT_EVIDENCE status."""
    cases = {t.transaction_id: t for t in load_dataset("data/development_cases.json")}
    analysis = analyze_transaction(cases["TXN_012"])
    
    res = generate_explanation(analysis)
    assert "INSUFFICIENT EVIDENCE" in res.explanation
    assert "merchant_snapshot.ram_gb" in res.explanation
