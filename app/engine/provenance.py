"""Evidence provenance verification utilities."""

from __future__ import annotations

import hashlib
import json
from typing import Any, Dict, List, Tuple


def canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)


def content_hash(value: Any, parent_hash: str | None = None) -> str:
    body = {"payload": value, "parent_hash": parent_hash}
    return hashlib.sha256(canonical_json(body).encode("utf-8")).hexdigest()


def verify_event_chain(event_log: List[Dict[str, Any]]) -> Tuple[str, List[str]]:
    """Verify a supplied hash chain when hashes exist; legacy logs remain UNVERIFIED."""
    previous = None
    missing: List[str] = []
    for event in event_log:
        event_id = str(event.get("event_id", "unknown"))
        supplied = event.get("content_hash")
        if not supplied:
            missing.append(event_id)
            previous = supplied or previous
            continue
        payload = dict(event)
        payload.pop("content_hash", None)
        payload.pop("parent_hash", None)
        expected = content_hash(payload, event.get("parent_hash"))
        if expected != supplied:
            return "INVALID", [event_id]
        if event.get("parent_hash") != previous:
            return "INVALID", [event_id]
        previous = supplied
    return ("VERIFIED" if event_log and not missing else "UNVERIFIED", missing)
