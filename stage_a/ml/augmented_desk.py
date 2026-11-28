"""R50: ML_FW_AUGMENTED governed FW-RETURN / REBIND caller (generic candidate; Build Plan 12-13). Reuses `fw.return_lineage` (return classes; FW-derived predictive input needs lineage+rebind) and `ml.receiver.check_fw_augmented/require_verified`
(declared FW ancestry, issued Gateway binding). Adds the OWNING sequence those pieces never connected:
  1 `record_fw_return`  : an FW return is recorded IMMUTABLY per return id; only the permitted classes (EVIDENCE/REQUEST/LINEAGE), it must carry LINEAGE (a return without lineage cannot feed ML), its FW manifest must be an FW manifest of the graph, and one lineage ref belongs to one return
  2 `rebind`            : an ML manifest is accepted as ML_FW_AUGMENTED only if (a) it declares exactly that return's FW manifest as its parent, (b) the AugmentedInput's lineage ref IS the returned lineage ref, (c) the Gateway actually issued the supplied rebind Binding to ML, and (d) the rebind is not the FW return's own binding. The result is recorded immutably per ML manifest.
The FW return PAYLOAD fields and the support/uncertainty/OOD representation are held (no source defines them): refs are checked for type and identity, not content. A verified rebind is candidate evidence only; ML_STANDALONE and qualification are untouched.
R51 handoff limitation: (i) `record_fw_return` requires an ACTUALLY ISSUED FW result: the owning `OutcomeSeriesDesk` must hold an `OutcomeReturn` for the return's fw_request_id (no desk, or no issued return => refuse; a return id alone is not an issued result). (ii) A rebind proves ISSUED-BINDING provenance only, so its association with a reverse-H1 / dataset-manifest identity starts HELD
(`association = "HELD"`); `associate` upgrades it to BOUND only on an explicit supplied mapping: a TypedH1 ML record whose REQUEST_ID is the rebind request, whose MANIFEST_OR_DATASET_BINDING_ID equals the identity the Gateway final store ACTUALLY issued to (ML, that request). CBID and MANIFEST_OR_DATASET_BINDING_ID stay distinct and are never forced equal. BOUND is request/consumer/mapping correlation of reference-carrier objects, NOT actual FW10/H3/native ML delivery."""
import dataclasses
from dataclasses import dataclass
from ..errors import Refusal
from ..schema.encoding import Ref
from ..fw.return_lineage import check_fw_return_classes, check_ml_input_origin
from . import receiver as R


@dataclass(frozen=True)
class FWReturnRecord:
    return_id: str; fw_request_id: str; fw_manifest_id: str; classes: tuple; lineage_ref: Ref
    def __post_init__(self):
        if not (all(isinstance(x, str) and x for x in (self.return_id, self.fw_request_id, self.fw_manifest_id)) and isinstance(self.classes, tuple) and isinstance(self.lineage_ref, Ref)): raise Refusal("return", code="FW_RETURN_RECORD_MALFORMED")


@dataclass(frozen=True)
class AugmentedBinding:
    manifest_id: str; return_id: str; rebind_request_id: str; lane: str; verified: bool = True
    association: str = "HELD"; consumer_binding_id: object = None; manifest_or_dataset_binding_id: object = None


