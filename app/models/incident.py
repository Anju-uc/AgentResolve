"""Incident and operational failure models for AgentResolve v2."""

from enum import Enum
from typing import Any, List, Optional
from pydantic import BaseModel, Field


class IncidentType(str, Enum):
    """Operational incident classes. These are not fault categories."""

    NORMAL_PURCHASE = "NORMAL_PURCHASE"
    UNAUTHORIZED_TRANSACTION = "UNAUTHORIZED_TRANSACTION"
    INCORRECT_AMOUNT = "INCORRECT_AMOUNT"
    WRONG_MERCHANT_OR_PAYEE = "WRONG_MERCHANT_OR_PAYEE"
    WRONG_ITEM_OR_VARIANT = "WRONG_ITEM_OR_VARIANT"
    NON_DELIVERY = "NON_DELIVERY"
    FULFILLMENT_ERROR = "FULFILLMENT_ERROR"
    PRODUCT_DEFECT = "PRODUCT_DEFECT"
    RETURN_REFUND_FAILURE = "RETURN_REFUND_FAILURE"
    PAYMENT_PROCESSING_FAILURE = "PAYMENT_PROCESSING_FAILURE"
    AUTHORIZATION_SCOPE_AMBIGUITY = "AUTHORIZATION_SCOPE_AMBIGUITY"
    AUTHORIZATION_SCOPE_VIOLATION = "AUTHORIZATION_SCOPE_VIOLATION"
    INVENTORY_RACE = "INVENTORY_RACE"
    FEE_TAX_SURPRISE = "FEE_TAX_SURPRISE"
    PROMOTION_FAILURE = "PROMOTION_FAILURE"
    DUPLICATE_CHARGE = "DUPLICATE_CHARGE"
    SYSTEM_INTEGRATION_FAILURE = "SYSTEM_INTEGRATION_FAILURE"


class ResponsibilityActor(str, Enum):
    """Recorded operational actor. This is not a legal liability finding."""

    USER = "USER"
    AGENT = "AGENT"
    MERCHANT = "MERCHANT"
    PAYMENT_SYSTEM = "PAYMENT_SYSTEM"
    EXTERNAL_SYSTEM = "EXTERNAL_SYSTEM"
    UNKNOWN = "UNKNOWN"


class IncidentSignal(BaseModel):
    """One inspectable signal that supports an incident classification."""

    field: str
    statement: str
    expected_value: Optional[Any] = None
    actual_value: Optional[Any] = None


class IncidentResult(BaseModel):
    """Structured incident classification separate from the six fault rules."""

    incident_type: IncidentType = IncidentType.NORMAL_PURCHASE
    status: str = "IDENTIFIED"
    signals: List[IncidentSignal] = Field(default_factory=list)
    related_incidents: List[IncidentType] = Field(default_factory=list)
    recorded_responsibility: ResponsibilityActor = ResponsibilityActor.UNKNOWN
    responsibility_evidence: Optional[str] = None
    economic_harm: Optional[float] = None
    harm_currency: Optional[str] = None
