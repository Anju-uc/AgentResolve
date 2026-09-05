from app.engine.incidents import classify_incident
from app.models.transaction import Transaction
from app.models.lifecycle import TransactionLifecycle
from app.models.incident import IncidentType, ResponsibilityActor


def base_txn():
    return Transaction.model_validate({
        "transaction_id": "INC_001",
        "timestamp": "2026-09-03T10:00:00Z",
        "user_request": {
            "raw_text": "Buy a phone.",
            "timestamp": "2026-09-03T09:55:00Z",
            "explicit_constraints": {},
        },
        "agent_interpretation": {"parsed_constraints": {}, "accessed_constraint_keys": []},
        "merchant_snapshot": {},
        "agent_decision": {},
        "dispute": {
            "disputed_field": "price",
            "user_claim": "There was a problem.",
            "dispute_timestamp": "2026-09-03T11:00:00Z",
        },
    })


def test_unauthorized_transaction():
    txn = base_txn()
    txn.lifecycle = TransactionLifecycle.model_validate({
        "authorization": {
            "user_authorized": False,
            "initiated_by_agent": True,
        }
    })
    result = classify_incident(txn)
    assert result.incident_type == IncidentType.UNAUTHORIZED_TRANSACTION
    assert result.recorded_responsibility == ResponsibilityActor.AGENT


def test_payment_processing_failure():
    txn = base_txn()
    txn.lifecycle = TransactionLifecycle.model_validate({"payment": {"status": "TIMEOUT"}})
    result = classify_incident(txn)
    assert result.incident_type == IncidentType.PAYMENT_PROCESSING_FAILURE


def test_non_delivery():
    txn = base_txn()
    txn.lifecycle = TransactionLifecycle.model_validate({
        "payment": {"status": "CAPTURED"},
        "fulfillment": {
            "delivered": False,
            "shipment_status": "NOT_SHIPPED",
            "responsible_party": "MERCHANT",
        },
    })
    result = classify_incident(txn)
    assert result.incident_type == IncidentType.NON_DELIVERY
    assert result.recorded_responsibility == ResponsibilityActor.MERCHANT


def test_refund_failure():
    txn = base_txn()
    txn.lifecycle = TransactionLifecycle.model_validate({
        "refund": {
            "return_accepted": True,
            "refund_expected": 500.0,
            "refund_received": 0.0,
        }
    })
    result = classify_incident(txn)
    assert result.incident_type == IncidentType.RETURN_REFUND_FAILURE


def test_system_integration_failure():
    txn = base_txn()
    txn.lifecycle = TransactionLifecycle.model_validate({
        "integration": {
            "agent_order_item_id": "ITEM-A",
            "merchant_recorded_item_id": "ITEM-B",
        }
    })
    result = classify_incident(txn)
    assert result.incident_type == IncidentType.SYSTEM_INTEGRATION_FAILURE


def test_incident_corpus_is_classifiable():
    import json
    from pathlib import Path

    raw_cases = json.loads(Path("data/incident_cases.json").read_text())
    results = []
    for raw in raw_cases:
        txn = Transaction.model_validate(raw)
        results.append(classify_incident(txn).incident_type)

    assert len(results) == 14
    assert IncidentType.UNAUTHORIZED_TRANSACTION in results
    assert IncidentType.SYSTEM_INTEGRATION_FAILURE in results
    assert IncidentType.DUPLICATE_CHARGE in results
