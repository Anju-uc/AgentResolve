"""
AgentResolve — Strict Deterministic Forensic Rule Engine

This module is intentionally conservative.

Core principles:
- Evidence first. Never guess from missing evidence.
- Incident ≠ fault attribution.
- Every canonical rule executes independently.
- A canonical fault fires only when its complete evidence predicate is satisfied.
- Missing, contradictory, or non-authoritative evidence produces a CLEAR/UNDETERMINED
  rule result, not a guessed fault.
- Low-level execution trace is authoritative when present.
- Human-readable evidence uses "Price", never "price_usd".
"""

from __future__ import annotations

from typing import Any, Iterable, List, Optional, Tuple

from app.models.transaction import Transaction
from app.models.result import RuleResult, FaultCategory, EvidenceItem
from app.engine.helpers import (
    constraint_exists,
    agent_had_constraint,
    validation_was_performed,
    constraint_is_satisfied,
    constraint_is_violated,
    merchant_value_changed,
    get_field_constraint,
    get_purchased_or_actual_value,
)


# ---------------------------------------------------------------------------
# Field normalization
# ---------------------------------------------------------------------------

FIELD_ALIASES = {
    "price": "price_usd",
    "price_usd": "price_usd",
    "ram": "ram_gb",
    "ram_gb": "ram_gb",
    "storage": "storage_gb",
    "storage_gb": "storage_gb",
    "delivery": "delivery_days",
    "delivery_days": "delivery_days",
    "seller": "seller",
    "color": "color",
    "condition": "condition",
}

DISPLAY_NAMES = {
    "price_usd": "Price",
    "ram_gb": "RAM",
    "storage_gb": "Storage",
    "delivery_days": "Delivery",
    "seller": "Seller",
    "color": "Color",
    "condition": "Condition",
}


def canonical_field(field: str) -> str:
    return FIELD_ALIASES.get(str(field).strip().lower(), str(field).strip())


def display_field(field: str) -> str:
    return DISPLAY_NAMES.get(canonical_field(field), str(field).replace("_", " ").title())


def _raw_text_mentions_field(txn: Transaction, field: str) -> bool:
    """Small deterministic parser-safety check; never used to create a requirement."""
    import re

    text = (txn.user_request.raw_text or "").lower()
    f = canonical_field(field)
    patterns = {
        "price_usd": [r"(?:under|below|at most|upto|up to|less than|maximum|min(?:imum)?)\s*[$₹€£]?[\d,]+", r"[$₹€£]\s*[\d,]+"],
        "ram_gb": [r"\b\d+(?:\.\d+)?\s*gb\s*(?:ram|memory)\b"],
        "storage_gb": [r"\b\d+(?:\.\d+)?\s*gb\s*(?:storage|ssd|disk)\b", r"\b\d+(?:\.\d+)?\s*tb\s*(?:storage|ssd|disk)\b"],
        "delivery_days": [r"(?:within|in|under|at most)\s*\d+\s*(?:day|days)\b"],
        "seller": [r"(?:from|seller|merchant|store)\s+[a-z0-9][a-z0-9 ._-]{1,40}"],
        "condition": [r"\b(?:new|refurbished|renewed|open[- ]?box|used)\b"],
        "color": [r"\b(?:black|white|red|blue|green|yellow|gold|silver|gray|grey|orange|purple|pink|brown|beige|space gray|space black)\b"],
    }
    return any(re.search(pattern, text) for pattern in patterns.get(f, []))


def _extract_color(txn: Transaction) -> Optional[str]:
    """Use explicitly recorded color fields first, then literal product-title color."""
    m = txn.merchant_snapshot
    d = txn.agent_decision
    candidates = [
        getattr(d, "attributes", {}).get("color") if isinstance(getattr(d, "attributes", None), dict) else None,
        getattr(m, "specs", {}).get("color") if isinstance(getattr(m, "specs", None), dict) else None,
        getattr(m, "title", None),
    ]
    colors = ["space gray", "space black", "black", "white", "red", "blue", "green", "yellow", "gold", "silver", "gray", "grey", "orange", "purple", "pink", "brown", "beige"]
    for value in candidates:
        if value is None:
            continue
        text = str(value).strip()
        low = text.lower()
        if low in colors:
            return text
        for color in colors:
            if color in low:
                return color.title()
    return None


