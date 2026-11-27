from dataclasses import dataclass
from typing import FrozenSet, Optional

ORDER_ISSUED = "ORDER_ISSUED"
ORDER_REVOKED = "ORDER_REVOKED"
CLAIM_BOUND = "CLAIM_BOUND"
CLAIM_CONSUMED = "CLAIM_CONSUMED"
CLAIM_RELEASED = "CLAIM_RELEASED"
KINDS = frozenset({ORDER_ISSUED, ORDER_REVOKED, CLAIM_BOUND, CLAIM_CONSUMED, CLAIM_RELEASED})

@dataclass(frozen=True)
class ConstructionOrder:
    order_id: str
    subject_key: str
    source_binding_hash: str
    issued_by: str
    valid_until_seq: Optional[int] = None

    def to_body(self) -> dict:
        return {"order_id": self.order_id, "subject_key": self.subject_key,
                "source_binding_hash": self.source_binding_hash,
                "issued_by": self.issued_by, "valid_until_seq": self.valid_until_seq}

    @staticmethod
    def from_body(b: dict) -> "ConstructionOrder":
        return ConstructionOrder(b["order_id"], b["subject_key"], b["source_binding_hash"],
                                 b["issued_by"], b.get("valid_until_seq"))

@dataclass(frozen=True)
class TrustAnchor:
    """Deployment-time trust root. Open decision: its source is an accepted role record."""
    issuer_ids: FrozenSet[str]
    source_binding_hash: str
