"""
Deterministic Constraint Helpers module for AgentResolve.

This module provides explicit mathematical comparison functions to verify whether
transaction parameters satisfy or violate recorded user/agent constraints.

EXPLICIT OPERATOR SEMANTICS (per rules.md section 20):
- "under"    -> <
- "at most"  -> <=
- "minimum"  -> >=
- "exactly"  -> ==

CRITICAL RULE: Do NOT infer or default missing values. If a required value is None,
helper logic returns None/False as appropriate without silent type coercion.
"""

from typing import Any, Optional, Tuple
import re
from app.models.transaction import Transaction, Constraints


def get_purchased_or_actual_value(txn: Transaction, field_name: str) -> Tuple[Optional[Any], Optional[Any]]:
    """
    Extracts the purchased state value and final delivered actual value for a field.

    Returns:
        Tuple (purchased_val, actual_val)
    """
    m = txn.merchant_snapshot
    d = txn.agent_decision

    if field_name in ["price", "price_usd"]:
        return d.purchased_price or m.price_at_checkout, m.price_at_checkout or m.price
    elif field_name in ["ram", "ram_gb"]:
        return d.purchased_ram_gb or m.ram_gb, m.ram_gb_actual or d.purchased_ram_gb or m.ram_gb
    elif field_name in ["storage", "storage_gb"]:
        return m.storage_gb, m.storage_gb_actual or m.storage_gb
    elif field_name == "color":
        val = m.specs.get("color")
        if not val and m.title:
            for c in ["Silver", "Space Gray", "Black", "Red", "White", "Blue", "Gold"]:
                if c.lower() in m.title.lower():
                    val = c
                    break
        return val, val
    elif field_name in m.specs:
        return m.specs[field_name], m.specs[field_name]

    attr = m.attributes.get(field_name)
    if attr is not None:
        return attr.checkout if attr.checkout is not None else attr.advertised, attr.delivered if attr.delivered is not None else (attr.checkout if attr.checkout is not None else attr.advertised)
    agent_attr = d.attributes.get(field_name)
    if isinstance(agent_attr, dict):
        value = agent_attr.get("value")
        return value, value
    if agent_attr is not None:
        return agent_attr, agent_attr

    return None, None


def get_field_constraint(constraints: Constraints, field_name: str) -> Tuple[Optional[Any], Optional[str]]:
    """Return value/operator for standard or generalized attributes."""
    aliases = {
        "price": "price_usd", "ram": "ram_gb",
        "storage": "storage_gb", "delivery": "delivery_days",
    }
    field = aliases.get(field_name, field_name)
    if hasattr(constraints, field):
        val = getattr(constraints, field)
        if val is not None:
            op = getattr(constraints, f"{field}_operator", None)
            if field in {"color", "condition"} and not op:
                op = "exactly"
            return val, op or "exactly"
    custom = constraints.custom_attributes.get(field_name)
    if custom is None and field != field_name:
        custom = constraints.custom_attributes.get(field)
    if isinstance(custom, dict) and "value" in custom:
        return custom.get("value"), custom.get("operator", "exactly")
    if custom is not None:
        return custom, "exactly"
    return None, None

def constraint_exists(constraints: Constraints, field_name: str) -> bool:
    """
    Checks whether a specific constraint field exists and is non-null.

    Args:
        constraints: Constraints object.
        field_name: Target attribute field.

    Returns:
        True if value is explicitly set and not None.
    """
    val, _ = get_field_constraint(constraints, field_name)
    return val is not None


def agent_had_constraint(txn: Transaction, field_name: str) -> bool:
    """
    Checks if the agent's interpretation contained the target constraint.

    Args:
        txn: Full Transaction object.
        field_name: Target attribute field.

    Returns:
        True if agent parsed_constraints contains non-null value for field_name.
    """
    agent_constraints = txn.agent_interpretation.parsed_constraints
    val, _ = get_field_constraint(agent_constraints, field_name)
    return val is not None


