"""ML receiving CONTRACT (Annex §XIV). Tracker -> Gateway -> ML only. STATUS: row builder/validator over Gateway outcomes;
NOT a connection to the real ML. Every input yields either an included row with identity preserved or an EXPLICIT exclusion
record (no silent row drop); no fill of any kind is representable."""
from dataclasses import dataclass
from typing import Optional, Tuple
from ..errors import Refusal
from ..gateway.contracts import Binding, NonDeliveryResolution, AbsenceApplied, DependencyEntry, REQUIRED, OPTIONAL
from ..schema.encoding import Ref
from ..fw.lanes import ConsumerManifest, classify, BASELINE

@dataclass(frozen=True)
class MLRow:
    row_id: str
    generation_binding_ref: Ref
    row_eligibility_reason: tuple          # TAGGED_ENUM_OR_REF value
    row_exclusion_reason: Optional[tuple]
    bindings: Tuple[Binding, ...]          # preserved exactly
    absence_applied: Tuple[AbsenceApplied, ...]   # keyed by FEATURE_ID+FEATURE_VERSION

    @property
    def included(self): return self.row_exclusion_reason is None

def build_row(row_id, generation_binding_ref, entries, outcomes, gateway, requested_vintage_mode, eligibility_reason,
              exclusion_reason_for_missing, tables=None):
    """entries: declared DependencyEntry list; outcomes: gateway outcomes in the same order."""
    if len(entries) != len(outcomes):
        raise Refusal("one outcome per declared dependency", code="OUTCOME_COUNT_MISMATCH")
    bindings, absences, keys = [], [], set()
    for e, o in zip(entries, outcomes):
        k = (e.feature_id, e.feature_version)
        if k in keys:
            raise Refusal("duplicate dependency", code="DUPLICATE_DEPENDENCY")
        keys.add(k)
        if isinstance(o, Binding):
            if gateway.outcome(o.request_id) is not o:
                raise Refusal(o.request_id, code="BINDING_NOT_FROM_GATEWAY")          # F4: no Gateway rebind -> rejected
            if o.entry.feature_id != e.feature_id or o.entry.feature_version != e.feature_version:
                raise Refusal("binding for a different dependency", code="WRONG_VERSION")
            if o.entry.data_vintage_mode != requested_vintage_mode:
                raise Refusal(o.entry.data_vintage_mode, code="VINTAGE_MODE_MIXED_OR_SUBSTITUTED")   # EVENTUAL look-ahead / mixed era
            bindings.append(o)
        elif isinstance(o, AbsenceApplied):
            if e.requirement_class != OPTIONAL or o.absence_handling_applied_ref != e.absence_rule_ref:
                raise Refusal("absence only via the exact governed rule", code="ABSENCE_RULE_MISMATCH")
            absences.append(o)
        elif isinstance(o, NonDeliveryResolution):
            if e.requirement_class == REQUIRED:
                return MLRow(row_id, generation_binding_ref, eligibility_reason, exclusion_reason_for_missing(o), tuple(bindings), tuple(absences))
            raise Refusal("optional dependency non-delivery must resolve to AbsenceApplied", code="OPTIONAL_NON_DELIVERY")
        else:
            raise Refusal(type(o).__name__, code="UNKNOWN_OUTCOME_TYPE")           # raw values/fills are not representable
    return MLRow(row_id, generation_binding_ref, eligibility_reason, None, tuple(bindings), tuple(absences))

def check_generation(m: ConsumerManifest, target: bytes, graph, kind: str):
    """M1/M2/F5: ML_STANDALONE must be baseline-lane with free closure; hidden FW ancestry is rejected. Returns lane."""
    lane = classify(m, target, graph)
    if kind == "ML_STANDALONE" and lane != BASELINE:
        raise Refusal(lane, code="STANDALONE_NOT_BASELINE")
    if kind == "ML_STANDALONE" and m.derived_from is not None and graph.get(m.derived_from) is not None \
            and graph[m.derived_from].kind == "FW":
        raise Refusal(m.derived_from, code="HIDDEN_FW_ANCESTRY")
    return lane

def check_fw_augmented(m: ConsumerManifest, aug: "AugmentedInput", target: bytes, graph):
    """ML_FW_AUGMENTED (Build Plan 13.2): an explicit separate generation class. FW ancestry must be DECLARED (derived_from resolves to an FW manifest), never
    hidden; a Gateway re-bind is required (carried by AugmentedInput); a standalone-style manifest with no FW parent cannot be augmented. Structural only:
    FW return/lineage PAYLOAD fields are not defined by any source read, so only the refs supplied in AugmentedInput are checked for presence."""
    if m.kind != "ML":
        raise Refusal(m.kind, code="AUGMENTED_REQUIRES_ML_MANIFEST")
    if m.derived_from is None:
        raise Refusal(m.manifest_id, code="AUGMENTED_WITHOUT_FW_ANCESTRY")
    parent = graph.get(m.derived_from)
    if parent is None:
        raise Refusal(m.derived_from, code="DERIVED_FROM_UNRESOLVED")
    if parent.kind != "FW":
        raise Refusal(parent.kind, code="AUGMENTED_PARENT_NOT_FW")
    if not isinstance(aug, AugmentedInput) or not getattr(aug.gateway_rebind, "request_id", None):
        raise Refusal("rebind", code="NO_GATEWAY_REBIND")
    return classify(m, target, graph)

@dataclass(frozen=True)
class AugmentedInput:
    """ML_FW_AUGMENTED schema-level completeness (F5/F6): lineage, uncertainty, OOD and dependency interval all required."""
    fw_lineage_ref: Ref
    uncertainty_ref: Optional[Ref]
    ood_ref: Optional[Ref]
    dependency_interval_ref: Optional[Ref]
    gateway_rebind: Optional[Binding]
    fw_generation_identity_ref: Optional[Ref] = None      # Build Plan 13.2: must preserve FW generation identity
    research_exposure_ref: Optional[Ref] = None           # ... and research exposure
    def __post_init__(self):
        for n in ("uncertainty_ref", "ood_ref", "dependency_interval_ref", "fw_generation_identity_ref", "research_exposure_ref"):
            if getattr(self, n) is None:
                raise Refusal(n, code="AUGMENTED_FIELD_MISSING")
        if self.gateway_rebind is None:
            raise Refusal("FW-derived ML input needs a Gateway rebind", code="NO_GATEWAY_REBIND")
