"""
Transaction Models module for AgentResolve.

This module defines Pydantic v2 domain schemas representing the complete log
of an agent-assisted e-commerce purchase lifecycle, including user request,
agent interpretation, merchant snapshots, agent decisions, and disputes.

RULE REMINDER: Preserve `None` as 'not specified'. Do NOT set arbitrary defaults
for missing numerical or text constraints. Missing fields trigger INSUFFICIENT_EVIDENCE.
"""

from typing import Dict, List, Optional, Any, Union
from pydantic import BaseModel, Field
from app.models.lifecycle import TransactionLifecycle
from app.models.forensics import AgentExecutionEvent, AttributeEvidence


class Constraints(BaseModel):
    """
    Represents technical or commercial constraints specified by a user or interpreted by an agent.
    All fields are Optional to preserve exact specification semantics (None = not specified).
    """
    ram_gb: Optional[float] = Field(
        default=None,
        description="RAM requirement in GB (e.g. 16.0). None if not specified."
    )
    ram_gb_operator: Optional[str] = Field(
        default="minimum",
        description="Comparison operator for RAM: 'under', 'at most', 'minimum', 'exactly'."
    )
    
    price_usd: Optional[float] = Field(
        default=None,
        description="Price budget limit in USD. None if not specified."
    )
    price_usd_operator: Optional[str] = Field(
        default="at most",
        description="Comparison operator for price: 'under', 'at most', 'minimum', 'exactly'."
    )
    
    seller: Optional[str] = Field(
        default=None,
        description="Required seller or merchant identifier (e.g. 'OfficialStore')."
    )
    seller_operator: Optional[str] = Field(
        default="exactly",
        description="Comparison operator for seller string."
    )
    
    delivery_days: Optional[int] = Field(
        default=None,
        description="Maximum expected delivery days. None if not specified."
    )
    delivery_days_operator: Optional[str] = Field(
        default="at most",
        description="Comparison operator for delivery days."
    )
    
    storage_gb: Optional[int] = Field(
        default=None,
        description="Storage capacity in GB (e.g. 512). None if not specified."
    )
    storage_gb_operator: Optional[str] = Field(
        default="minimum",
        description="Comparison operator for storage."
    )
    
    color: Optional[str] = Field(
        default=None,
        description="Desired color (e.g. 'Space Gray'). None if not specified."
    )
    
    condition: Optional[str] = Field(
        default=None,
        description="Desired item condition (e.g. 'New', 'Refurbished'). None if not specified."
    )
    
    custom_attributes: Dict[str, Any] = Field(
        default_factory=dict,
        description="Flexible key-value pairs for non-standard item attributes. A value may be raw or {value, operator}."
    )


class UserRequest(BaseModel):
    """
    Original request issued by the user to the autonomous agent.
    """
    raw_text: str = Field(..., description="Unmodified user natural language prompt.")
    timestamp: str = Field(..., description="ISO 8601 timestamp of request creation.")
    explicit_constraints: Constraints = Field(
        default_factory=Constraints,
        description="Parsed explicit constraints explicitly mentioned by user."
    )


class AgentInterpretation(BaseModel):
    """
    Internal state of the AI shopping agent after parsing the user request.
    """
    parsed_constraints: Constraints = Field(
        default_factory=Constraints,
        description="Constraints parsed and adopted by the agent."
    )
    accessed_constraint_keys: List[str] = Field(
        default_factory=list,
        description="Legacy summary of constraint keys used by the agent."
    )
    execution_trace: List[AgentExecutionEvent] = Field(
        default_factory=list,
        description="Recorded low-level execution events used to derive agent behavior."
    )


