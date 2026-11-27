"""Tracker-owned FW request / outcome / return ASSOCIATION (Contract V0.38 FINAL RESOLUTION IDENTITY: REQUEST_ID maps many-to-one onto the immutable resolution identity; H1 REQUEST_ID is consumer-local; Build Plan 12-13 FW returns Evidence, Request, Lineage only).
This is a GENERIC association ledger over the ONE `FinalResolutionStore`; it is not an FW<->Tracker consumer schema and not a Gateway. Facts it enforces:
  * a request is associated only with an identity the store itself already bound for (consumer 'FW', request_id) and whose stored outcome exists (the association never evaluates, never mints or alters an outcome);
  * a return refers to an associated request, has a permitted class, is immutable per return_id (identical retry idempotent, different content refused), and a LINEAGE return carries a non-empty lineage reference;
  * the RETURN PAYLOAD FIELDS are UNBOUND in every source read (mapping A04: payload bindings null): `payload_binding` is always HELD `FW_RETURN_PAYLOAD_FIELDS_UNBOUND`, no payload is parsed or trusted;
  * a later return never rewrites the earlier outcome or earlier returns (append-only; correction-after-bind is a later record, not a mutation).
Nothing here is qualified: the store is a single-process in-memory object (D10)."""
from dataclasses import dataclass
from typing import Optional
from ..errors import Refusal
from .return_lineage import check_fw_return_classes, RETURN_CLASSES
HELD_PAYLOAD = "FW_RETURN_PAYLOAD_FIELDS_UNBOUND"
FW = "FW"
def _s(x): return isinstance(x, str) and bool(x)

@dataclass(frozen=True)
class FwReturn:
    return_id: str; request_id: str; resolution_identity: object; return_class: str; lineage_ref: Optional[str]; seq: int
    payload_binding: str = HELD_PAYLOAD

class FwAssociation:
    def __init__(self, store):
        self._store = store; self._returns = {}; self._order = []
    def associate_request(self, request_id, identity):
        """Returns the stored outcome for the identity. Refuses unless the store itself bound (FW, request_id) -> identity and holds an outcome."""
        if not _s(request_id) or getattr(identity, "consumer_id", None) != FW: raise Refusal("request", code="FW_ASSOCIATION_NOT_AN_FW_REQUEST")
        if self._store.identity_of(FW, request_id) != identity: raise Refusal(request_id, code="FW_REQUEST_NOT_BOUND_TO_IDENTITY_BY_STORE")
        out = self._store.outcome_for(identity)
        if out is None: raise Refusal(request_id, code="FW_REQUEST_HAS_NO_STORED_OUTCOME")
        return out
    def record_return(self, return_id, request_id, return_class, lineage_ref=None, payload=None):
        if payload is not None: raise Refusal(HELD_PAYLOAD, code="FW_RETURN_PAYLOAD_NOT_ACCEPTED_UNBOUND")        # no source defines the fields: nothing is parsed or stored
        if not _s(return_id) or not _s(request_id): raise Refusal("ids", code="FW_RETURN_ID_INVALID")
        check_fw_return_classes([return_class])
        ident = self._store.identity_of(FW, request_id)
        if ident is None or self._store.outcome_for(ident) is None: raise Refusal(request_id, code="FW_RETURN_FOR_UNASSOCIATED_REQUEST")
        if return_class == "LINEAGE" and not _s(lineage_ref): raise Refusal(return_id, code="FW_LINEAGE_RETURN_WITHOUT_LINEAGE_REF")
        if return_class != "LINEAGE" and lineage_ref is not None: raise Refusal(return_id, code="FW_LINEAGE_REF_ON_NON_LINEAGE_RETURN")
        old = self._returns.get(return_id)
        if old is not None:
            if (old.request_id, old.return_class, old.lineage_ref) != (request_id, return_class, lineage_ref): raise Refusal(return_id, code="FW_RETURN_IMMUTABLE")
            return old
        r = FwReturn(return_id, request_id, ident, return_class, lineage_ref, len(self._order) + 1); self._returns[return_id] = r; self._order.append(return_id); return r
    def returns_for(self, identity): return tuple(self._returns[i] for i in self._order if self._returns[i].resolution_identity == identity)
    def has_lineage_return(self, identity, lineage_ref): return any(r.return_class == "LINEAGE" and r.lineage_ref == lineage_ref for r in self.returns_for(identity))
