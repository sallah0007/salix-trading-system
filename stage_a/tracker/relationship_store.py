"""R38: DURABLE, OWNER-BOUND version-relationship record store + the successor-claim reference (replaces the 'recorded/existing_version_deliverable' bare fields of `version_diff.RelationshipLedger.successor_claim` as a thing a reader could treat as authority).
  * records live in an append-only chain-verified JOURNAL (candidate kind `VERSION_RELATIONSHIP`; the byte layout is NOT source-defined, the id is the labelled candidate hash `version_diff` computes); replay re-derives; an identical retry is a no-op; a different record for the same (predecessor, successor, schema version) refuses;
  * BOTH versions must resolve in the OWNING feature journals (`owner_check(feature_key_string) -> bool`; `journal_owner_check` builds it from a FeatureJournalSet: the version must be CANONICAL_ACCEPTED or PUBLISHABLE there) before a record is appended or a reference is returned;
  * `successor_reference` returns a `RelationshipReference` that carries NO delivery fact: existing-version deliverability is the Gateway's decision under its own checks (p161: a missing/uncomputed record blocks the successor CLAIM, never delivery of the existing eligible version) - so this type has no `existing_version_deliverable` field to misread; `claim_allowed` is True only for a COMPUTED record with a class under the CURRENT schema version.
`health_observation(...)` (health.adapters.from_relationship_reference) reports facts only; no Health verdict. Clears no gate; mapping to chain-status/lifecycle is source-owned and HELD."""
import json
from dataclasses import dataclass
from typing import Optional
from ..errors import Refusal
from tracker_component.journal_port import GENESIS_HEAD
from ..replay import replay
from . import version_diff as VD, version_relationship as VR
KIND = "VERSION_RELATIONSHIP"; LIVE = ("CANONICAL_ACCEPTED", "PUBLISHABLE")
@dataclass(frozen=True)
class RelationshipReference:
    predecessor: str; successor: str; schema_version: str; state: str; relationship_class: Optional[str]; record_id: Optional[str]; claim_allowed: bool; store_head_seq: int; reason: str
def journal_owner_check(journals):
    def check(fk_string):
        ns, _, ver = fk_string.rpartition("/")
        if not ns: return False
        try: st = replay(ns, journals.journal(ns).read_from(1)).get(ver)
        except Refusal: return False
        return st is not None and st.status in LIVE
    return check
