"""ML receiving CONTRACT (Annex §XIV). Tracker -> Gateway -> ML only. STATUS: row builder/validator over Gateway outcomes;
NOT a connection to the real ML. Every input yields either an included row with identity preserved or an EXPLICIT exclusion
record (no silent row drop); no fill of any kind is representable."""
from dataclasses import dataclass
from typing import Optional, Tuple
from ..errors import Refusal
from ..gateway.outcome_binding import check_dependency_outcome
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
            check_dependency_outcome(o, e, gateway)                                  # exact dependency + rule + actually issued immutable Gateway outcome
            absences.append(o)
        elif isinstance(o, NonDeliveryResolution):
            check_dependency_outcome(o, e, gateway)                                  # a forged/foreign non-delivery cannot exclude a row
            if e.requirement_class == REQUIRED:
                return MLRow(row_id, generation_binding_ref, eligibility_reason, exclusion_reason_for_missing(o), tuple(bindings), tuple(absences))
            raise Refusal("optional dependency non-delivery must resolve to AbsenceApplied", code="OPTIONAL_NON_DELIVERY")
        else:
            raise Refusal(type(o).__name__, code="UNKNOWN_OUTCOME_TYPE")           # raw values/fills are not representable
    return MLRow(row_id, generation_binding_ref, eligibility_reason, None, tuple(bindings), tuple(absences))

def ancestry(m: ConsumerManifest, graph) -> list:
    """Every ancestor reached through DERIVED_FROM_MANIFEST_REF, nearest first. Fail closed: an unresolved parent (DERIVED_FROM_UNRESOLVED), a cycle (DERIVATION_CYCLE) or a graph
    entry stored under a different manifest id (GRAPH_KEY_MISMATCH) refuses; unknown ancestry is never read as 'no ancestry' (Build Plan 13.1)."""
    seen, out, cur = {m.manifest_id}, [], m
    while cur.derived_from is not None:
        nxt = graph.get(cur.derived_from)
        if nxt is None:
            raise Refusal(cur.derived_from, code="DERIVED_FROM_UNRESOLVED")
        if nxt.manifest_id != cur.derived_from:
            raise Refusal(cur.derived_from, code="GRAPH_KEY_MISMATCH")
        if nxt.manifest_id in seen:
            raise Refusal(nxt.manifest_id, code="DERIVATION_CYCLE")
        seen.add(nxt.manifest_id); out.append(nxt); cur = nxt
    return out

def check_generation(m: ConsumerManifest, target: bytes, graph, kind: str):
    """M1/M2/F5 + Build Plan 13.1: ML_STANDALONE must be baseline-lane with free closure and NO direct or TRANSITIVE FW ancestry. The whole derivation chain is walked (not
    only the immediate parent); a non-ML or unknown-kind ancestor, an unresolved parent or a cycle refuses. Returns lane."""
    if kind != "ML_STANDALONE":
        raise Refusal(str(kind), code="UNKNOWN_GENERATION_KIND")
    if m.kind != "ML":
        raise Refusal(m.kind, code="STANDALONE_REQUIRES_ML_MANIFEST")
    lane = classify(m, target, graph)
    if lane != BASELINE:
        raise Refusal(lane, code="STANDALONE_NOT_BASELINE")
    for anc in ancestry(m, graph):
        if anc.kind == "FW":
            raise Refusal(anc.manifest_id, code="HIDDEN_FW_ANCESTRY")
        if anc.kind != "ML":
            raise Refusal(str(anc.kind), code="UNKNOWN_ANCESTOR_KIND")
    return lane

