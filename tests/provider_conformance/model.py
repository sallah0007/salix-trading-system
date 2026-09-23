"""HEAD and transition records, and the E-09 key layout.

Frozen HEAD contents (Build Plan §29A E-01): "each governed authority namespace
has one mutable HEAD object containing epoch, sequence, accepted transition hash
and previous-head hash".

Frozen keys (Build Plan §29A E-09):
    stage-a/v1/coordination/{namespace_id}/HEAD
    stage-a/v1/coordination/{namespace_id}/epochs/{epoch}/transitions/
        {sequence_020d}-{transition_hash}.bin
"""
from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Optional

from .canonical import canonical_bytes, hash_payload, sha256_hex

HEAD_RECORD_KIND = "SALIX_E01_HEAD_V1"
TRANSITION_RECORD_KIND = "SALIX_E01_TRANSITION_V1"

# The genesis HEAD has no predecessor. A literal sentinel is used so that
# "no previous head" is an explicit declared value and never an absent field.
NO_PREVIOUS_HEAD = "GENESIS"
NO_PREVIOUS_TRANSITION = "GENESIS"


@dataclass(frozen=True)
class HeadRecord:
    namespace_id: str
    epoch: int
    sequence: int
    accepted_transition_hash: str
    previous_head_hash: str
    accepted_at_ns: int
    kind: str = HEAD_RECORD_KIND

    def to_bytes(self) -> bytes:
        return canonical_bytes(self.as_payload())

    def as_payload(self) -> dict:
        return {
            "kind": self.kind,
            "namespace_id": self.namespace_id,
            "epoch": self.epoch,
            "sequence": self.sequence,
            "accepted_transition_hash": self.accepted_transition_hash,
            "previous_head_hash": self.previous_head_hash,
            "accepted_at_ns": self.accepted_at_ns,
        }

    def head_hash(self) -> str:
        """Content hash of this HEAD, used as the successor's previous_head_hash.

        This is the SEMANTIC chain link. It is deliberately independent of the
        provider's ETag/version, which is the STORAGE precondition. The live
        Sydney finding is precisely that the storage precondition alone does not
        enforce the semantic chain.
        """
        return sha256_hex(self.to_bytes())

    @staticmethod
    def from_bytes(data: bytes) -> "HeadRecord":
        import json
        payload = json.loads(data.decode("utf-8"))
        if payload.get("kind") != HEAD_RECORD_KIND:
            raise ValueError("HEAD_RECORD_KIND_INVALID:" + str(payload.get("kind")))
        return HeadRecord(
            namespace_id=payload["namespace_id"],
            epoch=int(payload["epoch"]),
            sequence=int(payload["sequence"]),
            accepted_transition_hash=payload["accepted_transition_hash"],
            previous_head_hash=payload["previous_head_hash"],
            accepted_at_ns=int(payload["accepted_at_ns"]),
        )


@dataclass(frozen=True)
class TransitionRecord:
    namespace_id: str
    epoch: int
    sequence: int
    previous_head_hash: str
    previous_transition_hash: str
    payload_hash: str
    accepted_at_ns: int
    transition_kind: str = "GOVERNED_TRANSITION"
    kind: str = TRANSITION_RECORD_KIND

    def as_payload(self) -> dict:
        return {
            "kind": self.kind,
            "namespace_id": self.namespace_id,
            "epoch": self.epoch,
            "sequence": self.sequence,
            "previous_head_hash": self.previous_head_hash,
            "previous_transition_hash": self.previous_transition_hash,
            "payload_hash": self.payload_hash,
            "accepted_at_ns": self.accepted_at_ns,
            "transition_kind": self.transition_kind,
        }

    def to_bytes(self) -> bytes:
        return canonical_bytes(self.as_payload())

    def transition_hash(self) -> str:
        return hash_payload(self.as_payload())

    def with_accepted_at(self, accepted_at_ns: int) -> "TransitionRecord":
        """E01-M1: a retry needs a FRESH accepted_at, which yields a fresh hash
        and therefore a fresh immutable key. The old object is never reused."""
        return replace(self, accepted_at_ns=accepted_at_ns)


def head_key(prefix: str, namespace_id: str) -> str:
    return f"{prefix}/stage-a/v1/coordination/{namespace_id}/HEAD"


def transition_key(prefix: str, namespace_id: str, epoch: int, sequence: int,
                   transition_hash: str) -> str:
    return (f"{prefix}/stage-a/v1/coordination/{namespace_id}/epochs/{epoch}"
            f"/transitions/{sequence:020d}-{transition_hash}.bin")


def transition_scan_prefix(prefix: str, namespace_id: str,
                           epoch: Optional[int] = None) -> str:
    base = f"{prefix}/stage-a/v1/coordination/{namespace_id}/epochs/"
    return base if epoch is None else f"{base}{epoch}/transitions/"
