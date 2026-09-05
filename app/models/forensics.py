"""Forensic evidence and execution-trace models used by AgentResolve v2.3.0."""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class EvidenceProvenance(BaseModel):
    """Integrity metadata for one recorded evidence object."""

    evidence_id: Optional[str] = None
    event_id: Optional[str] = None
    source_type: Optional[str] = None
    source_reference: Optional[str] = None
    capture_method: Optional[str] = None
    timestamp: Optional[str] = None
    content_hash: Optional[str] = None
    parent_hash: Optional[str] = None
    integrity_status: str = "UNVERIFIED"


class AgentExecutionEvent(BaseModel):
    """Low-level agent execution evidence used to derive behavior."""

    event_id: str
    timestamp: str
    action: str
    tool: Optional[str] = None
    arguments: Dict[str, Any] = Field(default_factory=dict)
    result: Dict[str, Any] = Field(default_factory=dict)
    status: str = "RECORDED"
    content_hash: Optional[str] = None
    parent_hash: Optional[str] = None


class AttributeEvidence(BaseModel):
    """Generic four-stage state for an arbitrary commerce attribute."""

    constraint: Any = None
    operator: Optional[str] = None
    advertised: Any = None
    checkout: Any = None
    delivered: Any = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class DisputeDriftResult(BaseModel):
    """Deterministic supporting signal comparing original request and dispute text."""

    analyzed: bool = False
    similarity: Optional[float] = None
    new_terms: List[str] = Field(default_factory=list)
    likely_preference_drift: bool = False
    methodology: str = "token_overlap_supporting_signal"
