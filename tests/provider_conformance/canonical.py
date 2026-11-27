"""Deterministic encoding and hashing for harness records.

Frozen rule (Build Plan E-02): no pickle, no Python repr, no unordered JSON in
a governed hash domain. These bytes are HARNESS record bytes, not governed
artifact bytes: the harness never claims to produce canonical Stage A
artifacts.
"""
from __future__ import annotations

import hashlib
import json
from typing import Any

CANONICAL_ENCODING_ID = "SALIX-E01-CONFORMANCE-RECORD-V1"
HASH_ALGORITHM_ID = "sha256"


def canonical_bytes(payload: Any) -> bytes:
    """Sorted-key, tight-separator, ASCII-escaped UTF-8 JSON."""
    return json.dumps(
        payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True,
        allow_nan=False,
    ).encode("utf-8")


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def hash_payload(payload: Any) -> str:
    return sha256_hex(canonical_bytes(payload))
