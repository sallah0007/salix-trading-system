"""R37: H1 CONSUMER_BINDING_ID (package field, H3 p288) and MANIFEST_OR_DATASET_BINDING_ID (final-resolution identity field, p54/p250) are DISTINCT fields (Contract 1neiQsQ9AG... H1 p231/p250); they are NEVER compared as if equal. The Gateway entry carries no H1 CONSUMER_BINDING_ID, so the relation is an EXPLICIT SUPPLIED
`ConsumerBindingRecord` (CBID -> consumer, request id, manifest/dataset binding id) registered against the identity this Gateway's final store actually issued; with no record the request is HELD (`OUTCOME_REQUEST_CONSUMER_BINDING_NOT_CORRELATED`). The record's source (the H1 issuer) is unadmitted: nothing here issues a CBID.
Tracker->FW OUTCOME / TARGET series REQUEST -> RETURN caller (H3 owner path; generic, candidate). A request is accepted only for an FW consumer binding for which THIS Gateway already issued an FW window outcome (the consumer binding id comes from the issued identity and must equal the package's CONSUMER_BINDING_ID);
the return is the H3 structural decision (`gateway.outcome_series.evaluate`), recorded IMMUTABLY per (request id): a retry with the same package returns the STORED return and never re-evaluates (a later context cannot flip it), a different package under the same request id refuses.
`delivered` is ALWAYS False: H3 authorization inputs (authorized segments, sealed regions, unseal resolver, applicability, boundary convention) are caller-supplied UNADMITTED, and the real per-field instances (SEGMENT_REF, KNOWABLE_AT, ADMISSIBILITY_STATE derivations) are held (`HELD_FIELDS`, the exact descriptor-binding statuses). Nothing here releases data, appoints an owner or is a Gateway delivery."""
from dataclasses import dataclass
from ..errors import Refusal
from ..gateway import outcome_series as H
from ..gateway.contracts import Binding
HELD_FIELDS = ("SEGMENT_REF", "KNOWABLE_AT", "ADMISSIBILITY_STATE")
@dataclass(frozen=True)
class ConsumerBindingRecord:
    consumer_binding_id: str; consumer_id: str; request_id: str; manifest_or_dataset_binding_id: str
@dataclass(frozen=True)
class OutcomeReturn:
    request_id: str; consumer_binding_id: str; series_id: str; outcome_package_hash: str; decision: H.H3Decision; delivered: bool = False; held_fields: tuple = HELD_FIELDS
class OutcomeSeriesDesk:
    def __init__(self, gateway): self._g = gateway; self._r = {}; self._cb = {}; self._by_req = {}
    def register_consumer_binding(self, rec, *, identity):
        """Correlate an H1 CONSUMER_BINDING_ID with the identity (and its MANIFEST_OR_DATASET_BINDING_ID) this Gateway's final store issued for an FW window request. Immutable per CBID and per (consumer, request): a foreign CBID, a different request, or a different manifest binding id refuses; an identical retry is idempotent."""
        fs = getattr(self._g, "final_store", None)
        if not (isinstance(rec, ConsumerBindingRecord) and all(isinstance(x, str) and x for x in (rec.consumer_binding_id, rec.consumer_id, rec.request_id, rec.manifest_or_dataset_binding_id))): raise Refusal("record", code="CONSUMER_BINDING_RECORD_MALFORMED")
        if fs is None or rec.consumer_id != "FW" or fs.identity_of("FW", rec.request_id) != identity or getattr(identity, "consumer_id", None) != "FW" or identity.manifest_or_dataset_binding_id != rec.manifest_or_dataset_binding_id: raise Refusal(rec.consumer_binding_id, code="CONSUMER_BINDING_NOT_THE_ISSUED_WINDOW_IDENTITY")
        old = self._cb.get(rec.consumer_binding_id)
        if old is not None and old != rec: raise Refusal(rec.consumer_binding_id, code="CONSUMER_BINDING_IMMUTABLE")
        other = self._by_req.get(rec.request_id)
        if other is not None and other != rec.consumer_binding_id: raise Refusal(rec.request_id, code="CONSUMER_BINDING_REQUEST_ALREADY_CORRELATED")
        self._cb[rec.consumer_binding_id] = rec; self._by_req[rec.request_id] = rec.consumer_binding_id; return rec
    def request(self, request_id, pkg, ctx, *, identity):
        if not isinstance(pkg, H.OutcomeSeriesPackage) or not isinstance(request_id, str) or not request_id: raise Refusal("request", code="OUTCOME_REQUEST_MALFORMED")
        fs = getattr(self._g, "final_store", None)
        if fs is None: raise Refusal("final store", code="OUTCOME_REQUEST_NO_WINDOW_STORE")
        if fs.identity_of("FW", request_id) != identity or getattr(identity, "consumer_id", None) != "FW": raise Refusal(request_id, code="OUTCOME_REQUEST_NOT_ISSUED_TO_FW_WINDOW")
        rec = self._cb.get(pkg.consumer_binding_id)
        if rec is None: raise Refusal(str(pkg.consumer_binding_id), code="OUTCOME_REQUEST_CONSUMER_BINDING_NOT_CORRELATED")           # HELD: no H1 CBID relation supplied (never derived from the manifest binding id)
        if rec.request_id != request_id or rec.consumer_id != "FW" or rec.manifest_or_dataset_binding_id != identity.manifest_or_dataset_binding_id: raise Refusal(request_id, code="OUTCOME_REQUEST_CONSUMER_BINDING_FOR_DIFFERENT_WINDOW")
        issued = self._g.outcome(request_id, "FW")
        if not isinstance(issued, Binding): raise Refusal(request_id, code="OUTCOME_REQUEST_WINDOW_OUTCOME_NOT_A_BINDING")        # a non-delivery window outcome can never carry an outcome series
        old = self._r.get(request_id)
        if old is not None:
            if old[0] != pkg: raise Refusal(request_id, code="OUTCOME_REQUEST_IMMUTABLE")
            return old[1]
        out = OutcomeReturn(request_id, pkg.consumer_binding_id, pkg.series_id, pkg.outcome_package_hash, H.evaluate(pkg, ctx))
        self._r[request_id] = (pkg, out); return out
    def return_for(self, request_id): e = self._r.get(request_id); return None if e is None else e[1]
