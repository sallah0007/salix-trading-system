from dataclasses import dataclass
from typing import FrozenSet, Optional

ORDER_ISSUED = "ORDER_ISSUED"
ORDER_REVOKED = "ORDER_REVOKED"
CLAIM_BOUND = "CLAIM_BOUND"
CLAIM_CONSUMED = "CLAIM_CONSUMED"
CLAIM_RELEASED = "CLAIM_RELEASED"
ORDER_PROVENANCE = "ORDER_PROVENANCE"
# R7 PROPOSED successor semantics (NOT ADOPTED; candidate journal kinds, no grants/principals appointed): see tracker_component/lifecycle.py
CLAIM_ABANDONED = "CLAIM_ABANDONED"
GRANT_REVOKED = "GRANT_REVOKED"
ATTEMPT_ADMITTED = "ATTEMPT_ADMITTED"
ATTEMPT_REJECTED = "ATTEMPT_REJECTED"
LINEAGE_REPLACED = "LINEAGE_REPLACED"
REVIEW_DECIDED = "REVIEW_DECIDED"
REPORT_DISPOSITION = "REPORT_DISPOSITION"
KINDS = frozenset({ORDER_ISSUED, ORDER_REVOKED, CLAIM_BOUND, CLAIM_CONSUMED, CLAIM_RELEASED, ORDER_PROVENANCE,
                   CLAIM_ABANDONED, GRANT_REVOKED, ATTEMPT_ADMITTED, ATTEMPT_REJECTED, LINEAGE_REPLACED, REVIEW_DECIDED, REPORT_DISPOSITION})

@dataclass(frozen=True)
class ConstructionOrder:
    order_id: str
    subject_key: str
    source_binding_hash: str
    issued_by: str
    valid_until_seq: Optional[int] = None
    constraints: Optional[dict] = None      # the governed order contract as stated at issue (Composer V9 s8 bindings + consumer-local fields); None = legacy order that carries no constraints

    def to_body(self) -> dict:
        return {"order_id": self.order_id, "subject_key": self.subject_key,
                "source_binding_hash": self.source_binding_hash,
                "issued_by": self.issued_by, "valid_until_seq": self.valid_until_seq,
                **({"constraints": self.constraints} if self.constraints is not None else {})}

    @staticmethod
    def from_body(b: dict) -> "ConstructionOrder":
        return ConstructionOrder(b["order_id"], b["subject_key"], b["source_binding_hash"],
                                 b["issued_by"], b.get("valid_until_seq"), b.get("constraints"))

@dataclass(frozen=True)
class TrustAnchor:
    """Deployment-time trust root. Open decision: its source is an accepted role record."""
    issuer_ids: FrozenSet[str]
    source_binding_hash: str
