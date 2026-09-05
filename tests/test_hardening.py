from app.engine.helpers import validation_was_performed
from app.engine.incidents import classify_incident
from app.llm.explainer import generate_explanation
from app.models.lifecycle import TransactionLifecycle
from app.models.result import AnalysisResult, AnalysisStatus, PreventabilityRating
from app.models.transaction import Transaction
from app.models.incident import IncidentType


def base_txn():
    return Transaction.model_validate({
        "transaction_id": "HARDEN_001",
        "timestamp": "2026-09-05T10:00:00Z",
        "user_request": {"raw_text": "Buy a phone.", "timestamp": "2026-09-05T09:55:00Z", "explicit_constraints": {}},
        "agent_interpretation": {"parsed_constraints": {}, "accessed_constraint_keys": [], "execution_trace": []},
        "merchant_snapshot": {},
        "agent_decision": {"validation_steps_performed": ["ram_gb"]},
        "dispute": {"disputed_field": "price", "user_claim": "Problem", "dispute_timestamp": "2026-09-05T11:00:00Z"},
    })


def test_inventory_race_requires_ordered_timestamps():
    txn = base_txn()
    txn.lifecycle = TransactionLifecycle.model_validate({"inventory": {"available_at_selection": True, "available_at_checkout": False}})
    result = classify_incident(txn)
    assert result.incident_type == IncidentType.NORMAL_PURCHASE
    assert result.status == "INSUFFICIENT_EVIDENCE"


def test_fulfillment_quantity_mismatch_is_fulfillment_error():
    txn = base_txn()
    txn.lifecycle = TransactionLifecycle.model_validate({"fulfillment": {"delivered": True, "expected_quantity": 2, "actual_quantity": 1}})
    result = classify_incident(txn)
    assert result.incident_type == IncidentType.FULFILLMENT_ERROR


def test_fulfillment_variant_mismatch_is_wrong_item_or_variant():
    txn = base_txn()
    txn.lifecycle = TransactionLifecycle.model_validate({"fulfillment": {"delivered": True, "expected_variant": "Black / 10", "actual_variant": "Red / 10"}})
    result = classify_incident(txn)
    assert result.incident_type == IncidentType.WRONG_ITEM_OR_VARIANT


def test_trace_is_authoritative_over_legacy_validation_summary():
    txn = base_txn()
    txn.agent_interpretation.execution_trace = [{"event_id": "E1", "timestamp": "2026-09-05T09:56:00Z", "action": "search", "arguments": {}, "result": {}, "status": "RECORDED"}]
    assert validation_was_performed(txn, "ram_gb") is False


def test_llm_prompt_fallback_contains_real_values():
    analysis = AnalysisResult(
        transaction_id="PROMPT_001", status=AnalysisStatus.ANALYZED,
        preventability=PreventabilityRating.HIGH,
        primary_fault=None, all_rule_results=[], evidence=[], contributing_factors=[],
    )
    result = generate_explanation(analysis, provider="mock")
    assert "NO_FAULT_DETECTED" in result.explanation
    assert "if analysis.primary_fault" not in result.explanation
