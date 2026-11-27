"""Tracker->FW OUTCOME / TARGET series REQUEST -> RETURN caller (H3 owner path; generic, candidate). A request is accepted only for an FW consumer binding for which THIS Gateway already issued an FW window outcome (the consumer binding id comes from the issued identity and must equal the package's CONSUMER_BINDING_ID);
the return is the H3 structural decision (`gateway.outcome_series.evaluate`), recorded IMMUTABLY per (request id): a retry with the same package returns the STORED return and never re-evaluates (a later context cannot flip it), a different package under the same request id refuses.
`delivered` is ALWAYS False: H3 authorization inputs (authorized segments, sealed regions, unseal resolver, applicability, boundary convention) are caller-supplied UNADMITTED, and the real per-field instances (SEGMENT_REF, KNOWABLE_AT, ADMISSIBILITY_STATE derivations) are held (`HELD_FIELDS`, the exact descriptor-binding statuses). Nothing here releases data, appoints an owner or is a Gateway delivery."""
from dataclasses import dataclass
from ..errors import Refusal
from ..gateway import outcome_series as H
from ..gateway.contracts import Binding
HELD_FIELDS = ("SEGMENT_REF", "KNOWABLE_AT", "ADMISSIBILITY_STATE")
@dataclass(frozen=True)
class OutcomeReturn:
    request_id: str; consumer_binding_id: str; series_id: str; outcome_package_hash: str; decision: H.H3Decision; delivered: bool = False; held_fields: tuple = HELD_FIELDS
class OutcomeSeriesDesk:
    def __init__(self, gateway): self._g = gateway; self._r = {}
    def request(self, request_id, pkg, ctx, *, identity):
        if not isinstance(pkg, H.OutcomeSeriesPackage) or not isinstance(request_id, str) or not request_id: raise Refusal("request", code="OUTCOME_REQUEST_MALFORMED")
        fs = getattr(self._g, "final_store", None)
        if fs is None: raise Refusal("final store", code="OUTCOME_REQUEST_NO_WINDOW_STORE")
        if fs.identity_of("FW", request_id) != identity or getattr(identity, "consumer_id", None) != "FW": raise Refusal(request_id, code="OUTCOME_REQUEST_NOT_ISSUED_TO_FW_WINDOW")
        if identity.manifest_or_dataset_binding_id != pkg.consumer_binding_id: raise Refusal(request_id, code="OUTCOME_REQUEST_BINDING_ID_DIFFERS_FROM_ISSUED_IDENTITY")
        issued = self._g.outcome(request_id, "FW")
        if not isinstance(issued, Binding): raise Refusal(request_id, code="OUTCOME_REQUEST_WINDOW_OUTCOME_NOT_A_BINDING")        # a non-delivery window outcome can never carry an outcome series
        old = self._r.get(request_id)
        if old is not None:
            if old[0] != pkg: raise Refusal(request_id, code="OUTCOME_REQUEST_IMMUTABLE")
            return old[1]
        out = OutcomeReturn(request_id, pkg.consumer_binding_id, pkg.series_id, pkg.outcome_package_hash, H.evaluate(pkg, ctx))
        self._r[request_id] = (pkg, out); return out
    def return_for(self, request_id): e = self._r.get(request_id); return None if e is None else e[1]
