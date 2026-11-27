"""Contract V0.38 section X.1 DEPENDENCY_CLOSURE_RECORD / ANCESTRY_CLOSURE_REPORT (CURRENT Contract 1neiQsQ9AG-QKdyMgOqJxXE026D0uY___yhfGaTlIJ8Y, section X item 1, the closure object, the EDGE_CLASS vocabulary, the
fail-closed rule and the union-ancestry paragraph). Source-present, candidate behaviour:
  * mandatory fields and the EDGE_CLASS vocabulary are those in the source; nothing else is invented;
  * the verdict is DERIVED here from the node/edge sets by traversal over every required content-carrying edge (the UNION, not a linear DERIVED_FROM chain); the record's own CLOSURE_COMPLETE /
    ML_STANDALONE_ADMISSION_INPUT_VERDICT are claims that are CHECKED against the derivation, never trusted (a self-asserted complete=True with a missing/unknown/unresolved edge is FAIL_CLOSED);
  * UNKNOWN edge class, unresolved/missing required edge, an edge naming a node absent from NODE_SET, CLOSURE_COMPLETE=FALSE, FW taint reached => FAIL_CLOSED (source rule);
  * a neutral shared fact used by both FW and ML is NOT taint merely because both consumed it (source rule).
NOT decided here (held, individually): the provider/accepted COMPLETENESS WITNESS for the edge set (no source names who attests that EDGE_SET is the whole union), the FINAL_CLOSURE_HASH composition (no byte layout in
the sources read), resolver appointment, and the closure policy instance. A derived PASS is therefore a CANDIDATE: `qualified` is always False and `witness_status` says so."""
from dataclasses import dataclass
from typing import Optional, Tuple
from ..errors import Refusal

EDGE_CLASSES = ("FEATURE_DEPENDENCY", "LEARNED_DERIVED_MODEL_EDGE", "MODEL_GENERATION_INPUT_EDGE", "FW_PREDICTIVE_EDGE", "DATASET_SOURCE_EDGE", "FITTED_TRANSFORM_EDGE",
                "CALIBRATION_OOD_EDGE", "CROSS_INSTRUMENT_EDGE", "ADMINISTRATIVE_NON_CONTENT_EDGE", "UNKNOWN")
VERDICTS = ("PASS", "FAIL_CLOSED", "REVIEW_REQUIRED")
WITNESS_UNADMITTED = "COMPLETENESS_WITNESS_UNADMITTED_NO_ACCEPTED_PROVIDER"

def _s(x): return isinstance(x, str) and bool(x)

@dataclass(frozen=True)
class ClosureNode:
    node_id: str; node_type: str; version_or_hash: Optional[str]; source_ref: str; lifecycle_state: Optional[str] = None
@dataclass(frozen=True)
class ClosureEdge:
    parent: str; child: str; edge_class: str; evidence_source: str; content_carrying: bool; interval: Optional[Tuple[int, int]] = None
@dataclass(frozen=True)
class ClosureRecord:
    closure_id: str; subject_id: str; subject_type: str; subject_version_or_hash: Optional[str]
    policy_id: str; policy_version: str; policy_hash: str
    nodes: tuple; edges: tuple
    unresolved_edges: tuple; unknown_edge_types: tuple; missing_required_edges: tuple
    closure_complete: bool; fw_taint_present: bool; fw_taint_source_ids: tuple
    ml_fw_augmented_ancestry_present: bool; admission_input_verdict: str
    research_exposure_flags: tuple; computed_ts: int
    resolver_id: str; resolver_version: str; resolver_hash: str; final_closure_hash: str

@dataclass(frozen=True)
class ClosureVerdict:
    verdict: str; reasons: tuple; reached: tuple; derived_fw_taint: bool; witness_status: str = WITNESS_UNADMITTED; qualified: bool = False

