"""R37: the FEATURE_VERSION_RELATIONSHIP DIFF ENGINE and append-only ledger over the existing `version_relationship` rules (Registry p137-165, p322, p377; DOCX s7).
SOURCE-PRESENT and built: the five dimensions; PARTITION_TOTAL/DISJOINT schema validation (reused `check_field_dimension_map`); CHANGED_FIELDS computed deterministically over exactly the admitted fields; attempt identity outside the diff; the four outcome classes and CORRECTION's two conditions (verified predecessor-defect evidence AND every changed semantic-dimension field attributable to the remediation);
unexplained semantic change -> MATERIAL_ALTERNATIVE; genuinely unverifiable historical content -> RELATIONSHIP_UNCOMPUTABLE (never CORRECTION; routes to MATERIAL_ALTERNATIVE treatment); a pair with no record under the CURRENT diff-schema version is UNCOMPUTED (blocks a successor claim, never blocks delivery of the existing eligible version); earlier records stay immutable and replay pins the exact record id/hash.
NOT source-defined, so HELD and not invented: the relationship record's byte layout and hash (the id/hash below is a labelled CANDIDATE hash), how predecessor-defect evidence is verified (a SUPPLIED verifier callable decides; None => CORRECTION impossible), the class for changes confined to PROVENANCE together with SCOPE only (`COMBINATION_NOT_DEFINED_HELD`), and a class for an identical pair (`NO_CHANGED_FIELDS_NO_CLASS_DEFINED`).
Performance/output values never enter a class: only schema-admitted fields do. Current eligibility/lifecycle authority is not a field and creates no record (p164)."""
from dataclasses import dataclass
from typing import Optional
from ..errors import Refusal
from ..storage.byte_primitives import canonical_bytes, domain_hash
from . import version_relationship as VR
UNVERIFIABLE = "__UNVERIFIABLE_HISTORICAL_CONTENT__"
COMPUTED = "RELATIONSHIP_COMPUTED"
PROVENANCE_CHANGE, SCOPE_CHANGE, CORRECTION, MATERIAL_ALTERNATIVE = "PROVENANCE_CHANGE", "SCOPE_CHANGE", "CORRECTION", "MATERIAL_ALTERNATIVE"
SEMANTIC_DIMS = frozenset(("DEFINITION_SEMANTICS", "CAUSAL_TIME", "FITTED_LEARNED_STATE"))
@dataclass(frozen=True)
class DiffSchema:
    version: str; admitted: tuple; pairs: tuple                 # pairs: ((field, dimension), ...)
@dataclass(frozen=True)
class Relationship:
    predecessor: str; successor: str; schema_version: str; state: str; changed_fields: tuple; relationship_class: Optional[str]; reason: str; evidence_refs: tuple; record_id: str      # record_id == candidate hash (labelled)
def check_schema(s):
    if not (isinstance(s, DiffSchema) and isinstance(s.version, str) and s.version and isinstance(s.admitted, tuple) and isinstance(s.pairs, tuple)): raise Refusal("schema", code="SCHEMA_MISMATCH")
    VR.check_field_dimension_map(s.admitted, s.pairs); return dict(s.pairs)
def _strip(content, schema_fields):
    if not isinstance(content, dict): raise Refusal("content", code="SCHEMA_MISMATCH")
    c = {k: v for k, v in content.items() if k not in VR.OUTSIDE_VERSION_CONTENT_DIFF}                  # attempt identity: research lineage only, never a diff field
    if set(c) != set(schema_fields): raise Refusal(",".join(sorted(set(c) ^ set(schema_fields))), code="SCHEMA_MISMATCH")      # one-sided / unmapped / extra fields are RAISED, never skipped
    return c
