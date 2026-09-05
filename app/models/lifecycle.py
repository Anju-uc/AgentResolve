"""Optional transaction lifecycle evidence for real-world AgentResolve cases."""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class AuthorizationRecord(BaseModel):
    """Evidence about user consent and the scope the agent was authorized to use."""

    user_authorized: Optional[bool] = None
    initiated_by_agent: Optional[bool] = None
    consent_recorded: Optional[bool] = None
    authorization_scope: Optional[str] = None
    authorization_limit: Optional[float] = None
    authorized_amount: Optional[float] = None
    currency: Optional[str] = None
    final_cart_approved: Optional[bool] = None
    timestamp: Optional[str] = None


class PaymentRecord(BaseModel):
    """Payment processor state needed for payment and amount incidents."""

    status: Optional[str] = None
    payment_attempt_id: Optional[str] = None
    authorized_amount: Optional[float] = None
    captured_amount: Optional[float] = None
    refunded_amount: Optional[float] = None
    currency: Optional[str] = None
    error_code: Optional[str] = None
    gateway_message: Optional[str] = None
    duplicate_detected: Optional[bool] = None
    timestamp: Optional[str] = None


class FulfillmentRecord(BaseModel):
    """Evidence for shipment, delivery, received item, and defect cases."""

    order_status: Optional[str] = None
    shipment_status: Optional[str] = None
    tracking_id: Optional[str] = None
    promised_delivery_timestamp: Optional[str] = None
    actual_delivery_timestamp: Optional[str] = None
    delivered: Optional[bool] = None
    shipped: Optional[bool] = None
    actual_item_id: Optional[str] = None
    actual_variant: Optional[str] = None
    expected_variant: Optional[str] = None
    expected_quantity: Optional[int] = None
    actual_quantity: Optional[int] = None
    condition_at_delivery: Optional[str] = None
    defect_reported: Optional[bool] = None
    defect_description: Optional[str] = None
    delay_cause: Optional[str] = None
    responsible_party: Optional[str] = None


class RefundRecord(BaseModel):
    """Evidence for return and refund processing."""

    return_requested: Optional[bool] = None
    return_accepted: Optional[bool] = None
    refund_expected: Optional[float] = None
    refund_received: Optional[float] = None
    refund_status: Optional[str] = None
    currency: Optional[str] = None
    requested_timestamp: Optional[str] = None
    completed_timestamp: Optional[str] = None


class InventoryRecord(BaseModel):
    """Evidence for stock changes between product selection and checkout."""

    available_at_selection: Optional[bool] = None
    available_at_checkout: Optional[bool] = None
    selection_timestamp: Optional[str] = None
    checkout_timestamp: Optional[str] = None
    recorded_change_reason: Optional[str] = None


class CommercialAdjustmentRecord(BaseModel):
    """Evidence for taxes, fees and promotion/coupon changes."""

    listing_subtotal: Optional[float] = None
    checkout_subtotal: Optional[float] = None
    tax_amount: Optional[float] = None
    fee_amount: Optional[float] = None
    total_amount: Optional[float] = None
    authorized_total: Optional[float] = None
    currency: Optional[str] = None
    promotion_code: Optional[str] = None
    promotion_expected_discount: Optional[float] = None
    promotion_applied_discount: Optional[float] = None
    promotion_status: Optional[str] = None
    disclosed_fees_before_authorization: Optional[bool] = None


class IntegrationRecord(BaseModel):
    """Evidence for agent-to-merchant/API translation failures."""

    agent_order_item_id: Optional[str] = None
    merchant_recorded_item_id: Optional[str] = None
    agent_quantity: Optional[int] = None
    merchant_recorded_quantity: Optional[int] = None
    request_payload_hash: Optional[str] = None
    merchant_payload_hash: Optional[str] = None
    mismatch_detected: Optional[bool] = None
    error_code: Optional[str] = None
    error_message: Optional[str] = None


class TransactionLifecycle(BaseModel):
    """Optional lifecycle evidence; existing benchmark transactions remain valid."""

    authorization: Optional[AuthorizationRecord] = None
    payment: Optional[PaymentRecord] = None
    fulfillment: Optional[FulfillmentRecord] = None
    refund: Optional[RefundRecord] = None
    inventory: Optional[InventoryRecord] = None
    commercial: Optional[CommercialAdjustmentRecord] = None
    integration: Optional[IntegrationRecord] = None
    event_log: List[Dict[str, Any]] = Field(default_factory=list)