def _constraint_fields(txn: Transaction) -> List[str]:
    """
    Return every explicitly constrained field, including generalized attributes.
    Duplicates and unset values are removed.
    """
    constraints = txn.user_request.explicit_constraints
    fields: List[str] = []

    for field in (
        "price_usd",
        "ram_gb",
        "storage_gb",
        "seller",
        "delivery_days",
        "color",
        "condition",
    ):
        if constraint_exists(constraints, field):
            fields.append(field)

    for field in (constraints.custom_attributes or {}):
        if constraint_exists(constraints, field):
            fields.append(field)

    # Preserve order while removing aliases/duplicates.
    seen = set()
    result = []
    for field in fields:
        c = canonical_field(field)
        if c not in seen:
            seen.add(c)
            result.append(c)
    return result


def _evidence(
    field: str,
    statement: str,
    expected: Any = None,
    actual: Any = None,
) -> EvidenceItem:
    return EvidenceItem(
        field=display_field(field),
        evidence_statement=statement,
        expected_value=expected,
        actual_value=actual,
    )


def _clear(
    category: FaultCategory,
    reason: str,
    factors: Optional[List[str]] = None,
) -> RuleResult:
    """
    A cleared rule still carries an inspectable explanation so the forensic
    ledger can explain why the rule did not fire.
    """
    return RuleResult(
        category=category,
        fired=False,
        evidence=[
            _evidence(
                field="RULE_EVALUATION",
                statement=reason,
            )
        ],
        evidence_factors=factors or [],
        raw_points=0,
    )


def _fire(
    category: FaultCategory,
    evidence: List[EvidenceItem],
    factors: List[str],
    raw_points: int,
) -> RuleResult:
    return RuleResult(
        category=category,
        fired=True,
        evidence=evidence,
        evidence_factors=factors,
        raw_points=raw_points,
    )


def _target(txn: Transaction, field: str) -> Tuple[Optional[Any], Optional[str]]:
    return get_field_constraint(
        txn.user_request.explicit_constraints,
        canonical_field(field),
    )


def _state(txn: Transaction, field: str) -> Tuple[Optional[Any], Optional[Any]]:
    """Return (at_purchase_or_checkout, later/actual) for standard/generalized fields."""
    f = canonical_field(field)
    m = txn.merchant_snapshot
    d = txn.agent_decision

    if f == "delivery_days":
        purchase = d.purchased_delivery_days
        if purchase is None:
            purchase = m.delivery_days
        later = m.delivery_days_actual
        return purchase, later

    if f == "seller":
        purchase = d.purchased_seller
        if purchase is None:
            purchase = m.seller_at_checkout or m.seller
        later = m.seller_at_checkout or purchase
        return purchase, later

    if f == "color":
        checkout = (
            getattr(d, "attributes", {}).get("color")
            if isinstance(getattr(d, "attributes", None), dict)
            else None
        )
        checkout = checkout or getattr(m, "color_at_checkout", None) or getattr(m, "color", None)
        checkout = checkout or _extract_color(txn)
        delivered = getattr(m, "color_actual", None) or checkout
        return checkout, delivered

    return get_purchased_or_actual_value(txn, f)


def _parse_time(value: Any):
    """Parse an ISO-8601 timestamp when possible; return None when unavailable."""
    if not value:
        return None
    from datetime import datetime
    text = str(value).strip()
    try:
        if text.endswith("Z"):
            text = text[:-1] + "+00:00"
        return datetime.fromisoformat(text)
    except (TypeError, ValueError):
        return None


