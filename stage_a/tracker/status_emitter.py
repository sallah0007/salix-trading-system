"""R50: the OWNING STATUS EMITTER/CALLER (generic candidate, SIMULATION class). Reuses, never replaces: `lifecycle_status_event.journal_to_status_event` (Decision Context V4 A1 SUBJECT_STATUS_EVENT from a COMMITTED lifecycle record),
`SimulationPublicationPath.commit` (the committed SIM_STATUS_FACT side record + StatusProjection + Gateway rows), `status_decoder` (via the path) and `tracker_component.audit.transition_evidence` (BuildPlan s25 evidence for the owning transition).
One bounded sequence, every step before the single write is read-only, a refusal writes nothing:
  1 the lifecycle record is READ BACK from the owning feature journal (reachable from HEAD; a caller never hands in a record); it must be the LATEST committed record of that feature key
  2 the status token comes ONLY from a caller-supplied `kind_to_token` mapping (source-owned, HELD: None => STATUS_MAPPING_HELD). Nothing here maps PUBLISHABLE to CURRENT or WITHDRAWN to HALTED; an unmapped kind refuses
  3 the A1 event is derived (ids/hash/new/prior state from the committed record) and validated with the SUPPLIED boundary evidence (origin evidence is never defaulted; a conflict with a derived value refuses)
  4 sequence must strictly exceed the feature's latest committed side sequence, else refuse BEFORE writing (a non-increasing record would invalidate every projection of that journal)
  5 audit evidence for the owning record is derived; SUPPLIED items not given stay UNBOUND and `complete` stays False (never invented)
  6 exactly ONE SIM_STATUS_FACT append through the path, carrying `origin` = the lifecycle record's seq/hash; an exact replay of the same lifecycle record + token returns the existing side record and appends nothing
Held (not guessed): the lifecycle-kind -> status mapping, the status-origin principal, EFFECTIVE_AT/MACHINE_REASON_CODE/AUTHORITY_STATE and the rest of FROM_BOUNDARY. This changes no gate; a committed status is simulation evidence only."""
import json
from ..errors import Refusal
from tracker_component.audit import transition_evidence
from tracker_component.claims import Refusal as ComponentRefusal
from .lifecycle_status_event import journal_to_status_event
from .sim_publication_path import SimulationPublicationPath, STATUS_KIND, SuppliedRowInputs


class StatusEmitter:
    def __init__(self, path, *, kind_to_token=None):
        if type(path) is not SimulationPublicationPath: raise Refusal("path", code="STATUS_EMITTER_PATH_INVALID")
        if kind_to_token is not None and not (isinstance(kind_to_token, dict) and all(isinstance(k, str) and k and isinstance(v, str) and v for k, v in kind_to_token.items())): raise Refusal("mapping", code="STATUS_MAPPING_INVALID")
        self._path, self._map = path, (None if kind_to_token is None else dict(kind_to_token))

    def _lifecycle(self, feature_key):
        recs = [r for r in self._path.feature_journal.read_from(1) if json.loads(r.body_json).get("feature_key") == feature_key.key()]
        if not recs: raise Refusal(feature_key.key(), code="STATUS_EMIT_NO_COMMITTED_LIFECYCLE_RECORD")
        return recs

    def emit(self, feature_key, supplied: SuppliedRowInputs, *, sequence, boundary_evidence, context_known, audit_fields=None, correction=False):
        if self._map is None: raise Refusal("kind_to_token", code="STATUS_MAPPING_HELD")
        recs = self._lifecycle(feature_key); rec = recs[-1]
        token = self._map.get(rec.kind)
        if token is None: raise Refusal(rec.kind, code="STATUS_KIND_UNMAPPED")
        prior = recs[-2] if len(recs) > 1 else None
        event = journal_to_status_event(rec, prior.kind if prior else None, boundary_evidence, context_known)     # A1 derived + validated; refuses on any gap/conflict
        try: evidence = transition_evidence(rec, **(audit_fields or {}))     # predecessor_hash is the record's own prev_hash (journal predecessor, not the previous record of this feature key)
        except ComponentRefusal as e: raise Refusal(str(e), code=e.code)                                  # one refusal family at this boundary
        mine = [b for b in self._path.records() if b["feature_key"] == feature_key.key()]
        for b in mine:
            if b.get("origin", {}).get("record_hash") == rec.record_hash:
                if b.get("origin", {}).get("token") != token or b[self._path._spec["status_field"]] != token: raise Refusal(rec.record_hash, code="STATUS_EMIT_REPLAY_DIFFERS")
                return {"status_event": event, "audit": evidence, "status_record": None, "replay": True, "simulation": True}
        seqf = self._path._spec["sequence_field"]
        if mine and (type(sequence) is not int or sequence <= max(b[seqf] for b in mine)): raise Refusal(str(sequence), code="STATUS_SEQUENCE_NOT_INCREASING")
        out = self._path.commit(feature_key, supplied, token, sequence=sequence, correction=correction, origin={"record_seq": rec.seq, "record_hash": rec.record_hash, "kind": rec.kind, "token": token})
        return {"status_event": event, "audit": evidence, "status_record": out, "replay": False, "simulation": True}
