"""Deterministic counterfactual replay for AgentResolve."""

from __future__ import annotations

from typing import Optional, Any, Tuple

from app.models.transaction import Transaction
from app.models.result import (
    CounterfactualResult,
    FaultAttribution,
    FaultCategory,
)

from app.engine.helpers import (
    constraint_is_violated,
    constraint_is_satisfied,
    get_field_constraint,
    get_purchased_or_actual_value,
    agent_had_constraint,
)


def _candidate_fields(txn: Transaction):
    c = txn.user_request.explicit_constraints

    fields = [
        "price_usd",
        "ram_gb",
        "storage_gb",
        "seller",
        "delivery_days",
        "color",
        "condition",
    ]

    fields += list(
        (getattr(c, "custom_attributes", {}) or {}).keys()
    )

    out = []
    seen = set()

    for field in fields:
        if field in seen:
            continue

        target, _ = get_field_constraint(c, field)

        if target is not None:
            seen.add(field)
            out.append(field)

    return out


def _first_agent_trigger(
    txn: Transaction,
) -> Optional[Tuple[str, Any, str, Any]]:

    c = txn.user_request.explicit_constraints

    validations = {
        str(x).strip().lower()
        for x in (
            getattr(
                txn.agent_decision,
                "validation_steps_performed",
                [],
            )
            or []
        )
    }

    for field in _candidate_fields(txn):

        target, op = get_field_constraint(
            c,
            field,
        )

        if target is None:
            continue

        if not agent_had_constraint(
            txn,
            field,
        ):
            continue

        purchased, _ = get_purchased_or_actual_value(
            txn,
            field,
        )

        if purchased is None:
            continue

        if not constraint_is_violated(
            purchased,
            c,
            field,
        ):
            continue

        aliases = {
            field.lower(),
            field.replace(
                "_gb",
                "",
            ).replace(
                "_usd",
                "",
            ).lower(),
        }

        if aliases & validations:
            continue

        return (
            field,
            target,
            op or "at most",
            purchased,
        )

    return None


def _first_merchant_trigger(txn: Transaction):
    m = txn.merchant_snapshot

    checks = [
        (
            "price_usd",
            getattr(m, "price", None),
            getattr(m, "price_at_checkout", None),
            "verify_checkout_price",
        ),
        (
            "seller",
            getattr(m, "seller", None),
            getattr(m, "seller_at_checkout", None),
            "verify_seller_at_checkout",
        ),
        (
            "ram_gb",
            getattr(m, "ram_gb", None),
            getattr(m, "ram_gb_actual", None),
            "verify_ram",
        ),
        (
            "storage_gb",
            getattr(m, "storage_gb", None),
            getattr(m, "storage_gb_actual", None),
            "verify_storage",
        ),
    ]

    for field, expected, actual, action in checks:
        if (
            expected is not None
            and actual is not None
            and expected != actual
        ):
            return (
                field,
                expected,
                actual,
                action,
            )

    for field, attr in (
        getattr(m, "attributes", {}) or {}
    ).items():

        advertised = getattr(
            attr,
            "advertised",
            None,
        )

        checkout = getattr(
            attr,
            "checkout",
            None,
        )

        delivered = getattr(
            attr,
            "delivered",
            None,
        )

        actual = (
            checkout
            if checkout is not None
            and checkout != advertised
            else delivered
        )

        if (
            advertised is not None
            and actual is not None
            and actual != advertised
        ):
            return (
                field,
                advertised,
                actual,
                f"verify_{field}",
            )

    return None


def _first_external_trigger(txn: Transaction):
    c = txn.user_request.explicit_constraints

    for field in _candidate_fields(txn):

        target, op = get_field_constraint(
            c,
            field,
        )

        purchased = None
        later = None

        try:
            from app.engine.rules import _state

            purchased, later = _state(
                txn,
                field,
            )
        except Exception:
            continue

        if (
            target is None
            or purchased is None
            or later is None
        ):
            continue

        if (
            constraint_is_satisfied(
                purchased,
                c,
                field,
            )
            and constraint_is_violated(
                later,
                c,
                field,
            )
        ):
            return (
                field,
                f"{op} {target}",
                purchased,
                later,
            )

    return None


