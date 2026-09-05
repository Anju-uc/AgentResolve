"""Deterministic evidence-coverage scoring for AgentResolve."""

from __future__ import annotations

from typing import Any, Dict

from app.engine.provenance import verify_event_chain
from app.models.transaction import Transaction


WEIGHTS = {
    "request": 10,
    "constraints": 20,
    "agent_execution": 15,
    "decision": 15,
    "lifecycle": 15,
    "dispute": 5,
    "rule_audit": 10,
    "integrity": 10,
}


def _has(value: Any) -> bool:
    return value is not None and value not in (
        "",
        [],
        {},
    )


def _action(event: Any) -> str:
    if isinstance(event, dict):
        value = event.get("action", "")
    else:
        value = getattr(
            event,
            "action",
            "",
        )

    return str(value or "").lower()


def _fields(txn: Transaction):
    c = txn.user_request.explicit_constraints

    fields = []

    for field in (
        "price_usd",
        "ram_gb",
        "storage_gb",
        "seller",
        "delivery_days",
        "color",
        "condition",
    ):
        if getattr(c, field, None) is not None:
            fields.append(field)

    for field, value in (
        getattr(
            c,
            "custom_attributes",
            {},
        )
        or {}
    ).items():

        if value is not None and field not in fields:
            fields.append(field)

    return fields


def _target(txn: Transaction, field: str):
    c = txn.user_request.explicit_constraints

    value = getattr(
        c,
        field,
        None,
    )

    if value is not None:
        return value

    custom = (
        getattr(
            c,
            "custom_attributes",
            {},
        )
        or {}
    )

    value = custom.get(field)

    if isinstance(value, dict):
        return value.get("value")

    return value


def _observed(txn: Transaction, field: str):

    m = txn.merchant_snapshot
    d = txn.agent_decision

    if field == "price_usd":
        return (
            d.purchased_price
            if d.purchased_price is not None
            else (
                getattr(m, "price_at_checkout", None)
                or getattr(m, "price", None)
            )
        )

    if field == "ram_gb":
        return (
            d.purchased_ram_gb
            if d.purchased_ram_gb is not None
            else (
                getattr(m, "ram_gb_actual", None)
                or getattr(m, "ram_gb", None)
            )
        )

    if field == "storage_gb":
        return (
            getattr(m, "storage_gb_actual", None)
            or getattr(m, "storage_gb", None)
        )

    if field == "seller":
        return (
            getattr(d, "purchased_seller", None)
            or getattr(m, "seller_at_checkout", None)
            or getattr(m, "seller", None)
        )

    if field == "delivery_days":
        return (
            d.purchased_delivery_days
            if d.purchased_delivery_days is not None
            else (
                getattr(
                    m,
                    "delivery_days_actual",
                    None,
                )
                or getattr(
                    m,
                    "delivery_days",
                    None,
                )
            )
        )

    if field == "color":
        return (
            getattr(
                d,
                "purchased_color",
                None,
            )
            or getattr(
                m,
                "color_actual",
                None,
            )
            or getattr(
                m,
                "color_at_checkout",
                None,
            )
            or getattr(
                m,
                "color",
                None,
            )
            or (
                getattr(
                    m,
                    "specs",
                    {},
                )
                or {}
            ).get("color")
        )

    if field == "condition":
        return (
            (
                getattr(
                    m,
                    "specs",
                    {},
                )
                or {}
            ).get("condition")
            or (
                getattr(
                    d,
                    "attributes",
                    {},
                )
                or {}
            ).get("condition")
        )

    item = (
        getattr(
            m,
            "attributes",
            {},
        )
        or {}
    ).get(field)

    if item is not None:
        return (
            getattr(
                item,
                "delivered",
                None,
            )
            or getattr(
                item,
                "checkout",
                None,
            )
            or getattr(
                item,
                "advertised",
                None,
            )
        )

    return (
        getattr(
            m,
            "specs",
            {},
        )
        or {}
    ).get(field)