def _purchase_cutoff(txn: Transaction):
    """Return the earliest reliable execution cutoff for pre-purchase validation."""
    candidates = []
    lifecycle = getattr(txn, "lifecycle", None)
    if lifecycle is not None:
        auth = getattr(lifecycle, "authorization", None)
        payment = getattr(lifecycle, "payment", None)
        if auth is not None and getattr(auth, "timestamp", None):
            candidates.append(_parse_time(auth.timestamp))
        if payment is not None and getattr(payment, "timestamp", None):
            candidates.append(_parse_time(payment.timestamp))
        for item in getattr(lifecycle, "event_log", []) or []:
            action = str(item.get("action", "")).lower().replace("-", "_")
            if any(token in action for token in ("authorize", "payment_capture", "payment_authorized", "checkout", "order_created")):
                candidates.append(_parse_time(item.get("timestamp")))
    candidates = [c for c in candidates if c is not None]
    if candidates:
        return min(candidates)
    return _parse_time(getattr(txn, "timestamp", None))


def _validation_evidence_state(txn: Transaction, field: str) -> str:
    """
    Returns one of:
      PASSED_PRE_PURCHASE
      FAILED_PRE_PURCHASE
      NOT_PERFORMED
      NOT_RECORDED
      POST_PURCHASE_ONLY

    Crucially, a validation event is not considered successful merely because
    its event status is SUCCESS. The result payload is inspected when it carries
    a boolean/pass-like outcome, and the event must occur before the purchase
    cutoff when timestamps are available.
    """
    aliases = {canonical_field(field)}
    if canonical_field(field) == "price_usd":
        aliases.add("price")
    if canonical_field(field) == "ram_gb":
        aliases.add("ram")
    if canonical_field(field) == "storage_gb":
        aliases.add("storage")
    if canonical_field(field) == "delivery_days":
        aliases.add("delivery")

    trace = list(getattr(txn.agent_interpretation, "execution_trace", []) or [])
    cutoff = _purchase_cutoff(txn)
    found_any = False
    found_pre = False
    found_post = False

    for event in trace:
        action = str(getattr(event, "action", "") or "").lower().replace("-", "_")
        arguments = getattr(event, "arguments", {}) or {}
        result = getattr(event, "result", {}) or {}
        observed_field = arguments.get("field") or result.get("field")
        if observed_field not in aliases:
            continue
        if not ("validat" in action or action in {"constraint_check", "checkout_validation"}):
            continue

        found_any = True
        event_time = _parse_time(getattr(event, "timestamp", None))
        is_pre = cutoff is None or event_time is None or event_time < cutoff
        if not is_pre:
            found_post = True
            continue
        found_pre = True

        status = str(getattr(event, "status", "") or "").upper()
        passed = result.get("passed")
        if passed is None:
            passed = result.get("valid")
        if passed is None:
            passed = result.get("satisfied")
        if passed is False:
            return "FAILED_PRE_PURCHASE"
        if passed is True:
            return "PASSED_PRE_PURCHASE"
        if status in {"FAILED", "ERROR"}:
            return "FAILED_PRE_PURCHASE"
        if status in {"SUCCESS", "RECORDED", "COMPLETED"}:
            # A generic success event without a field-level outcome is not enough
            # to prove the requirement was actually satisfied.
            return "NOT_RECORDED"

    if found_post and not found_pre:
        return "POST_PURCHASE_ONLY"
    if found_any and found_pre:
        return "NOT_RECORDED"

    # If any low-level trace exists, it is authoritative. A missing matching
    # validation event is NOT_PERFORMED; do not consult the legacy summary.
    if trace:
        return "NOT_PERFORMED"

    # Legacy records: the schema's validation_steps_performed field is the
    # explicit audit summary of validations actually performed. This fallback
    # is permitted only when no low-level trace exists.
    steps = getattr(txn.agent_decision, "validation_steps_performed", []) or []
    if any(alias in steps for alias in aliases):
        return "PASSED_PRE_PURCHASE"
    return "NOT_PERFORMED"