def validation_was_performed(txn: Transaction, field_name: str) -> bool:
    """Prefer derived execution evidence; legacy checklist is compatibility fallback."""
    aliases = {field_name}
    if field_name == "price_usd": aliases.add("price")
    if field_name == "ram_gb": aliases.add("ram")
    if field_name == "storage_gb": aliases.add("storage")
    if field_name == "delivery_days": aliases.add("delivery")

    trace = getattr(txn.agent_interpretation, "execution_trace", []) or []
    if trace:
        # Once low-level execution evidence exists, it is the sole authority.
        # A trace that contains no matching validation event therefore does not
        # establish that validation occurred; never fall back to the legacy summary.
        for event in trace:
            action = (getattr(event, "action", None) if not isinstance(event, dict) else event.get("action") or "") or ""
            action = str(action).lower().replace("-", "_")
            arguments = getattr(event, "arguments", None) if not isinstance(event, dict) else event.get("arguments", {})
            result = getattr(event, "result", None) if not isinstance(event, dict) else event.get("result", {})
            arguments = arguments or {}
            result = result or {}
            field = arguments.get("field") or result.get("field")
            if field in aliases and ("validat" in action or action in {"constraint_check", "checkout_validation"}):
                status = (getattr(event, "status", None) if not isinstance(event, dict) else event.get("status") or "") or ""
                status = str(status).upper()
                return status not in {"FAILED", "ERROR"}
        return False

    # Legacy benchmark compatibility is allowed only when no low-level trace exists.
    steps = txn.agent_decision.validation_steps_performed or []
    return any(alias in steps for alias in aliases)

def compare_values(actual_val: Any, target_val: Any, operator_str: str) -> bool:
    """Compare scalar/list/string values using explicit extensible operators."""
    if actual_val is None or target_val is None:
        return False
    op = (operator_str or "exactly").strip().lower().replace(" ", "_")
    if op in {"under", "<"}:
        op = "lt"
    elif op in {"at_most", "<="}:
        op = "lte"
    elif op in {"minimum", ">="}:
        op = "gte"
    elif op in {"exactly", "=="}:
        op = "eq"

    try:
        act = float(actual_val)
        tgt = float(target_val)
        if op == "lt": return act < tgt
        if op == "lte": return act <= tgt
        if op == "gte": return act >= tgt
        if op == "gt": return act > tgt
        if op == "eq": return act == tgt
    except (ValueError, TypeError):
        act_s = str(actual_val).strip().lower()
        tgt_s = str(target_val).strip().lower()
        if op == "eq": return act_s == tgt_s
        if op == "contains": return tgt_s in act_s
        if op == "subset_of":
            a = set(repr(x).lower() for x in actual_val) if isinstance(actual_val, (list, tuple, set)) else {act_s}
            t = set(repr(x).lower() for x in target_val) if isinstance(target_val, (list, tuple, set)) else {tgt_s}
            return a.issubset(t)
    if op == "contains":
        try: return target_val in actual_val
        except TypeError: return False
    if op == "subset_of":
        try: return set(actual_val).issubset(set(target_val))
        except TypeError: return False
    return str(actual_val).strip().lower() == str(target_val).strip().lower()

def constraint_is_satisfied(actual_val: Any, constraints: Constraints, field_name: str) -> bool:
    """
    Determines if an actual value satisfies the recorded constraint for field_name.

    Args:
        actual_val: Value observed.
        constraints: Constraints object.
        field_name: Attribute name.

    Returns:
        True if actual_val satisfies constraint. False if violated or constraint absent.
    """
    target_val, operator_str = get_field_constraint(constraints, field_name)
    if target_val is None or actual_val is None:
        return False
    return compare_values(actual_val, target_val, operator_str)


def constraint_is_violated(actual_val: Any, constraints: Constraints, field_name: str) -> bool:
    """
    Determines if an actual value violates the recorded constraint for field_name.

    Args:
        actual_val: Value observed.
        constraints: Constraints object.
        field_name: Attribute name.

    Returns:
        True if constraint exists AND actual_val fails comparison.
    """
    target_val, operator_str = get_field_constraint(constraints, field_name)
    if target_val is None or actual_val is None:
        return False
    return not compare_values(actual_val, target_val, operator_str)


def merchant_value_changed(initial_val: Any, final_val: Any) -> bool:
    """
    Checks if a merchant value changed between initial snapshot selection and checkout/actual state.

    Args:
        initial_val: Pre-purchase listed merchant value.
        final_val: Post-selection or actual merchant value.

    Returns:
        True if both values are non-null and differ.
    """
    if initial_val is None or final_val is None:
        return False
    return str(initial_val).strip() != str(final_val).strip()
