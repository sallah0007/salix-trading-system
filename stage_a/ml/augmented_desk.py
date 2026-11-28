"""R50: ML_FW_AUGMENTED governed FW-RETURN / REBIND caller (generic candidate; Build Plan 12-13). Reuses `fw.return_lineage` (return classes; FW-derived predictive input needs lineage+rebind) and `ml.receiver.check_fw_augmented/require_verified`
(declared FW ancestry, issued Gateway binding). Adds the OWNING sequence those pieces never connected:
  1 `record_fw_return`  : an FW return is recorded IMMUTABLY per return id; only the permitted classes (EVIDENCE/REQUEST/LINEAGE), it must carry LINEAGE (a return without lineage cannot feed ML), its FW manifest must be an FW manifest of the graph, and one lineage ref belongs to one return
  2 `rebind`            : an ML manifest is accepted as ML_FW_AUGMENTED only if (a) it declares exactly that return's FW manifest as its parent, (b) the AugmentedInput's lineage ref IS the returned lineage ref, (c) the Gateway actually issued the supplied rebind Binding to ML, and (d) the rebind is not the FW return's own binding. The result is recorded immutably per ML manifest.
The FW return PAYLOAD fields and the support/uncertainty/OOD representation are held (no source defines them): refs are checked for type and identity, not content. A verified rebind is candidate evidence only; ML_STANDALONE and qualification are untouched."""
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


class AugmentedDesk:
    def __init__(self, gateway, graph):
        if gateway is None or not isinstance(graph, dict): raise Refusal("desk", code="AUGMENTED_DESK_PART_MISSING")
        self._g, self._graph, self._ret, self._lin, self._done = gateway, graph, {}, {}, {}
    def record_fw_return(self, ret):
        if not isinstance(ret, FWReturnRecord): raise Refusal(type(ret).__name__, code="FW_RETURN_RECORD_MALFORMED")
        check_fw_return_classes(ret.classes)
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
        if aug.gateway_rebind.request_id == ret.fw_request_id: raise Refusal(ret.fw_request_id, code="AUGMENTED_REBIND_IS_THE_FW_BINDING")
        lane = R.require_verified(R.check_fw_augmented(m, aug, target, self._graph, gateway=self._g))
        out = AugmentedBinding(m.manifest_id, return_id, aug.gateway_rebind.request_id, lane)
        old = self._done.get(m.manifest_id)
        if old is not None and old != out: raise Refusal(m.manifest_id, code="AUGMENTED_REBIND_IMMUTABLE")
        self._done[m.manifest_id] = out; return out
    def result_for(self, manifest_id): return self._done.get(manifest_id)