# ---------------------------------------------------------------------------
# USER_AMBIGUITY
# ---------------------------------------------------------------------------

def check_user_ambiguity(txn: Transaction) -> RuleResult:
    """
    Fires only when the customer's original requirement is genuinely absent.

    USER_AMBIGUITY is a canonical attribution rule, not an operational
    incident classifier. When the transaction record independently establishes
    an operational incident (for example payment failure, non-delivery,
    product defect, inventory race, duplicate charge, or integration failure),
    this rule must not reinterpret the incident as user ambiguity merely
    because the disputed field was not an original constraint.

    A structured-parser omission is also not treated as user ambiguity when the
    raw request explicitly mentions the disputed attribute.
    """
    disputed_field = canonical_field(txn.dispute.disputed_field)
    constraints = txn.user_request.explicit_constraints

    # ------------------------------------------------------------------
    # Gate 0: incident / attribution separation
    # ------------------------------------------------------------------
    # Operational incident detection answers WHAT happened. This rule answers
    # whether the user's requirement itself was ambiguous. Keep the layers
    # separate so operational failures cannot be relabelled as user faults.
    try:
        from app.engine.incidents import classify_incident

        incident = classify_incident(txn)
        incident_type = getattr(
            getattr(incident, "incident_type", None),
            "value",
            str(getattr(incident, "incident_type", "")),
        )
        if incident_type and incident_type != "NORMAL_PURCHASE":
            return _clear(
                FaultCategory.USER_AMBIGUITY,
                (
                    f"The transaction has an independently recorded operational incident "
                    f"({incident_type}); this canonical rule does not convert an operational "
                    "incident into USER_AMBIGUITY without separate evidence that the user's "
                    "original requirement was genuinely ambiguous."
                ),
                ["incident_attribution_separation"],
            )
    except Exception:
        # If incident detection itself is unavailable, do not manufacture a
        # user-fault attribution from the absence of incident evidence. Continue
        # with the narrow user-ambiguity predicate below.
        pass

    # ------------------------------------------------------------------
    # Gate 1: original requirement is present
    # ------------------------------------------------------------------
    if constraint_exists(constraints, disputed_field):
        return _clear(
            FaultCategory.USER_AMBIGUITY,
            (
                f"{display_field(disputed_field)} was explicitly recorded in the "
                "original user requirements, so this rule does not support "
                "USER_AMBIGUITY."
            ),
        )

    # ------------------------------------------------------------------
    # Gate 2: raw request contradicts the structured omission
    # ------------------------------------------------------------------
    # The natural-language request is evidence, but it must not create a new
    # constraint here. Its presence only prevents us from calling the user
    # ambiguous when the parser failed to record an explicitly mentioned field.
    if _raw_text_mentions_field(txn, disputed_field):
        return _clear(
            FaultCategory.USER_AMBIGUITY,
            (
                f"The structured record contains no explicit {display_field(disputed_field)} "
                "constraint, but the original raw request contains language that appears "
                "to address that attribute. The record therefore does not establish that "
                "the user's requirement itself was ambiguous; parser/evidence reconciliation "
                "is required."
            ),
            ["parser_record_inconsistency"],
        )

    # ------------------------------------------------------------------
    # Gate 3: there must be an explicit later expectation / claim
    # ------------------------------------------------------------------
    claim = (txn.dispute.user_claim or "").strip()
    post_pref = (txn.dispute.post_purchase_preference or "").strip()

    if not claim and not post_pref:
        return _clear(
            FaultCategory.USER_AMBIGUITY,
            (
                f"{display_field(disputed_field)} was not constrained originally, "
                "but the dispute contains no recorded later requirement that "
                "would establish a new expectation."
            ),
        )

    # ------------------------------------------------------------------
    # Gate 4: missing original requirement + later expectation
    # ------------------------------------------------------------------
    return _fire(
        FaultCategory.USER_AMBIGUITY,
        [
            _evidence(
                disputed_field,
                (
                    f"The original request contains no explicit requirement for "
                    f"{display_field(disputed_field)}. The later dispute introduces "
                    "a concern about that attribute, so the original record does "
                    "not establish that requirement before purchase."
                ),
                expected="No explicit original requirement",
                actual=claim or post_pref,
            )
        ],
        ["missing_constraint"],
        50,
    )