class MerchantSnapshot(BaseModel):
    """
    Data provided by merchant listings before selection and at checkout.
    Used to verify merchant inconsistencies or post-purchase external changes.
    """
    item_id: Optional[str] = Field(default=None, description="Merchant SKU / item identifier.")
    title: Optional[str] = Field(default=None, description="Product title listing.")
    seller: Optional[str] = Field(default=None, description="Seller name listed at product page.")
    seller_at_checkout: Optional[str] = Field(default=None, description="Seller name recorded at checkout.")
    color: Optional[str] = Field(default=None, description="Color shown on listing.")
    color_at_checkout: Optional[str] = Field(default=None, description="Color recorded at checkout.")
    color_actual: Optional[str] = Field(default=None, description="Color actually delivered.")
    
    price: Optional[float] = Field(default=None, description="Advertised listing price USD.")
    price_at_checkout: Optional[float] = Field(default=None, description="Actual price charged at checkout USD.")
    
    ram_gb: Optional[float] = Field(default=None, description="RAM listed on product page.")
    ram_gb_actual: Optional[float] = Field(default=None, description="Physical RAM delivered/verified.")
    
    storage_gb: Optional[int] = Field(default=None, description="Storage listed on product page.")
    storage_gb_actual: Optional[int] = Field(default=None, description="Physical storage delivered.")
    
    delivery_days: Optional[int] = Field(default=None, description="Advertised delivery timeframe in days.")
    delivery_days_actual: Optional[int] = Field(default=None, description="Actual delivery timeframe realized.")
    
    specs: Dict[str, Any] = Field(default_factory=dict, description="Legacy flexible item attributes.")
    attributes: Dict[str, AttributeEvidence] = Field(
        default_factory=dict,
        description="Generalized attribute evidence across request, listing, checkout, and delivery."
    )


class AgentDecision(BaseModel):
    """
    Action taken by the agent during purchase execution.
    """
    selected_item_id: Optional[str] = Field(default=None, description="Selected item ID.")
    purchased_price: Optional[float] = Field(default=None, description="Price paid by agent.")
    purchased_ram_gb: Optional[float] = Field(default=None, description="RAM spec of item purchased.")
    purchased_seller: Optional[str] = Field(default=None, description="Seller of item purchased.")
    purchased_color: Optional[str] = Field(default=None, description="Color of item purchased.")
    purchased_delivery_days: Optional[int] = Field(default=None, description="Delivery promise of item purchased.")
    validation_steps_performed: List[str] = Field(
        default_factory=list,
        description="Legacy summary of validations; lower-level execution trace is authoritative when present."
    )
    attributes: Dict[str, Any] = Field(
        default_factory=dict,
        description="Generalized agent-selected attributes."
    )


class Dispute(BaseModel):
    """
    Post-purchase claim initiated by user.
    """
    disputed_field: str = Field(
        ...,
        description="Target attribute under dispute (e.g. 'ram_gb', 'price', 'delivery_days', 'seller', 'color')."
    )
    user_claim: str = Field(..., description="User explanation of what went wrong.")
    post_purchase_preference: Optional[str] = Field(
        default=None,
        description="New preference expressed by user only after purchase completed."
    )
    dispute_timestamp: str = Field(..., description="ISO 8601 timestamp of dispute filing.")


class GroundTruth(BaseModel):
    """
    Expected outcome ground truth used for evaluation against benchmark dataset.
    """
    primary_fault: str = Field(..., description="Expected primary fault category.")
    contributing_factors: List[str] = Field(
        default_factory=list,
        description="Expected contributing fault categories."
    )
    preventability: str = Field(..., description="Expected preventability rating: HIGH, LOW, or N/A.")


class Transaction(BaseModel):
    """
    Complete root transaction record passed to the AgentResolve engine for analysis.
    """
    transaction_id: str = Field(..., description="Unique transaction ID (e.g. 'TXN_001').")
    timestamp: str = Field(..., description="ISO timestamp of transaction completion.")
    user_request: UserRequest = Field(..., description="Recorded user request details.")
    agent_interpretation: AgentInterpretation = Field(..., description="Recorded agent state details.")
    merchant_snapshot: MerchantSnapshot = Field(..., description="Recorded merchant listing snapshot.")
    agent_decision: AgentDecision = Field(..., description="Recorded agent execution details.")
    dispute: Dispute = Field(..., description="Recorded post-purchase dispute details.")
    lifecycle: Optional[TransactionLifecycle] = Field(
        default=None,
        description="Optional transaction lifecycle evidence for operational incident analysis.",
    )
    direct_financial_harm: Optional[float] = Field(
        default=None,
        description="Measured direct financial impact in transaction currency when recorded."
    )
    harm_currency: Optional[str] = Field(default=None)
    duplicate_charge: bool = Field(
        default=False,
        description="Payment flag indicating duplicate billing. Handled as data flag, NOT fault category."
    )
    ground_truth: Optional[GroundTruth] = Field(
        default=None,
        description="Optional ground truth for synthetic benchmark testing."
    )