def compute(schema: DiffSchema, predecessor_id: str, predecessor: dict, successor_id: str, successor: dict, *, defect_verifier=None, defect_evidence_refs=(), attributable_fields=()) -> Relationship:
    dim = check_schema(schema); a = _strip(predecessor, dim); b = _strip(successor, dim)
    if not all(isinstance(x, str) and x for x in (predecessor_id, successor_id)) or predecessor_id == successor_id: raise Refusal("ids", code="RELATIONSHIP_IDS_INVALID")
    def mk(state, cls, reason, changed, evid=()):
        body = {"predecessor": predecessor_id, "successor": successor_id, "schema_version": schema.version, "state": state, "changed_fields": list(changed), "class": cls, "reason": reason, "evidence_refs": list(evid)}
        return Relationship(predecessor_id, successor_id, schema.version, state, tuple(changed), cls, reason, tuple(evid), domain_hash("SALIX_FEATURE_VERSION_RELATIONSHIP_CANDIDATE_V1", canonical_bytes(body)))
    if any(v == UNVERIFIABLE for v in list(a.values()) + list(b.values())): return mk(VR.UNCOMPUTABLE, None, "HISTORICAL_CONTENT_UNVERIFIABLE_ROUTE_MATERIAL_ALTERNATIVE_TREATMENT", ())
    changed = tuple(sorted(f for f in dim if a[f] != b[f])); dims = {dim[f] for f in changed}
    if not changed: return mk(COMPUTED, None, "NO_CHANGED_FIELDS_NO_CLASS_DEFINED", ())
    if not dims & SEMANTIC_DIMS:
        if dims == {"PROVENANCE_SOURCE"}: return mk(COMPUTED, PROVENANCE_CHANGE, "", changed)
        if dims == {"SCOPE_ELIGIBILITY_DEFINITION"}: return mk(COMPUTED, SCOPE_CHANGE, "", changed)
        return mk(COMPUTED, None, "COMBINATION_NOT_DEFINED_HELD", changed)
    semantic = {f for f in changed if dim[f] in SEMANTIC_DIMS}
    ok = callable(defect_verifier) and bool(defect_evidence_refs) and defect_verifier(tuple(defect_evidence_refs)) is True and isinstance(attributable_fields, tuple) and semantic <= set(attributable_fields) <= set(dim)
    return mk(COMPUTED, CORRECTION if ok else MATERIAL_ALTERNATIVE, "" if ok else "UNEXPLAINED_SEMANTIC_CHANGE_OR_DEFECT_EVIDENCE_NOT_VERIFIED", changed, tuple(defect_evidence_refs) if ok else ())
class RelationshipLedger:
    """Append-only: one record per (predecessor, successor, schema version); earlier schema versions stay as immutable history; replay pins a record by id."""
    def __init__(self): self._r = {}; self._by_id = {}
    def append(self, rel: Relationship):
        if not isinstance(rel, Relationship): raise Refusal("rel", code="RELATIONSHIP_MALFORMED")
        k = (rel.predecessor, rel.successor, rel.schema_version); old = self._r.get(k)
        if old is not None:
            if old != rel: raise Refusal(str(k), code="RELATIONSHIP_IMMUTABLE_PER_SCHEMA_VERSION")
            return old
        self._r[k] = rel; self._by_id[rel.record_id] = rel; return rel
    def pinned(self, record_id): return self._by_id.get(record_id)                                  # historical replay resolves the pinned id, never "current"
    def current(self, predecessor, successor, current_schema_version): return self._r.get((predecessor, successor, current_schema_version))
    def successor_claim(self, predecessor, successor, current_schema_version) -> dict:
        """Gateway rule (p161): a successor/replacement claim needs a COMPUTED record under the CURRENT diff schema; UNCOMPUTED/UNCOMPUTABLE fail the CLAIM closed, while the existing eligible version stays deliverable."""
        r = self.current(predecessor, successor, current_schema_version)
        if r is None: return {"claim": "FAIL_CLOSED", "state": VR.UNCOMPUTED, "existing_version_deliverable": True, "record_id": None}
        if r.state != COMPUTED or r.relationship_class is None: return {"claim": "FAIL_CLOSED", "state": r.state, "existing_version_deliverable": True, "record_id": r.record_id}
        return {"claim": "REFERENCE_RECORD", "state": r.state, "existing_version_deliverable": True, "record_id": r.record_id, "class": r.relationship_class}