# ---------------------------------------------------------------------------
# AGENT_MISJUDGMENT
# ---------------------------------------------------------------------------

def _agent_access_state(txn: Transaction, field: str) -> str:
    """Return ESTABLISHED / NOT_ESTABLISHED for agent access to a requirement."""
    if not agent_had_constraint(txn, field):
        return "NOT_ESTABLISHED"

    trace = list(getattr(txn.agent_interpretation, "execution_trace", []) or [])
    if trace:
        aliases = {canonical_field(field)}
        if canonical_field(field) == "price_usd": aliases.add("price")
        if canonical_field(field) == "ram_gb": aliases.add("ram")
        if canonical_field(field) == "storage_gb": aliases.add("storage")
        if canonical_field(field) == "delivery_days": aliases.add("delivery")

        for event in trace:
            action = str(getattr(event, "action", "") or "").lower().replace("-", "_")
            args = getattr(event, "arguments", {}) or {}
            result = getattr(event, "result", {}) or {}
            observed = args.get("field") or result.get("field")
            if observed in aliases and any(token in action for token in ("constraint", "requirement", "validate", "select", "checkout")):
                return "ESTABLISHED"

        # A trace exists but contains no event establishing access. Do not assume
        # access from a parsed summary alone.
        return "NOT_ESTABLISHED"

    # Legacy record: parsed constraints + accessed_constraint_keys are the available
    # execution summary. An empty key list does not establish access.
    keys = {canonical_field(x) for x in (getattr(txn.agent_interpretation, "accessed_constraint_keys", []) or [])}
    return "ESTABLISHED" if canonical_field(field) in keys else "NOT_ESTABLISHED"


