from app.engine.helpers import compare_values, validation_was_performed
from app.models.transaction import Transaction
from agent.execution_trace import build_event
from app.engine.provenance import verify_event_chain
from app.engine.drift import detect_dispute_drift


def test_generic_comparison_operators():
    assert compare_values(4, 5, "lte")
    assert compare_values("blue jacket", "jacket", "contains")
    assert compare_values(["charger", "case"], ["charger", "case", "cable"], "subset_of")
    assert compare_values("m3 pro", "m3 pro", "eq")


def test_execution_trace_is_authoritative_for_validation():
    txn = Transaction.model_validate({
        "transaction_id":"TRACE-1",
        "timestamp":"2026-09-03T12:00:00Z",
        "user_request":{"raw_text":"Buy under $100","timestamp":"2026-09-03T11:59:00Z","explicit_constraints":{"price_usd":100,"price_usd_operator":"under"}},
        "agent_interpretation":{"parsed_constraints":{"price_usd":100,"price_usd_operator":"under"},"accessed_constraint_keys":["price_usd"],"execution_trace":[build_event("E0","validate_constraint", arguments={"field":"price_usd"}), build_event("E1","checkout")]},
        "merchant_snapshot":{"price":80,"price_at_checkout":80},
        "agent_decision":{"selected_item_id":"X","purchased_price":80,"validation_steps_performed":[]},
        "dispute":{"disputed_field":"price","user_claim":"charged incorrectly","dispute_timestamp":"2026-09-03T13:00:00Z"},
    })
    assert validation_was_performed(txn, "price_usd") is True


def test_hash_chain_verification():
    e1 = build_event("E1", "parse_request")
    e2 = build_event("E2", "search_catalog", parent_hash=e1.content_hash)
    status, missing = verify_event_chain([e1.model_dump(), e2.model_dump()])
    assert status == "VERIFIED"
    assert missing == []


def test_dispute_drift_is_supporting_only():
    result = detect_dispute_drift("Buy a black laptop under 1000 dollars", "Actually I need silver and 2000 dollars")
    assert result.analyzed is True
    assert result.new_terms
