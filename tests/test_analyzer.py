"""
Unit & Regression Tests for Core Forensic Analyzer (Phase 6 & 10).

Verifies analyze_transaction() against all regression cases TXN_001 through TXN_011:
- TXN_001 -> USER_AMBIGUITY
- TXN_002 -> AGENT_MISJUDGMENT
- TXN_003 -> MERCHANT_DATA_ERROR
- TXN_004 -> EXTERNAL_CHANGE
- TXN_005 -> USER_POST_PURCHASE_CHANGE
- TXN_006 -> AGENT_MISJUDGMENT
- TXN_007 -> MERCHANT_DATA_ERROR
- TXN_008 -> NO_FAULT_DETECTED
- TXN_009 -> USER_AMBIGUITY
- TXN_010 -> NO_FAULT_DETECTED
- TXN_011 -> AGENT_MISJUDGMENT (contributor: MERCHANT_DATA_ERROR)
- TXN_012 -> INSUFFICIENT_EVIDENCE
- TXN_013 -> DUPLICATE_CHARGE data flag
"""

from app.models.result import AnalysisStatus
from app.engine.analyzer import analyze_transaction
from evaluation.evaluate import load_dataset


def test_regression_suite_txn_001_to_txn_011():
    """Runs regression test across TXN_001 through TXN_011."""
    cases = {t.transaction_id: t for t in load_dataset("data/development_cases.json")}
    
    expected_primary = {
        "TXN_001": "USER_AMBIGUITY",
        "TXN_002": "AGENT_MISJUDGMENT",
        "TXN_003": "MERCHANT_DATA_ERROR",
        "TXN_004": "EXTERNAL_CHANGE",
        "TXN_005": "USER_POST_PURCHASE_CHANGE",
        "TXN_006": "AGENT_MISJUDGMENT",
        "TXN_007": "MERCHANT_DATA_ERROR",
        "TXN_008": "NO_FAULT_DETECTED",
        "TXN_009": "USER_AMBIGUITY",
        "TXN_010": "NO_FAULT_DETECTED",
        "TXN_011": "AGENT_MISJUDGMENT",
    }
    
    for txn_id, exp_fault in expected_primary.items():
        txn = cases[txn_id]
        analysis = analyze_transaction(txn)
        
        assert analysis.status == AnalysisStatus.ANALYZED
        assert analysis.primary_fault is not None
        assert analysis.primary_fault.category.value == exp_fault, (
            f"Failed on {txn_id}: expected {exp_fault}, got {analysis.primary_fault.category.value}"
        )


def test_multi_fault_txn_011_retains_contributors():
    """Verifies that multi-fault case TXN_011 retains contributing factor MERCHANT_DATA_ERROR."""
    cases = {t.transaction_id: t for t in load_dataset("data/development_cases.json")}
    analysis = analyze_transaction(cases["TXN_011"])
    
    assert analysis.primary_fault.category.value == "AGENT_MISJUDGMENT"
    contrib_cats = [c.category.value for c in analysis.contributing_factors]
    assert "MERCHANT_DATA_ERROR" in contrib_cats


def test_insufficient_evidence_case_txn_012():
    """Verifies missing merchant RAM specification returns INSUFFICIENT_EVIDENCE."""
    cases = {t.transaction_id: t for t in load_dataset("data/development_cases.json")}
    analysis = analyze_transaction(cases["TXN_012"])
    
    assert analysis.status == AnalysisStatus.INSUFFICIENT_EVIDENCE
    assert "merchant_snapshot.ram_gb" in analysis.missing_fields
    assert analysis.primary_fault is None


def test_duplicate_charge_flag_txn_013():
    """Verifies duplicate charge is flagged under data_flags without creating agent or merchant fault."""
    cases = {t.transaction_id: t for t in load_dataset("data/development_cases.json")}
    analysis = analyze_transaction(cases["TXN_013"])
    
    assert "DUPLICATE_CHARGE" in analysis.data_flags
    assert analysis.primary_fault.category.value == "NO_FAULT_DETECTED"