class AugmentedDesk:
    def __init__(self, gateway, graph, outcome_desk=None):
        if gateway is None or not isinstance(graph, dict): raise Refusal("desk", code="AUGMENTED_DESK_PART_MISSING")
        self._g, self._graph, self._od, self._ret, self._lin, self._done = gateway, graph, outcome_desk, {}, {}, {}
    def record_fw_return(self, ret):
        if not isinstance(ret, FWReturnRecord): raise Refusal(type(ret).__name__, code="FW_RETURN_RECORD_MALFORMED")
        check_fw_return_classes(ret.classes)
        if self._od is None: raise Refusal(ret.return_id, code="FW_RESULT_SOURCE_HELD")                                  # no owning FW outcome desk: an issued FW result cannot be established
        from ..fw.outcome_desk import OutcomeReturn
        if not isinstance(self._od.return_for(ret.fw_request_id), OutcomeReturn): raise Refusal(ret.fw_request_id, code="FW_RETURN_NOT_AN_ISSUED_FW_RESULT")
        if "LINEAGE" not in ret.classes: raise Refusal(ret.return_id, code="FW_RETURN_HAS_NO_LINEAGE")
        fw = self._graph.get(ret.fw_manifest_id)
        if fw is None or fw.kind != "FW": raise Refusal(ret.fw_manifest_id, code="FW_RETURN_MANIFEST_NOT_AN_FW_MANIFEST")
        old = self._ret.get(ret.return_id)
        if old is not None:
            if old != ret: raise Refusal(ret.return_id, code="FW_RETURN_IMMUTABLE")
            return old
        if self._lin.get(ret.lineage_ref, ret.return_id) != ret.return_id: raise Refusal(ret.return_id, code="FW_RETURN_LINEAGE_ALREADY_RETURNED_BY_ANOTHER")
        self._ret[ret.return_id] = ret; self._lin[ret.lineage_ref] = ret.return_id; return ret
    def rebind(self, m, aug, target, *, return_id, fw_derived_predictive=True):
        check_ml_input_origin(fw_derived_predictive, aug)                           # FW-derived predictive input with no lineage+rebind refuses before anything else
        ret = self._ret.get(return_id)
        if ret is None: raise Refusal(str(return_id), code="FW_RETURN_UNKNOWN")
        if getattr(m, "derived_from", None) != ret.fw_manifest_id: raise Refusal(str(getattr(m, "derived_from", None)), code="AUGMENTED_RETURN_FOR_DIFFERENT_FW_MANIFEST")
        if not isinstance(aug, R.AugmentedInput) or aug.fw_lineage_ref != ret.lineage_ref: raise Refusal(return_id, code="AUGMENTED_LINEAGE_NOT_THE_RETURNED_ONE")
        if aug.gateway_rebind is self._g.outcome(ret.fw_request_id, "FW"): raise Refusal(ret.fw_request_id, code="AUGMENTED_REBIND_IS_THE_FW_BINDING")      # R52: the ACTUAL issued FW Binding object reused as the ML rebind; request ids are consumer-local, so equal strings prove nothing
        lane = R.require_verified(R.check_fw_augmented(m, aug, target, self._graph, gateway=self._g))
        out = AugmentedBinding(m.manifest_id, return_id, aug.gateway_rebind.request_id, lane)
        old = self._done.get(m.manifest_id)
        if old is not None:
            if dataclasses.replace(old, association="HELD", consumer_binding_id=None, manifest_or_dataset_binding_id=None) != out: raise Refusal(m.manifest_id, code="AUGMENTED_REBIND_IMMUTABLE")
            return old                                                                                                       # an exact replay returns the stored record (a BOUND association is never reset to HELD)
        self._done[m.manifest_id] = out; return out
    def associate(self, manifest_id, h1, identity):
        """HELD -> BOUND for an already verified rebind, only through an explicit supplied reverse-H1 mapping checked against what the Gateway final store actually issued. Idempotent; a different mapping for a BOUND rebind refuses; any failed check leaves the association HELD."""
        from ..gateway.h1_record import TypedH1
        cur = self._done.get(manifest_id)
        if cur is None: raise Refusal(str(manifest_id), code="AUGMENTED_REBIND_UNKNOWN")
        if not isinstance(h1, TypedH1): raise Refusal(type(h1).__name__, code="H1_RECORD_NOT_TYPED")
        f = h1.fields
        if f["CONSUMER_ID"] != "ML" or not h1.is_ml: raise Refusal(f["CONSUMER_ID"], code="ASSOCIATION_H1_NOT_AN_ML_RECORD")
        if f["REQUEST_ID"] != cur.rebind_request_id: raise Refusal(f["REQUEST_ID"], code="ASSOCIATION_H1_REQUEST_NOT_THE_REBIND_REQUEST")
        fs = getattr(self._g, "final_store", None)
        if fs is None or getattr(identity, "consumer_id", None) != "ML" or fs.identity_of("ML", cur.rebind_request_id) != identity: raise Refusal(cur.rebind_request_id, code="ASSOCIATION_IDENTITY_NOT_ISSUED_TO_ML_REQUEST")
        rec = h1.correlation(identity)                                                                                       # CBID and manifest/dataset id stay distinct; held when the record carries no manifest binding id
        if cur.association == "BOUND":
            if (cur.consumer_binding_id, cur.manifest_or_dataset_binding_id) != (rec.consumer_binding_id, rec.manifest_or_dataset_binding_id): raise Refusal(manifest_id, code="AUGMENTED_ASSOCIATION_IMMUTABLE")
            return cur
        out = dataclasses.replace(cur, association="BOUND", consumer_binding_id=rec.consumer_binding_id, manifest_or_dataset_binding_id=rec.manifest_or_dataset_binding_id)
        self._done[manifest_id] = out; return out
    def result_for(self, manifest_id): return self._done.get(manifest_id)
