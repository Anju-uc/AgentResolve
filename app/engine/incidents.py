"""Deterministic operational incident detection for AgentResolve v2.

This layer answers WHAT happened operationally. It does not replace the six
canonical fault rules that answer attribution for constraint-based failures.
"""

from typing import List

from app.models.incident import (
    IncidentResult,
    IncidentSignal,
    IncidentType,
    ResponsibilityActor,
)
from app.models.transaction import Transaction
from app.models.lifecycle import TransactionLifecycle


def _parse_time(value):
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


def _signal(field: str, statement: str, expected=None, actual=None) -> IncidentSignal:
    return IncidentSignal(
        field=field,
        statement=statement,
        expected_value=expected,
        actual_value=actual,
    )


def classify_incident(txn: Transaction) -> IncidentResult:
    """Classify the most specific recorded operational incident available."""
    signals: List[IncidentSignal] = []
    related: List[IncidentType] = []
    actor = ResponsibilityActor.UNKNOWN
    actor_evidence = None

    lifecycle = TransactionLifecycle.model_validate(txn.lifecycle) if txn.lifecycle is not None else None

    if txn.duplicate_charge or (
        lifecycle and lifecycle.payment and lifecycle.payment.duplicate_detected is True
    ):
        signals.append(_signal(
            "duplicate_charge",
            "The transaction record contains a duplicate-charge signal.",
            expected=False,
            actual=True,
        ))
        return IncidentResult(
            incident_type=IncidentType.DUPLICATE_CHARGE,
            signals=signals,
        )

    if lifecycle:
        auth = lifecycle.authorization
        payment = lifecycle.payment
        fulfillment = lifecycle.fulfillment
        refund = lifecycle.refund
        inventory = lifecycle.inventory
        commercial = lifecycle.commercial
        integration = lifecycle.integration

        if auth:
            if auth.user_authorized is False:
                signals.append(_signal(
                    "authorization.user_authorized",
                    "Recorded authorization evidence states that the user did not authorize the transaction.",
                    expected=True,
                    actual=False,
                ))
                if auth.initiated_by_agent is True:
                    actor = ResponsibilityActor.AGENT
                    actor_evidence = "The record states the transaction was initiated by the agent while user authorization was false."
                return IncidentResult(
                    incident_type=IncidentType.UNAUTHORIZED_TRANSACTION,
                    signals=signals,
                    related_incidents=related,
                    recorded_responsibility=actor,
                    responsibility_evidence=actor_evidence,
                )

            if auth.user_authorized is None and auth.final_cart_approved is False:
                signals.append(_signal(
                    "authorization.final_cart_approved",
                    "The final cart was not approved and the record does not establish clear purchase consent.",
                    expected=True,
                    actual=False,
                ))
                return IncidentResult(
                    incident_type=IncidentType.AUTHORIZATION_SCOPE_AMBIGUITY,
                    signals=signals,
                )

            if (
                auth.authorization_limit is not None
                and auth.authorized_amount is not None
                and auth.authorized_amount > auth.authorization_limit
            ):
                signals.append(_signal(
                    "authorization.authorized_amount",
                    "The authorized amount exceeded the recorded authorization cap.",
                    expected=f"<= {auth.authorization_limit}",
                    actual=auth.authorized_amount,
                ))
                if auth.initiated_by_agent is True:
                    actor = ResponsibilityActor.AGENT
                    actor_evidence = "The recorded authorization amount exceeded the cap during an agent-initiated transaction."
                related.append(IncidentType.INCORRECT_AMOUNT)
                return IncidentResult(
                    incident_type=IncidentType.AUTHORIZATION_SCOPE_VIOLATION,
                    signals=signals,
                    related_incidents=related,
                    recorded_responsibility=actor,
                    responsibility_evidence=actor_evidence,
                )

        if payment:
            if (
                payment.authorized_amount is not None
                and payment.captured_amount is not None
                and payment.captured_amount != payment.authorized_amount
            ):
                signals.append(_signal(
                    "payment.captured_amount",
                    "The captured payment amount differs from the processor-authorized amount.",
                    expected=payment.authorized_amount,
                    actual=payment.captured_amount,
                ))
                harm = max(float(payment.captured_amount) - float(payment.authorized_amount), 0.0) if payment else None
                return IncidentResult(
                    incident_type=IncidentType.INCORRECT_AMOUNT,
                    signals=signals,
                    economic_harm=harm,
                    harm_currency=(payment.currency if payment else None),
                )

            if payment.status and payment.status.upper() in {
                "FAILED", "TIMEOUT", "UNKNOWN", "PENDING", "UNCERTAIN",
            }:
                signals.append(_signal(
                    "payment.status",
                    f"Payment processing ended in the recorded state '{payment.status}'.",
                    expected="CAPTURED",
                    actual=payment.status,
                ))
                return IncidentResult(
                    incident_type=IncidentType.PAYMENT_PROCESSING_FAILURE,
                    signals=signals,
                    recorded_responsibility=ResponsibilityActor.PAYMENT_SYSTEM,
                )

        if inventory and inventory.available_at_selection is True and inventory.available_at_checkout is False:
            selection_time = _parse_time(inventory.selection_timestamp)
            checkout_time = _parse_time(inventory.checkout_timestamp)

            if selection_time is not None and checkout_time is not None and checkout_time <= selection_time:
                signals.append(_signal(
                    "inventory.timestamps",
                    "The recorded checkout timestamp does not occur after the recorded selection timestamp; the inventory transition cannot be established as a race.",
                    expected="checkout_timestamp > selection_timestamp",
                    actual={"selection": inventory.selection_timestamp, "checkout": inventory.checkout_timestamp},
                ))
                return IncidentResult(incident_type=IncidentType.NORMAL_PURCHASE, signals=signals)

            # A race is a temporal claim, so both timestamps and their order
            # are required. Stage flags alone do not establish a race.
            if selection_time is None or checkout_time is None:
                signals.append(_signal(
                    "inventory.timestamps",
                    "Inventory changed from available at selection to unavailable at checkout, but the timestamp pair needed to establish a race is incomplete.",
                    expected="selection_timestamp and checkout_timestamp with checkout > selection",
                    actual={"selection": inventory.selection_timestamp, "checkout": inventory.checkout_timestamp},
                ))
                return IncidentResult(
                    incident_type=IncidentType.NORMAL_PURCHASE,
                    status="INSUFFICIENT_EVIDENCE",
                    signals=signals,
                )

            statement = "The item was available at selection but unavailable at checkout. Recorded timestamps establish checkout after selection."
            signals.append(_signal(
                "inventory.available_at_checkout",
                statement,
                expected=True,
                actual=False,
            ))
            return IncidentResult(
                incident_type=IncidentType.INVENTORY_RACE,
                signals=signals,
                recorded_responsibility=ResponsibilityActor.MERCHANT,
            )

        if integration:
            item_mismatch = (
                integration.agent_order_item_id is not None
                and integration.merchant_recorded_item_id is not None
                and integration.agent_order_item_id != integration.merchant_recorded_item_id
            )
            quantity_mismatch = (
                integration.agent_quantity is not None
                and integration.merchant_recorded_quantity is not None
                and integration.agent_quantity != integration.merchant_recorded_quantity
            )
            if item_mismatch or quantity_mismatch or integration.mismatch_detected is True:
                if item_mismatch:
                    signals.append(_signal(
                        "integration.item_id",
                        "The item ID sent by the agent differs from the item ID recorded by the merchant system.",
                        expected=integration.agent_order_item_id,
                        actual=integration.merchant_recorded_item_id,
                    ))
                if quantity_mismatch:
                    signals.append(_signal(
                        "integration.quantity",
                        "The quantity sent by the agent differs from the merchant-recorded quantity.",
                        expected=integration.agent_quantity,
                        actual=integration.merchant_recorded_quantity,
                    ))
                return IncidentResult(
                    incident_type=IncidentType.SYSTEM_INTEGRATION_FAILURE,
                    signals=signals,
                    recorded_responsibility=ResponsibilityActor.EXTERNAL_SYSTEM,
                )

        if commercial:
            if (
                commercial.promotion_expected_discount is not None
                and commercial.promotion_applied_discount is not None
                and commercial.promotion_expected_discount != commercial.promotion_applied_discount
            ):
                signals.append(_signal(
                    "commercial.promotion_discount",
                    "The recorded promotion discount differs from the expected promotion discount.",
                    expected=commercial.promotion_expected_discount,
                    actual=commercial.promotion_applied_discount,
                ))
                return IncidentResult(
                    incident_type=IncidentType.PROMOTION_FAILURE,
                    signals=signals,
                )

            fee_tax_total = None
            if commercial.total_amount is not None and commercial.checkout_subtotal is not None:
                fee_tax_total = commercial.total_amount - commercial.checkout_subtotal
            if fee_tax_total is not None and fee_tax_total > 0 and commercial.disclosed_fees_before_authorization is False:
                signals.append(_signal(
                    "commercial.fees_and_tax",
                    "Checkout added fees or taxes that the record says were not disclosed before authorization.",
                    expected=True,
                    actual=False,
                ))
                return IncidentResult(
                    incident_type=IncidentType.FEE_TAX_SURPRISE,
                    signals=signals,
                )

        if fulfillment:
            if payment and payment.status and payment.status.upper() == "CAPTURED":
                if fulfillment.delivered is False and fulfillment.shipment_status:
                    status = fulfillment.shipment_status.upper()
                    if status in {"NOT_SHIPPED", "CANCELLED", "NO_SHIPMENT", "LOST"}:
                        signals.append(_signal(
                            "fulfillment.shipment_status",
                            f"Payment was captured but shipment status is recorded as '{fulfillment.shipment_status}'.",
                            expected="SHIPPED",
                            actual=fulfillment.shipment_status,
                        ))
                        responsibility = ResponsibilityActor.UNKNOWN
                        responsibility_evidence = None
                        party = (fulfillment.responsible_party or "").upper()
                        if party == "MERCHANT":
                            responsibility = ResponsibilityActor.MERCHANT
                            responsibility_evidence = "The fulfillment record explicitly identifies the merchant as the responsible party."
                        elif party in {"CARRIER", "DELIVERY_PARTNER", "EXTERNAL_SYSTEM"}:
                            responsibility = ResponsibilityActor.EXTERNAL_SYSTEM
                            responsibility_evidence = "The fulfillment record explicitly identifies an external delivery party as responsible."
                        return IncidentResult(
                            incident_type=IncidentType.NON_DELIVERY,
                            signals=signals,
                            recorded_responsibility=responsibility,
                            responsibility_evidence=responsibility_evidence,
                        )

            # Fulfillment mismatches are operational incidents independent of
            # the six canonical attribution categories. Check item/variant and
            # quantity evidence before defect/delivery outcomes.
            if fulfillment.delivered is True:
                if fulfillment.actual_variant is not None and fulfillment.expected_variant is not None and fulfillment.actual_variant != fulfillment.expected_variant:
                    signals.append(_signal(
                        "fulfillment.actual_variant",
                        "The delivered variant differs from the expected ordered variant.",
                        expected=fulfillment.expected_variant,
                        actual=fulfillment.actual_variant,
                    ))
                    return IncidentResult(
                        incident_type=IncidentType.WRONG_ITEM_OR_VARIANT,
                        signals=signals,
                    )

                if fulfillment.expected_quantity is not None and fulfillment.actual_quantity is not None and fulfillment.actual_quantity != fulfillment.expected_quantity:
                    signals.append(_signal(
                        "fulfillment.actual_quantity",
                        "The fulfilled quantity differs from the ordered quantity.",
                        expected=fulfillment.expected_quantity,
                        actual=fulfillment.actual_quantity,
                    ))
                    return IncidentResult(
                        incident_type=IncidentType.FULFILLMENT_ERROR,
                        signals=signals,
                    )

            if fulfillment.delivered is True and fulfillment.defect_reported is True:
                signals.append(_signal(
                    "fulfillment.defect_reported",
                    "The fulfillment record states that the delivered product was reported defective.",
                    expected=False,
                    actual=True,
                ))
                return IncidentResult(
                    incident_type=IncidentType.PRODUCT_DEFECT,
                    signals=signals,
                )

            if fulfillment.actual_item_id and txn.agent_decision.selected_item_id and fulfillment.actual_item_id != txn.agent_decision.selected_item_id:
                signals.append(_signal(
                    "fulfillment.actual_item_id",
                    "The item delivered has a different recorded item ID from the item selected for purchase.",
                    expected=txn.agent_decision.selected_item_id,
                    actual=fulfillment.actual_item_id,
                ))
                return IncidentResult(
                    incident_type=IncidentType.WRONG_ITEM_OR_VARIANT,
                    signals=signals,
                )

        if refund:
            if refund.return_accepted is True:
                expected = refund.refund_expected
                received = refund.refund_received
                if expected is not None and (received is None or received < expected):
                    signals.append(_signal(
                        "refund.refund_received",
                        "A return was accepted but the recorded refund received is below the expected amount.",
                        expected=expected,
                        actual=received,
                    ))
                    return IncidentResult(
                        incident_type=IncidentType.RETURN_REFUND_FAILURE,
                        signals=signals,
                    )

    # Existing transaction structure can still identify common incidents.
    if txn.merchant_snapshot.price is not None and txn.merchant_snapshot.price_at_checkout is not None:
        if txn.merchant_snapshot.price != txn.merchant_snapshot.price_at_checkout:
            signals.append(_signal(
                "merchant_snapshot.price_at_checkout",
                "The recorded checkout price differs from the recorded listing price.",
                expected=txn.merchant_snapshot.price,
                actual=txn.merchant_snapshot.price_at_checkout,
            ))
            harm = max(float(txn.merchant_snapshot.price_at_checkout) - float(txn.merchant_snapshot.price), 0.0)
            return IncidentResult(
                incident_type=IncidentType.INCORRECT_AMOUNT,
                signals=signals,
                economic_harm=harm,
                harm_currency="USD",
                recorded_responsibility=ResponsibilityActor.MERCHANT,
                responsibility_evidence="The transaction record explicitly shows a listing-to-checkout price mismatch.",
            )

    if txn.merchant_snapshot.seller and txn.merchant_snapshot.seller_at_checkout:
        if txn.merchant_snapshot.seller != txn.merchant_snapshot.seller_at_checkout:
            signals.append(_signal(
                "merchant_snapshot.seller_at_checkout",
                "The seller recorded at checkout differs from the seller shown during selection.",
                expected=txn.merchant_snapshot.seller,
                actual=txn.merchant_snapshot.seller_at_checkout,
            ))
            return IncidentResult(
                incident_type=IncidentType.WRONG_MERCHANT_OR_PAYEE,
                signals=signals,
            )

    return IncidentResult(incident_type=IncidentType.NORMAL_PURCHASE, signals=[])