def validate_shape(r) -> None:
    """Every mandatory field present and typed; a malformed record is refused (it is not a verdict). Booleans must be real booleans; the vocabulary is the source's."""
    if not isinstance(r, ClosureRecord): raise Refusal(type(r).__name__, code="CLOSURE_NOT_A_CLOSURE_RECORD")
    for f in ("closure_id", "subject_id", "subject_type", "policy_id", "policy_version", "policy_hash", "resolver_id", "resolver_version", "resolver_hash", "final_closure_hash"):
        if not _s(getattr(r, f)): raise Refusal(f, code="CLOSURE_MANDATORY_FIELD_MISSING")
    for f in ("nodes", "edges", "unresolved_edges", "unknown_edge_types", "missing_required_edges", "fw_taint_source_ids", "research_exposure_flags"):
        if not isinstance(getattr(r, f), tuple): raise Refusal(f, code="CLOSURE_MANDATORY_LIST_MISSING")           # mandatory lists may be EMPTY but must be present (a stated empty list is not an absent one)
    for f in ("closure_complete", "fw_taint_present", "ml_fw_augmented_ancestry_present"):
        if getattr(r, f) is not True and getattr(r, f) is not False: raise Refusal(f, code="CLOSURE_MANDATORY_BOOLEAN_MISSING")
    if r.admission_input_verdict not in VERDICTS: raise Refusal(str(r.admission_input_verdict), code="CLOSURE_VERDICT_VOCABULARY")
    if type(r.computed_ts) is not int or r.computed_ts < 0: raise Refusal("computed_ts", code="CLOSURE_MANDATORY_FIELD_MISSING")
    if r.fw_taint_present and not r.fw_taint_source_ids: raise Refusal("taint without sources", code="CLOSURE_TAINT_SOURCES_MANDATORY")
    ids = set()
    for n in r.nodes:
        if not (isinstance(n, ClosureNode) and _s(n.node_id) and _s(n.node_type) and _s(n.source_ref)): raise Refusal(repr(n), code="CLOSURE_NODE_MALFORMED")
        if n.node_id in ids: raise Refusal(n.node_id, code="CLOSURE_NODE_DUPLICATE")
        ids.add(n.node_id)
    for e in r.edges:
        if not (isinstance(e, ClosureEdge) and _s(e.parent) and _s(e.child) and _s(e.evidence_source) and (e.content_carrying is True or e.content_carrying is False)): raise Refusal(repr(e), code="CLOSURE_EDGE_MALFORMED")
        if e.interval is not None and not (isinstance(e.interval, tuple) and len(e.interval) == 2 and all(type(v) is int for v in e.interval) and e.interval[0] <= e.interval[1]): raise Refusal(repr(e), code="CLOSURE_EDGE_INTERVAL_MALFORMED")

def derive(r: ClosureRecord) -> ClosureVerdict:
    """Independent derivation from NODE_SET/EDGE_SET. Ancestors of the subject are found by walking child -> parent over every content-carrying edge (the union of all edge classes)."""
    validate_shape(r)
    reasons = []; nodes = {n.node_id for n in r.nodes}
    if r.subject_id not in nodes: reasons.append("SUBJECT_NOT_IN_NODE_SET")
    by_child = {}
    for e in r.edges:
        by_child.setdefault(e.child, []).append(e)
        if e.edge_class not in EDGE_CLASSES: reasons.append("EDGE_CLASS_OUTSIDE_VOCABULARY")
        if e.edge_class == "ADMINISTRATIVE_NON_CONTENT_EDGE" and e.content_carrying: reasons.append("ADMINISTRATIVE_EDGE_CLAIMS_CONTENT")      # contradictory classification
    seen, stack, taint = {r.subject_id}, [r.subject_id], False
    while stack:
        cur = stack.pop()
        for e in by_child.get(cur, ()):
            if not e.content_carrying: continue                          # administrative/presentation-only: no ancestry by that link
            if e.edge_class == "UNKNOWN" or e.edge_class not in EDGE_CLASSES: reasons.append("UNKNOWN_EDGE_TYPE_ON_REQUIRED_PATH"); continue
            if e.parent not in nodes or e.child not in nodes: reasons.append("EDGE_ENDPOINT_NOT_IN_NODE_SET"); continue
            if e.edge_class == "FW_PREDICTIVE_EDGE" or e.parent in r.fw_taint_source_ids: taint = True
            if e.parent not in seen: seen.add(e.parent); stack.append(e.parent)
    if r.unknown_edge_types: reasons.append("UNKNOWN_EDGE_TYPES_PRESENT")
    if r.unresolved_edges: reasons.append("UNRESOLVED_EDGES_PRESENT")
    if r.missing_required_edges: reasons.append("MISSING_REQUIRED_EDGES_PRESENT")
    if not r.closure_complete: reasons.append("CLOSURE_COMPLETE_FALSE")
    if taint: reasons.append("FW_TAINT_REACHED")
    if taint and not r.fw_taint_present: reasons.append("FW_TAINT_UNDECLARED")          # derived taint the record denied
    if r.admission_input_verdict == "PASS" and reasons: reasons.append("ASSERTED_PASS_CONTRADICTED_BY_DERIVATION")
    reasons = tuple(sorted(set(reasons)))
    return ClosureVerdict("FAIL_CLOSED" if reasons else "PASS", reasons, tuple(sorted(seen - {r.subject_id})), taint)
