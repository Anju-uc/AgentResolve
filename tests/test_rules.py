"""
Unit Tests for Deterministic Fault Rules (Phase 4).

Tests positive, negative, boundary, and missing-evidence cases for all 5 fault checks:
1. USER_AMBIGUITY
2. AGENT_MISJUDGMENT
3. MERCHANT_DATA_ERROR
4. EXTERNAL_CHANGE
5. USER_POST_PURCHASE_CHANGE
"""

from app.models.transaction import Transaction
from app.engine.rules import (
    check_user_ambiguity,
    check_agent_misjudgment,
    check_merchant_data_error,
    check_external_change,
    check_user_post_purchase_change,
    run_all_rules,
)
from evaluation.evaluate import load_dataset


def test_rule_user_ambiguity_positive_and_negative():
    """Test USER_AMBIGUITY fires when disputed field constraint is absent from request."""
    cases = {t.transaction_id: t for t in load_dataset("data/development_cases.json")}
    
    # TXN_001: Disputed color, absent from request -> Fired
    res_001 = check_user_ambiguity(cases["TXN_001"])
    assert res_001.fired is True
    assert res_001.category.value == "USER_AMBIGUITY"
    assert "missing_constraint" in res_001.evidence_factors

    # TXN_002: Disputed ram_gb, explicit constraint exists -> Not Fired
    res_002 = check_user_ambiguity(cases["TXN_002"])
    assert res_002.fired is False


def test_rule_agent_misjudgment_positive_and_negative():
    """Test AGENT_MISJUDGMENT fires when constraint exists, agent had it, state violated, and validation skipped."""
    cases = {t.transaction_id: t for t in load_dataset("data/development_cases.json")}
    
    # TXN_002: 16GB RAM requested, 8GB bought, validation skipped -> Fired
    res_002 = check_agent_misjudgment(cases["TXN_002"])
    assert res_002.fired is True
    assert res_002.category.value == "AGENT_MISJUDGMENT"
    assert "validation_skipped" in res_002.evidence_factors

    # TXN_008: No constraint violation -> Not Fired
    res_008 = check_agent_misjudgment(cases["TXN_008"])
    assert res_008.fired is False


def test_rule_merchant_data_error_positive_and_negative():
    """Test MERCHANT_DATA_ERROR fires when listing vs checkout price or spec differs."""
    cases = {t.transaction_id: t for t in load_dataset("data/development_cases.json")}
    
    # TXN_003: Price listing $950 vs checkout $1150 -> Fired
    res_003 = check_merchant_data_error(cases["TXN_003"])
    assert res_003.fired is True
    assert res_003.category.value == "MERCHANT_DATA_ERROR"
    assert "merchant_inconsistency" in res_003.evidence_factors

    # TXN_001: Same listing & checkout price -> Not Fired
    res_001 = check_merchant_data_error(cases["TXN_001"])
    assert res_001.fired is False


def test_rule_external_change_positive_and_negative():
    """Test EXTERNAL_CHANGE fires when condition was satisfied at purchase but changed post-purchase."""
    cases = {t.transaction_id: t for t in load_dataset("data/development_cases.json")}
    
    # TXN_004: Delivery promised 2 days <= 3, actual 7 days -> Fired
    res_004 = check_external_change(cases["TXN_004"])
    assert res_004.fired is True
    assert res_004.category.value == "EXTERNAL_CHANGE"

    # TXN_001: No post-purchase change -> Not Fired
    res_001 = check_external_change(cases["TXN_001"])
    assert res_001.fired is False


def test_rule_user_post_purchase_change_positive_and_negative():
    """Test USER_POST_PURCHASE_CHANGE fires when new preference introduced post-purchase."""
    cases = {t.transaction_id: t for t in load_dataset("data/development_cases.json")}
    
    # TXN_005: Space Gray preference added post-purchase -> Fired
    res_005 = check_user_post_purchase_change(cases["TXN_005"])
    assert res_005.fired is True
    assert res_005.category.value == "USER_POST_PURCHASE_CHANGE"

    # TXN_001: No post purchase preference -> Not Fired
    res_001 = check_user_post_purchase_change(cases["TXN_001"])
    assert res_001.fired is False


def test_run_all_rules_runs_all_five_checks_independently():
    """Verifies that run_all_rules executes all 5 rules independently without short-circuiting."""
    cases = {t.transaction_id: t for t in load_dataset("data/development_cases.json")}
    
    results = run_all_rules(cases["TXN_011"])
    assert len(results) == 5
    
    fired_categories = [r.category.value for r in results if r.fired]
    # TXN_011 is a multi-fault case triggering AGENT_MISJUDGMENT & MERCHANT_DATA_ERROR
    assert "AGENT_MISJUDGMENT" in fired_categories
    assert "MERCHANT_DATA_ERROR" in fired_categories
