"""
Unit Tests for Domain Schemas (Phase 2 & 4).

Verifies Pydantic v2 domain model validation:
- Valid transaction models
- Malformed transaction JSON
- Null handling for optional constraints (None = not specified)
- Validates all dataset cases TXN_001 through TXN_011
"""

import pytest
from pydantic import ValidationError
from app.models.transaction import (
    Transaction,
    Constraints,
    UserRequest,
    AgentInterpretation,
    MerchantSnapshot,
    AgentDecision,
    Dispute,
)
from evaluation.evaluate import load_dataset


def test_valid_transaction_model_instantiation():
    """Test instantiating a valid Transaction object programmatically."""
    txn = Transaction(
        transaction_id="TXN_TEST_01",
        timestamp="2026-08-01T10:00:00Z",
        user_request=UserRequest(
            raw_text="Buy laptop with 16GB RAM under $1000",
            timestamp="2026-08-01T09:50:00Z",
            explicit_constraints=Constraints(ram_gb=16.0, price_usd=1000.0)
        ),
        agent_interpretation=AgentInterpretation(
            parsed_constraints=Constraints(ram_gb=16.0, price_usd=1000.0),
            accessed_constraint_keys=["ram_gb", "price_usd"]
        ),
        merchant_snapshot=MerchantSnapshot(
            item_id="LAP_100",
            price=900.0,
            price_at_checkout=900.0,
            ram_gb=16.0
        ),
        agent_decision=AgentDecision(
            selected_item_id="LAP_100",
            purchased_price=900.0,
            purchased_ram_gb=16.0,
            validation_steps_performed=["price", "ram_gb"]
        ),
        dispute=Dispute(
            disputed_field="price",
            user_claim="Test claim",
            dispute_timestamp="2026-08-02T10:00:00Z"
        )
    )
    assert txn.transaction_id == "TXN_TEST_01"
    assert txn.user_request.explicit_constraints.ram_gb == 16.0
    assert txn.user_request.explicit_constraints.color is None  # None preserved as not specified


def test_missing_required_fields_raises_validation_error():
    """Test that missing required fields throws ValidationError."""
    with pytest.raises(ValidationError):
        Transaction.model_validate({"transaction_id": "TXN_INVALID"})


def test_validate_all_development_dataset_cases():
    """Validates that all development dataset cases (TXN_001 through TXN_020) parse cleanly."""
    dev_cases = load_dataset("data/development_cases.json")
    assert len(dev_cases) == 20
    txn_ids = [t.transaction_id for t in dev_cases]
    for idx in range(1, 12):
        assert f"TXN_{idx:03d}" in txn_ids


def test_validate_all_holdout_dataset_cases():
    """Validates that all holdout dataset cases (TXN_021 through TXN_030) parse cleanly."""
    holdout_cases = load_dataset("data/holdout_cases.json")
    assert len(holdout_cases) == 10