def check_agent_misjudgment(txn: Transaction) -> RuleResult:
    """
    Strict four-gate predicate, evaluated separately for every explicit field:

        1) explicit requirement exists
        2) agent had the requirement
        3) purchased state violates it
        4) pre-purchase validation was not successfully performed

    A validation failure is NOT automatically treated as "skipped".
    The execution record must establish that the validation did not succeed.
    """

    fields = _constraint_fields(txn)

    if not fields:
        return _clear(
            FaultCategory.AGENT_MISJUDGMENT,
            "No explicit user constraints were recorded; the agent-misjudgment predicate cannot be satisfied.",
        )

    fired: List[EvidenceItem] = []
    gate_summaries: List[str] = []

    for field in fields:
        target, operator = _target(txn, field)

        agent_access = _agent_access_state(
            txn,
            field,
        )

        purchased, _ = _state(
            txn,
            field,
        )

        violated = constraint_is_violated(
            purchased,
            txn.user_request.explicit_constraints,
            field,
        )

        validation_state = _validation_evidence_state(
            txn,
            field,
        )

        # ------------------------------------------------------------------
        # Gate 1: explicit requirement exists
        # ------------------------------------------------------------------
        if target is None:
            gate_summaries.append(
                f"{display_field(field)}: CLEAR — no explicit target."
            )
            continue

        # ------------------------------------------------------------------
        # Gate 2: agent had usable access to the requirement
        # ------------------------------------------------------------------
        if agent_access != "ESTABLISHED":
            gate_summaries.append(
                f"{display_field(field)}: CLEAR — the record does not "
                "establish that the agent had usable access to this requirement."
            )
            continue

        # ------------------------------------------------------------------
        # Gate 3: purchased value exists and violates the requirement
        # ------------------------------------------------------------------
        if purchased is None:
            gate_summaries.append(
                f"{display_field(field)}: CLEAR — purchased value is not recorded."
            )
            continue

        if not violated:
            gate_summaries.append(
                f"{display_field(field)}: CLEAR — purchased value satisfied "
                "the recorded requirement."
            )
            continue

        # ------------------------------------------------------------------
        # Gate 4: validation must NOT have succeeded pre-purchase
        #
        # Important:
        # - PASSED_PRE_PURCHASE      -> clear
        # - FAILED_PRE_PURCHASE      -> clear
        # - POST_PURCHASE_ONLY       -> clear
        # - NOT_RECORDED             -> clear
        #
        # None of these states proves skipped validation.
        # ------------------------------------------------------------------
        if validation_state == "PASSED_PRE_PURCHASE":
            gate_summaries.append(
                f"{display_field(field)}: CLEAR — a pre-purchase validation "
                "record exists; this canonical rule requires skipped validation."
            )
            continue

        if validation_state == "FAILED_PRE_PURCHASE":
            gate_summaries.append(
                f"{display_field(field)}: CLEAR — validation occurred "
                "pre-purchase but failed; this canonical rule does not "
                "equate a failed check with a skipped check."
            )
            continue

        if validation_state == "POST_PURCHASE_ONLY":
            gate_summaries.append(
                f"{display_field(field)}: CLEAR — validation evidence exists "
                "only after purchase; the record does not establish that "
                "the pre-purchase check was skipped."
            )
            continue

        if validation_state == "NOT_RECORDED":
            gate_summaries.append(
                f"{display_field(field)}: CLEAR — the record does not "
                "establish a sufficiently specific pre-purchase validation outcome."
            )
            continue

        # ------------------------------------------------------------------
        # All four gates satisfied.
        # ------------------------------------------------------------------
        fired.append(
            _evidence(
                field,
                (
                    f"{display_field(field)} requirement ({operator} {target}) "
                    "was explicitly requested, agent access is established "
                    "from the recorded constraints, and the purchased value "
                    f"({purchased}) violated it. The recorded execution shows "
                    "no successful pre-purchase validation for this field."
                ),
                expected=f"{operator} {target}",
                actual=purchased,
            )
        )

    # ----------------------------------------------------------------------
    # At least one field satisfied all four gates.
    # ----------------------------------------------------------------------
    if fired:
        return _fire(
            FaultCategory.AGENT_MISJUDGMENT,
            fired,
            [
                "explicit_constraint",
                "agent_access",
                "agent_violation",
                "validation_skipped",
            ],
            100,
        )

    # ----------------------------------------------------------------------
    # No field satisfied all four gates.
    # ----------------------------------------------------------------------
    return _clear(
        FaultCategory.AGENT_MISJUDGMENT,
        "No field satisfied all four strict agent-misjudgment gates.",
        gate_summaries,
    )

# ---------------------------------------------------------------------------
# MERCHANT_DATA_ERROR
# ---------------------------------------------------------------------------