class RelationshipStore:
    """R39: a record is accepted ONLY if the actual compute path, re-run here over the OWNING predecessor/successor content under the store's CURRENT diff schema (and, for CORRECTION, the supplied defect verifier + evidence), reproduces the exact record (state, class, changed fields, reason, evidence, labelled candidate record_id). A hand-authored class, a forged self-consistent class+hash, an unknown class, an arbitrary hash or content that is not the owner's all fail RELATIONSHIP_DOES_NOT_MATCH_RECOMPUTATION. Unbound inputs (no schema / no content source) => append refuses and a reference is not claim-allowed (HELD, never guessed). Records already in the journal are exact historical pins (kept; `pinned`); current eligibility re-verifies only records under the current schema."""
    def __init__(self, journal, owner_check, *, schema=None, content_of=None, defect_verifier=None):
        if not callable(owner_check): raise Refusal("owner_check", code="RELATIONSHIP_OWNER_CHECK_REQUIRED")
        if schema is not None: VD.check_schema(schema)
        if content_of is not None and not callable(content_of): raise Refusal("content_of", code="RELATIONSHIP_CONTENT_SOURCE_INVALID")
        self._j, self._own, self._schema, self._content, self._verifier = journal, owner_check, schema, content_of, defect_verifier
    def _records(self):
        head = self._j.head(); out = {}; attr = {}
        for r in (self._j.read_from(1) if head != GENESIS_HEAD else []):
            if r.kind != KIND: raise Refusal(r.kind, code="RELATIONSHIP_UNKNOWN_RECORD_KIND")
            b = json.loads(r.body_json); k = (b["predecessor"], b["successor"], b["schema_version"]); out[k] = VD.Relationship(b["predecessor"], b["successor"], b["schema_version"], b["state"], tuple(b["changed_fields"]), b["class"], b["reason"], tuple(b["evidence_refs"]), b["record_id"]); attr[k] = tuple(b.get("attributable_fields", ()))
        self._attr = attr; return head, out
    def _recompute(self, pred, succ, evidence_refs, attributable):
        if self._schema is None or self._content is None: raise Refusal("inputs", code="RELATIONSHIP_RECOMPUTATION_INPUTS_NOT_BOUND_HELD")
        cp, cs = self._content(pred), self._content(succ)
        if not (isinstance(cp, dict) and isinstance(cs, dict)): raise Refusal("%s -> %s" % (pred, succ), code="RELATIONSHIP_OWNING_CONTENT_NOT_RESOLVED")
        return VD.compute(self._schema, pred, cp, succ, cs, defect_verifier=self._verifier, defect_evidence_refs=tuple(evidence_refs), attributable_fields=tuple(attributable))
    def append(self, rel, attributable_fields=()):
        if not isinstance(rel, VD.Relationship): raise Refusal("rel", code="RELATIONSHIP_MALFORMED")
        if not (self._own(rel.predecessor) and self._own(rel.successor)): raise Refusal("%s -> %s" % (rel.predecessor, rel.successor), code="RELATIONSHIP_OWNER_NOT_RESOLVED")
        if self._schema is None or rel.schema_version != self._schema.version: raise Refusal(rel.schema_version, code="RELATIONSHIP_SCHEMA_NOT_THE_CURRENT_BOUND_SCHEMA")      # historical records are pinned, never re-authored
        want = self._recompute(rel.predecessor, rel.successor, rel.evidence_refs, attributable_fields)
        if want != rel: raise Refusal("%s -> %s" % (rel.predecessor, rel.successor), code="RELATIONSHIP_DOES_NOT_MATCH_RECOMPUTATION")
        head, recs = self._records(); k = (rel.predecessor, rel.successor, rel.schema_version); old = recs.get(k)
        if old is not None:
            if old != rel: raise Refusal(str(k), code="RELATIONSHIP_IMMUTABLE_PER_SCHEMA_VERSION")
            return None
        return self._j.append(head, KIND, {"predecessor": rel.predecessor, "successor": rel.successor, "schema_version": rel.schema_version, "state": rel.state, "changed_fields": list(rel.changed_fields), "class": rel.relationship_class, "reason": rel.reason, "evidence_refs": list(rel.evidence_refs), "record_id": rel.record_id, "attributable_fields": list(attributable_fields)})
    def successor_reference(self, predecessor, successor, current_schema_version) -> RelationshipReference:
        head, recs = self._records(); h = head.seq
        if not (self._own(predecessor) and self._own(successor)): return RelationshipReference(predecessor, successor, current_schema_version, "OWNER_NOT_RESOLVED", None, None, False, h, "VERSION_NOT_LIVE_IN_OWNING_JOURNAL")
        k = (predecessor, successor, current_schema_version); r = recs.get(k)
        if r is None: return RelationshipReference(predecessor, successor, current_schema_version, VR.UNCOMPUTED, None, None, False, h, "NO_RECORD_UNDER_CURRENT_SCHEMA")
        ok = r.state == VD.COMPUTED and r.relationship_class is not None
        try:
            if self._schema is None or self._schema.version != current_schema_version: why = "CURRENT_SCHEMA_NOT_BOUND_HELD"
            elif self._recompute(predecessor, successor, r.evidence_refs, self._attr.get(k, ())) != r: why = "RECORD_DOES_NOT_MATCH_RECOMPUTATION"
            else: why = None
        except Refusal as e: why = e.code
        if why is not None: return RelationshipReference(predecessor, successor, current_schema_version, r.state, r.relationship_class, r.record_id, False, h, why)       # fail closed: a stored record never allows the claim unless the compute path reproduces it NOW
        return RelationshipReference(predecessor, successor, current_schema_version, r.state, r.relationship_class, r.record_id, ok, h, r.reason)
    def pinned(self, record_id):
        for r in self._records()[1].values():
            if r.record_id == record_id: return r