# MLCore (Matrix-selected 1cf1uR0w..., paras 99-118): ML_STANDALONE needs COMPLETE UNION closure over all required content-carrying ancestry edges (feature->feature, learned-feature->
# model/generation, generation->training/predictor, materialized-output lineage, other declared content-carrying ancestry). Declared content-carrying => traverse; administrative/presentation-
# only => no taint by that link; unknown/unclassified => FAIL CLOSED; incomplete required ancestry => FAIL CLOSED. The three edge CLASSES are source-given; the edge KIND vocabulary and the
# machine-readable edge schema are NOT (blueprint-owned), so none is invented: callers supply (child, parent, class) triples. check_generation above walks ONLY the linear
# DERIVED_FROM_MANIFEST_REF chain and is therefore NOT the union proof.
CONTENT_CARRYING, ADMINISTRATIVE_ONLY = "CONTENT_CARRYING", "ADMINISTRATIVE_ONLY"
UNION_CLOSURE_UNPROVEN = "UNION_CLOSURE_NOT_PROVEN_NO_EDGES_SUPPLIED"
UNION_CLOSURE_TRAVERSED = "TRAVERSED_EDGE_SET_COMPLETENESS_UNPROVEN"

@dataclass(frozen=True)
class StandaloneCheck:
    lane: str
    union_closure: str            # never 'PROVEN': completeness of the supplied edge set has no witness in any source read
    reached: tuple = ()

def union_closure(root: str, edges, taint_sources) -> tuple:
    """Traverse supplied (child, parent, class) edges from `root` over CONTENT_CARRYING edges only. Refuses: UNCLASSIFIED_EDGE (any class other than the two source-given ones, on an edge
    reachable from the root), HIDDEN_FW_ANCESTRY (a taint source is reached through content-carrying edges). Returns the sorted reached ancestor ids. Administrative-only edges do not taint."""
    edges = list(edges); taint = set(taint_sources); by_child = {}
    for e in edges:
        if not (isinstance(e, tuple) and len(e) == 3):
            raise Refusal(repr(e), code="EDGE_MALFORMED")
        by_child.setdefault(e[0], []).append(e)
    seen, stack = {root}, [root]
    while stack:
        cur = stack.pop()
        for child, parent, cls in by_child.get(cur, ()):
            if cls == ADMINISTRATIVE_ONLY:
                continue
            if cls != CONTENT_CARRYING:
                raise Refusal("%s->%s:%r" % (child, parent, cls), code="UNCLASSIFIED_EDGE")     # unknown edge type fails closed
            if parent in taint:
                raise Refusal(parent, code="HIDDEN_FW_ANCESTRY")
            if parent not in seen:
                seen.add(parent); stack.append(parent)
    return tuple(sorted(seen - {root}))

def check_standalone(m: ConsumerManifest, target: bytes, graph, kind: str, edges=None, taint_sources=()) -> StandaloneCheck:
    """The ML_STANDALONE boundary: the linear check (check_generation) plus, if edges are supplied, the union traversal. The result is NEVER qualified: see require_standalone_qualified."""
    lane = check_generation(m, target, graph, kind)
    if edges is None:
        return StandaloneCheck(lane, UNION_CLOSURE_UNPROVEN)
    return StandaloneCheck(lane, UNION_CLOSURE_TRAVERSED, union_closure(m.manifest_id, edges, taint_sources))

def require_standalone_qualified(chk) -> str:
    """Holds the claimed ML_STANDALONE qualification: complete union closure cannot be PROVEN (no source defines the required edge set's completeness witness or the edge schema),
    so this always refuses. Callers needing only the structural lane use check_generation and must not call the result qualified."""
    raise Refusal(getattr(chk, "union_closure", type(chk).__name__), code="UNION_CLOSURE_COMPLETENESS_UNPROVEN")

@dataclass(frozen=True)
class AugmentedCheck:
    """Result of check_fw_augmented. rebind_verified is True ONLY when the supplied Binding is the exact outcome the Gateway issued for its request id. Without a Gateway
    the result is UNVERIFIED_SHAPE_ONLY: structure was checked, provenance was not, and a consumer must not rely on it (use require_verified)."""
    lane: str
    rebind_verified: bool
    status: str