def check_merchant_data_error(txn: Transaction) -> RuleResult:
    """
    Fires only on a recorded merchant-state inconsistency that is observable
    across lifecycle stages.

    Price differences are treated as merchant-data evidence only when the
    transaction record does not explicitly explain them as a commercial
    adjustment. This prevents taxes/shipping/fees from being mislabeled as a
    listing error when those records exist.
    """

    m = txn.merchant_snapshot
    evidence: List[EvidenceItem] = []

    # Price: listing -> checkout
    if m.price is not None and m.price_at_checkout is not None:
        if merchant_value_changed(m.price, m.price_at_checkout):
            commercial = getattr(txn.lifecycle, "commercial", None)
            explained = bool(commercial)

            if not explained:
                evidence.append(
                    _evidence(
                        "price",
                        (
                            f"Merchant advertised Price {m.price}, but checkout "
                            f"recorded Price {m.price_at_checkout}. No separate "
                            "recorded commercial adjustment explains the difference."
                        ),
                        expected=m.price,
                        actual=m.price_at_checkout,
                    )
                )

    # Seller: listing -> checkout
    if m.seller is not None and m.seller_at_checkout is not None:
        if merchant_value_changed(m.seller, m.seller_at_checkout):
            evidence.append(
                _evidence(
                    "seller",
                    (
                        f"Merchant-listed Seller '{m.seller}' changed to "
                        f"'{m.seller_at_checkout}' at checkout."
                    ),
                    expected=m.seller,
                    actual=m.seller_at_checkout,
                )
            )

    # Standard physical attributes: listing -> delivered
    for field, listed, actual in (
        ("ram_gb", m.ram_gb, m.ram_gb_actual),
        ("storage_gb", m.storage_gb, m.storage_gb_actual),
    ):
        if listed is None or actual is None:
            continue

        if not merchant_value_changed(listed, actual):
            continue

        # Strict attribution: only treat the mismatch as merchant data error
        # when the listing/attribute was part of the transaction's recorded
        # decision context or explicit requirement.
        relevant = (
            constraint_exists(txn.user_request.explicit_constraints, field)
            or agent_had_constraint(txn, field)
            or str(field) in (getattr(m, "attributes", {}) or {})
        )

        if relevant:
            evidence.append(
                _evidence(
                    field,
                    (
                        f"Merchant-listed {display_field(field)} was {listed}, "
                        f"while delivered evidence records {actual}. The two "
                        "merchant states are inconsistent."
                    ),
                    expected=listed,
                    actual=actual,
                )
            )

    # Generalized attributes
    for field, attr in (getattr(m, "attributes", {}) or {}).items():
        advertised = getattr(attr, "advertised", None)
        delivered = getattr(attr, "delivered", None)
        checkout = getattr(attr, "checkout", None)

        if (
            advertised is not None
            and checkout is not None
            and merchant_value_changed(advertised, checkout)
        ):
            evidence.append(
                _evidence(
                    field,
                    (
                        f"Merchant advertised {display_field(field)} "
                        f"'{advertised}', but checkout recorded '{checkout}'."
                    ),
                    expected=advertised,
                    actual=checkout,
                )
            )

        elif (
            advertised is not None
            and delivered is not None
            and merchant_value_changed(advertised, delivered)
        ):
            evidence.append(
                _evidence(
                    field,
                    (
                        f"Merchant advertised {display_field(field)} "
                        f"'{advertised}', but delivered evidence records "
                        f"'{delivered}'."
                    ),
                    expected=advertised,
                    actual=delivered,
                )
            )

    if evidence:
        return _fire(
            FaultCategory.MERCHANT_DATA_ERROR,
            evidence,
            ["merchant_inconsistency"],
            40,
        )

    return _clear(
        FaultCategory.MERCHANT_DATA_ERROR,
        (
            "No relevant merchant attribute shows a recorded listing-to-checkout "
            "or listing-to-delivery inconsistency that this rule can establish."
        ),
    )


# ---------------------------------------------------------------------------
# EXTERNAL_CHANGE
# ---------------------------------------------------------------------------

