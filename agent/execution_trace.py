"""Deterministic execution-trace helpers for the shopping-agent simulator."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List, Optional

from app.models.forensics import AgentExecutionEvent


def _canonical(payload: Dict[str, Any]) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)


def hash_event(payload: Dict[str, Any], parent_hash: Optional[str] = None) -> str:
    body = {"payload": payload, "parent_hash": parent_hash}
    return hashlib.sha256(_canonical(body).encode("utf-8")).hexdigest()


def build_event(
    event_id: str,
    action: str,
    arguments: Optional[Dict[str, Any]] = None,
    result: Optional[Dict[str, Any]] = None,
    tool: Optional[str] = None,
    timestamp: Optional[str] = None,
    status: str = "RECORDED",
    parent_hash: Optional[str] = None,
) -> AgentExecutionEvent:
    arguments = arguments or {}
    result = result or {}
    timestamp = timestamp or datetime.now(timezone.utc).isoformat()
    payload = {
        "event_id": event_id,
        "timestamp": timestamp,
        "action": action,
        "tool": tool,
        "arguments": arguments,
        "result": result,
        "status": status,
    }
    return AgentExecutionEvent(
        **payload,
        content_hash=hash_event(payload, parent_hash),
        parent_hash=parent_hash,
    )


def derive_validated_fields(events: Iterable[AgentExecutionEvent]) -> List[str]:
    """Derive validations from recorded execution actions, never from labels."""
    fields: List[str] = []
    for event in events:
        action = event.action.lower().replace("-", "_")
        field = event.arguments.get("field") or event.result.get("field")
        if field and ("validat" in action or action in {"constraint_check", "checkout_validation"}):
            if field not in fields:
                fields.append(str(field))
    return fields
