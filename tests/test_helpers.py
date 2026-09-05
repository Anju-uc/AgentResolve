"""
Unit Tests for Deterministic Constraint Helpers (Phase 3).

Verifies explicit mathematical comparison operators and constraint helpers:
- 'under' -> <
- 'at most' -> <=
- 'minimum' -> >=
- 'exactly' -> ==
"""

from app.models.transaction import Constraints
from app.engine.helpers import (
    compare_values,
    constraint_is_satisfied,
    constraint_is_violated,
    merchant_value_changed,
)


def test_comparison_operator_under():
    """Test 'under' (<) comparison semantics."""
    assert compare_values(99.0, 100.0, "under") is True
    assert compare_values(100.0, 100.0, "under") is False
    assert compare_values(101.0, 100.0, "under") is False


def test_comparison_operator_at_most():
    """Test 'at most' (<=) comparison semantics."""
    assert compare_values(99.0, 100.0, "at most") is True
    assert compare_values(100.0, 100.0, "at most") is True
    assert compare_values(101.0, 100.0, "at most") is False


def test_comparison_operator_minimum():
    """Test 'minimum' (>=) comparison semantics."""
    assert compare_values(16.0, 16.0, "minimum") is True
    assert compare_values(32.0, 16.0, "minimum") is True
    assert compare_values(8.0, 16.0, "minimum") is False


def test_comparison_operator_exactly():
    """Test 'exactly' (==) comparison semantics."""
    assert compare_values("OfficialStore", "OfficialStore", "exactly") is True
    assert compare_values("ThirdParty", "OfficialStore", "exactly") is False
    assert compare_values(512, 512, "exactly") is True
    assert compare_values(256, 512, "exactly") is False


def test_constraint_satisfied_and_violated_helpers():
    """Test constraint_is_satisfied and constraint_is_violated functions."""
    c = Constraints(ram_gb=16.0, ram_gb_operator="minimum")
    
    assert constraint_is_satisfied(16.0, c, "ram_gb") is True
    assert constraint_is_satisfied(8.0, c, "ram_gb") is False
    
    assert constraint_is_violated(8.0, c, "ram_gb") is True
    assert constraint_is_violated(16.0, c, "ram_gb") is False


def test_merchant_value_changed():
    """Test detection of merchant value changes between listing and checkout/actual."""
    assert merchant_value_changed(999.0, 1099.0) is True
    assert merchant_value_changed("OfficialStore", "ThirdParty") is True
    assert merchant_value_changed(500.0, 500.0) is False
    assert merchant_value_changed(None, 500.0) is False