def check_external_change(txn: Transaction) -> RuleResult:
    """
    Strict post-purchase change rule:

        value satisfied the requirement at purchase
        AND a later recorded value violates the same requirement
        AND the transition occurs after purchase in the recorded lifecycle

    A late value alone is insufficient.
    """
    constraints = txn.user_request.explicit_constraints
    fired: List[EvidenceItem] = []

    for field in _constraint_fields(txn):
        target, operator = _target(txn, field)
        checkout, actual = _state(txn, field)

        if target is None or checkout is None or actual is None:
            continue

        at_purchase_ok = constraint_is_satisfied(checkout, constraints, field)
        later_failed = constraint_is_violated(actual, constraints, field)

        if not (at_purchase_ok and later_failed):
            continue

        # For delivery and generalized attributes, the model's state sequence
        # itself is the evidence of change. We do not invent timestamps here.
        fired.append(
            _evidence(
                field,
                (
                    f"{display_field(field)} satisfied the recorded requirement "
                    f"({operator} {target}) at purchase ({checkout}), but the later "
                    f"recorded state ({actual}) violates the same requirement."
                ),
                expected=f"{operator} {target}",
                actual={"at_purchase": checkout, "later": actual},
            )
        )

    if fired:
        return _fire(
            FaultCategory.EXTERNAL_CHANGE,
            fired,
            ["post_purchase_change"],
            40,
        )

    return _clear(
        FaultCategory.EXTERNAL_CHANGE,
        (
            "No constrained field shows the required transition from satisfied "
            "at purchase to violated in a later recorded state."
        ),
    )


# ---------------------------------------------------------------------------
# USER_POST_PURCHASE_CHANGE
# ---------------------------------------------------------------------------

def check_user_post_purchase_change(txn: Transaction) -> RuleResult:
    """
    Fires only when the user explicitly records a new preference after purchase
    that was absent from the original request, and the original purchase
    satisfied the original requirement (or there was no original requirement).
    """
    pref = (txn.dispute.post_purchase_preference or "").strip()
    disputed_field = canonical_field(txn.dispute.disputed_field)

    if not pref:
        return _clear(
            FaultCategory.USER_POST_PURCHASE_CHANGE,
            "No explicit post-purchase preference was recorded.",
        )

    original_target, operator = _target(txn, disputed_field)
    purchased_value, _ = _state(txn, disputed_field)

    preference_is_new = (
        original_target is None
        or str(original_target).strip().lower() != pref.lower()
    )

    if not preference_is_new:
        return _clear(
            FaultCategory.USER_POST_PURCHASE_CHANGE,
            (
                f"The recorded post-purchase preference for {display_field(disputed_field)} "
                "matches the original requirement; no new preference was established."
            ),
        )

    if original_target is not None and purchased_value is None:
        return _clear(
            FaultCategory.USER_POST_PURCHASE_CHANGE,
            (
                f"The original {display_field(disputed_field)} requirement exists, "
                "but the purchased value is not recorded well enough to establish "
                "that it was satisfied."
            ),
        )

    if original_target is not None and not constraint_is_satisfied(
        purchased_value,
        txn.user_request.explicit_constraints,
        disputed_field,
    ):
        return _clear(
            FaultCategory.USER_POST_PURCHASE_CHANGE,
            (
                f"The original {display_field(disputed_field)} requirement was not "
                "shown to be satisfied at purchase, so this rule will not attribute "
                "the dispute to a later preference change."
            ),
        )

    return _fire(
        FaultCategory.USER_POST_PURCHASE_CHANGE,
        [
            _evidence(
                disputed_field,
                (
                    f"The original request did not require the later preference "
                    f"'{pref}' for {display_field(disputed_field)}. The preference "
                    "was recorded only after purchase, while the original recorded "
                    "requirement was satisfied or absent."
                ),
                expected=(
                    f"Original: {operator} {original_target}"
                    if original_target is not None
                    else "No original requirement"
                ),
                actual=f"Post-purchase preference: {pref}",
            )
        ],
        ["post_purchase_change"],
        40,
    )


# ---------------------------------------------------------------------------
# All canonical rules
# ---------------------------------------------------------------------------

def run_all_rules(txn: Transaction) -> List[RuleResult]:
    """
    Execute every canonical rule independently and in a stable order.

    Never short-circuit on the first fired rule.
    """
    return [
        check_user_ambiguity(txn),
        check_agent_misjudgment(txn),
        check_merchant_data_error(txn),
        check_external_change(txn),
        check_user_post_purchase_change(txn),
    ]