def evidence_breakdown(
    txn: Transaction,
    analysis: Any,
) -> Dict[str, Dict[str, Any]]:

    raw = (
        txn.user_request.raw_text
        or ""
    ).strip()

    fields = _fields(txn)

    observed_count = sum(
        _has(_target(txn, field))
        and _has(_observed(txn, field))
        for field in fields
    )

    request = (
        10
        if raw and txn.user_request.timestamp
        else 7
        if raw
        else 0
    )

    constraints = (
        round(
            20 * observed_count / len(fields)
        )
        if fields
        else (
            3
            if raw
            else 0
        )
    )

    trace = list(
        getattr(
            txn.agent_interpretation,
            "execution_trace",
            [],
        )
        or []
    )

    access = list(
        getattr(
            txn.agent_interpretation,
            "accessed_constraint_keys",
            [],
        )
        or []
    )

    meaningful = sum(
        bool(_action(event))
        for event in trace
    )

    execution = (
        min(
            15,
            meaningful
            + min(
                3,
                len(access),
            ),
        )
        if meaningful
        else (
            min(
                9,
                3 * len(access),
            )
            if access
            else 0
        )
    )

    d = txn.agent_decision

    decision_values = [
        getattr(
            d,
            "selected_item_id",
            None,
        ),
        getattr(
            d,
            "purchased_price",
            None,
        ),
        getattr(
            d,
            "purchased_seller",
            None,
        ),
        getattr(
            d,
            "validation_steps_performed",
            [],
        ),
        getattr(
            d,
            "attributes",
            {},
        ),
    ]

    decision = round(
        15
        * sum(
            _has(value)
            for value in decision_values
        )
        / len(decision_values)
    )

    life = getattr(
        txn,
        "lifecycle",
        None,
    )

    events = (
        list(
            getattr(
                life,
                "event_log",
                [],
            )
            or []
        )
        if life
        else []
    )

    actions = {
        _action(event)
        for event in events
    }

    groups = [
        ("request",),
        ("search", "catalog", "listing"),
        ("author",),
        (
            "checkout",
            "payment",
            "capture",
            "order",
        ),
        (
            "fulfill",
            "ship",
            "deliver",
        ),
        (
            "return",
            "refund",
            "dispute",
        ),
    ]

    lifecycle_hits = sum(
        any(
            any(
                token in action
                for token in group
            )
            for action in actions
        )
        for group in groups
    )

    lifecycle = round(
        15
        * lifecycle_hits
        / len(groups)
    )

    dispute = (
        5
        if (
            txn.dispute.user_claim.strip()
            and txn.dispute.disputed_field
            and txn.dispute.dispute_timestamp
        )
        else 3
        if txn.dispute.user_claim.strip()
        else 0
    )

    rules = list(
        getattr(
            analysis,
            "all_rule_results",
            [],
        )
        or []
    )

    rule_audit = min(
        10,
        round(
            10 * len(rules) / 5
        ),
    )

    integrity = 0
    reason = (
        "No event-chain evidence recorded."
    )

    if events:
        try:
            integrity_status, missing = (
                verify_event_chain(events)
            )

            integrity_status = str(
                integrity_status
            ).upper()

            if (
                integrity_status
                in {
                    "VERIFIED",
                    "VALID",
                }
                and not missing
            ):
                integrity = 10
                reason = (
                    "Event chain verified."
                )

            elif integrity_status == "UNVERIFIED":
                integrity = 4
                reason = (
                    "Event-chain integrity is "
                    "partial or failed; missing "
                    f"links: {len(missing)}."
                )

        except Exception:
            reason = (
                "Event-chain verification "
                "could not be completed."
            )

    result = {
        "request": (
            request,
            10,
            "Original request and timestamp.",
        ),
        "constraints": (
            constraints,
            20,
            (
                f"{observed_count}/"
                f"{len(fields)} constrained fields "
                "have recorded target and observed "
                "values."
                if fields
                else
                "No structured constraints recorded."
            ),
        ),
        "agent_execution": (
            execution,
            15,
            (
                f"{meaningful} trace events and "
                f"{len(access)} access keys recorded."
            ),
        ),
        "decision": (
            decision,
            15,
            "Decision evidence coverage.",
        ),
        "lifecycle": (
            lifecycle,
            15,
            "Lifecycle milestone coverage.",
        ),
        "dispute": (
            dispute,
            5,
            "Dispute field/claim/timestamp coverage.",
        ),
        "rule_audit": (
            rule_audit,
            10,
            (
                f"{len(rules)}/5 canonical rule "
                "results available."
            ),
        ),
        "integrity": (
            integrity,
            10,
            reason,
        ),
    }

    return {
        key: {
            "earned": earned,
            "weight": weight,
            "percent": (
                round(
                    100 * earned / weight
                )
                if weight
                else 0
            ),
            "reason": explanation,
        }
        for key, (
            earned,
            weight,
            explanation,
        ) in result.items()
    }


def calculate_forensic_score(
    txn: Transaction,
    status: str,
    integrity=None,
):
    analysis_view = type(
        "AnalysisView",
        (),
        {
            "all_rule_results": (
                [1, 2, 3, 4, 5]
                if status == "ANALYZED"
                else []
            )
        },
    )()

    parts = evidence_breakdown(
        txn,
        analysis_view,
    )

    return max(
        0,
        min(
            100,
            round(
                sum(
                    value["earned"]
                    for value in parts.values()
                )
            ),
        ),
    )


def forensic_score_breakdown(
    txn: Transaction,
    status: str,
    integrity=None,
):
    analysis_view = type(
        "AnalysisView",
        (),
        {
            "all_rule_results": (
                [1, 2, 3, 4, 5]
                if status == "ANALYZED"
                else []
            )
        },
    )()

    parts = evidence_breakdown(
        txn,
        analysis_view,
    )

    return {
        key: value["percent"]
        for key, value in parts.items()
    }