def require_verified(chk: AugmentedCheck) -> str:
    if not isinstance(chk, AugmentedCheck) or not chk.rebind_verified:
        raise Refusal(getattr(chk, "status", type(chk).__name__), code="AUGMENTED_REBIND_UNVERIFIED")
    return chk.lane

def check_fw_augmented(m: ConsumerManifest, aug: "AugmentedInput", target: bytes, graph, gateway=None) -> AugmentedCheck:
    """ML_FW_AUGMENTED (Build Plan 13.2): an explicit separate generation class. FW ancestry must be DECLARED (derived_from resolves to an FW manifest), never hidden; a
    Gateway re-bind is required. The AugmentedInput is structurally validated (typed Ref fields, a Binding). Provenance: only a Gateway that issued exactly that Binding
    verifies it; with no Gateway the result is UNVERIFIED_SHAPE_ONLY. FW return/lineage PAYLOAD fields are not defined by any source read, so refs are checked for type, not content."""
    if m.kind != "ML":
        raise Refusal(m.kind, code="AUGMENTED_REQUIRES_ML_MANIFEST")
    if m.derived_from is None:
        raise Refusal(m.manifest_id, code="AUGMENTED_WITHOUT_FW_ANCESTRY")
    ancestry(m, graph)                                             # unresolved / cyclic / mismatched ancestry refuses before any parent is trusted
    parent = graph.get(m.derived_from)
    if parent.kind != "FW":
        raise Refusal(parent.kind, code="AUGMENTED_PARENT_NOT_FW")
    if not isinstance(aug, AugmentedInput):
        raise Refusal("rebind", code="NO_GATEWAY_REBIND")
    lane = classify(m, target, graph)
    if gateway is None:
        return AugmentedCheck(lane, False, "UNVERIFIED_SHAPE_ONLY")
    if gateway.outcome(aug.gateway_rebind.request_id) is not aug.gateway_rebind:
        raise Refusal(aug.gateway_rebind.request_id, code="BINDING_NOT_FROM_GATEWAY")      # well-typed but never issued (or a different object): refused
    return AugmentedCheck(lane, True, "VERIFIED_ISSUED_BINDING")

@dataclass(frozen=True)
class AugmentedInput:
    """ML_FW_AUGMENTED schema-level completeness (F5/F6; Build Plan 13.2: generation identity, uncertainty/OOD/SUPPORT, dependency interval, research exposure). Every field is an INTERNAL typed
    reference carrier of this seam: the external FW payload representation of any of them (incl. support) is undefined in the sources read and is NOT invented here."""
    fw_lineage_ref: Ref
    uncertainty_ref: Optional[Ref]
    ood_ref: Optional[Ref]
    dependency_interval_ref: Optional[Ref]
    gateway_rebind: Optional[Binding]
    fw_generation_identity_ref: Optional[Ref] = None      # Build Plan 13.2: must preserve FW generation identity
    research_exposure_ref: Optional[Ref] = None           # ... and research exposure
    support_ref: Optional[Ref] = None                     # ... and support (13.2 names it with uncertainty/OOD); internal carrier only
    def __post_init__(self):
        for n in ("fw_lineage_ref", "uncertainty_ref", "ood_ref", "dependency_interval_ref", "fw_generation_identity_ref", "research_exposure_ref", "support_ref"):
            v = getattr(self, n)
            if v is None:
                raise Refusal(n, code="AUGMENTED_FIELD_MISSING")
            if not isinstance(v, Ref):
                raise Refusal(n, code="AUGMENTED_FIELD_MALFORMED")                # an arbitrary object is not a governed reference
        if self.gateway_rebind is None:
            raise Refusal("FW-derived ML input needs a Gateway rebind", code="NO_GATEWAY_REBIND")
        if not isinstance(self.gateway_rebind, Binding) or not getattr(self.gateway_rebind, "request_id", None):
            raise Refusal(type(self.gateway_rebind).__name__, code="NO_GATEWAY_REBIND")