def simulate_counterfactual(
    txn: Transaction,
    primary_fault: Optional[FaultAttribution],
    is_insufficient_evidence: bool = False,
) -> CounterfactualResult:

    if (
        is_insufficient_evidence
        or primary_fault is None
    ):
        return CounterfactualResult(
            applicable=False,
            action=None,
            expected=None,
            actual=None,
            result=(
                "COUNTERFACTUAL_NOT_APPLICABLE_"
                "DUE_TO_INSUFFICIENT_EVIDENCE"
            ),
            narrative=(
                "Counterfactual replay was not performed "
                "because the required transaction evidence "
                "is incomplete or no supported primary "
                "attribution exists."
            ),
        )

    category = primary_fault.category

    # ---------------------------------------------------------
    # AGENT MISJUDGMENT
    # ---------------------------------------------------------
    if category == FaultCategory.AGENT_MISJUDGMENT:

        trigger = _first_agent_trigger(txn)

        if trigger:
            (
                field,
                target,
                op,
                purchased,
            ) = trigger

            return CounterfactualResult(
                applicable=True,
                action=f"validate_{field}",
                expected=f"{op} {target}",
                actual=purchased,
                result="PURCHASE_WOULD_HAVE_BEEN_BLOCKED",
                narrative=(
                    f"Under the recorded constraints, "
                    f"validating {field} before purchase "
                    f"would have evaluated the recorded "
                    f"purchased value ({purchased}) "
                    f"against the requirement "
                    f"({op} {target}); "
                    f"the purchase would have been blocked "
                    f"before execution."
                ),
            )

    # ---------------------------------------------------------
    # MERCHANT DATA ERROR
    # ---------------------------------------------------------
    if category == FaultCategory.MERCHANT_DATA_ERROR:

        trigger = _first_merchant_trigger(txn)

        if trigger:
            (
                field,
                expected,
                actual,
                action,
            ) = trigger

            if field == "price_usd":
                result_code = (
                    "PRICE_DISCREPANCY_"
                    "WOULD_HAVE_BEEN_FLAGGED"
                )
            else:
                result_code = (
                    "MERCHANT_INCONSISTENCY_"
                    "WOULD_HAVE_BEEN_FLAGGED"
                )

            return CounterfactualResult(
                applicable=True,
                action=action,
                expected=expected,
                actual=actual,
                result=result_code,
                narrative=(
                    f"If {field} had been reconciled "
                    f"across the recorded merchant states "
                    f"before payment, the discrepancy "
                    f"between expected ({expected}) and "
                    f"observed ({actual}) would have been "
                    f"flagged before execution."
                ),
            )

    # ---------------------------------------------------------
    # EXTERNAL CHANGE
    # ---------------------------------------------------------
    if category == FaultCategory.EXTERNAL_CHANGE:

        trigger = _first_external_trigger(txn)

        if trigger:

            (
                field,
                requirement,
                purchase_value,
                later_value,
            ) = trigger

            return CounterfactualResult(
                applicable=True,
                action=(
                    f"verify_{field}_after_purchase"
                ),
                expected=(
                    f"{requirement} at purchase"
                ),
                actual={
                    "at_purchase": purchase_value,
                    "later": later_value,
                },
                result=(
                    "POST_PURCHASE_CHANGE_"
                    "NOT_PREVENTABLE_BY_"
                    "PRE_PURCHASE_VALIDATION"
                ),
                narrative=(
                    f"The recorded {field} state "
                    f"satisfied the requirement at "
                    f"purchase ({purchase_value}) and "
                    f"violated it later ({later_value}). "
                    f"A pre-purchase validation could not "
                    f"by itself prevent a change that the "
                    f"record places after purchase."
                ),
            )

    # ---------------------------------------------------------
    # NO ACTION
    # ---------------------------------------------------------
    return CounterfactualResult(
        applicable=False,
        action=None,
        expected=None,
        actual=None,
        result=(
            "NO_PRE_PURCHASE_ACTION_APPLICABLE"
        ),
        narrative=(
            "No additional deterministic pre-purchase "
            "action is supported by the primary attribution "
            "and recorded evidence."
        ),
    )