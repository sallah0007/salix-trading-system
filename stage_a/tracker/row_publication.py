"""R53 per-ROW publication into the EXISTING SIMULATION publication path (CANDIDATE, SIMULATION class; reuses SimulationPublicationPath.commit, status_decoder, StatusProjection and the Gateway unchanged).
The published row is DERIVED from three committed things, never handed in: (1) the ROW_ACCEPTED record READ BACK from the row namespace journal (reachable from HEAD), (2) the stored PendingRow re-loaded and re-verified by the row store, (3) the ACCEPTED feature-version manifest read back with bytes re-hashed
(`accepted_manifest`). The row must bind that very feature version and manifest hash. AVAILABLE_ASOF is the acceptance record's own time (== CANONICAL_ACCEPTED_AT).
The typed transition hash is RECOMPUTED here from the record's fields by the independent encoder and must equal the recorded one; the canonical_transition_ref carries that hash.
SUPPLIED and HELD (not invented): status token (through the path's own status_map; PUBLISHABLE is never read as CURRENT), sequence, VISIBLE_AT, the projection HASH (no hash rule is defined), data vintage mode, the source/causal policy ref.
Not claimed: that the acceptance is qualified, any gate/hold clearance, a per-row A1 SUBJECT_STATUS_EVENT (the lifecycle-kind vocabulary does not cover ROW_ACCEPTED; no mapping is invented)."""
import json
from ..errors import Refusal, UnknownCommit
from tracker_component.journal_port import HeadMismatch, GENESIS_HEAD
from ..schema import objects as O, independent as X
from ..schema.encoding import Ref
from . import accepted_manifest as AM
from . import row_acceptance as RA
from .sim_publication_path import SuppliedRowInputs

def _accepted_record(journals, row):
    j = journals.journal(RA.row_namespace(row)); head = j.head()
    for r in j.read_from(1):
        if r.seq > head.seq: break
        if r.kind != RA.KIND: raise Refusal(r.kind, code="ROW_NAMESPACE_FOREIGN_KIND")
        b = json.loads(r.body_json)
        if b.get("version") != RA.VERSION_TAG: raise Refusal(b.get("version"), code="ROW_ACCEPTED_VERSION_UNKNOWN")
        yield r, b

class RowPublication:
    def __init__(self, path, journals, rows, tables, store):
        for n, o in (("path", path), ("journals", journals), ("rows", rows), ("tables", tables), ("store", store)):
            if o is None: raise Refusal(n, code="ROW_PUBLICATION_PART_MISSING")
        self._path, self._js, self._rows, self._t, self._st = path, journals, rows, tables, store

    def _derive(self, feature_key, row_hash, visible_at, published_projection_hash, data_vintage_mode, source_or_causal_policy_ref):
        row = self._rows.load(row_hash)                                                       # committed + re-verified row only
        hit = [(r, b) for r, b in _accepted_record(self._js, row) if b["row_content_hash"] == row_hash]
        if not hit: raise Refusal(row_hash, code="ROW_NOT_ACCEPTED")
        rec, b = hit[-1]
        rb = AM.read_accepted_manifest(self._path.feature_journal, self._st, feature_key)       # the ACTUAL accepted feature version, manifest bytes re-hashed
        if row.feature_version != feature_key.feature_version or row.quant_manifest_hash != bytes.fromhex(rb.manifest_hash): raise Refusal(row_hash, code="ROW_FEATURE_BINDING_MISMATCH")
        ev = b["verification_evidence_ref"]; evref = Ref(ev[0], bytes.fromhex(ev[1]), bytes.fromhex(ev[2]), None if ev[3] is None else bytes.fromhex(ev[3]))
        gd = b["gate_dependency_transition_ref"]; gref = None if gd is None else Ref(gd[0], bytes.fromhex(gd[1]), bytes.fromhex(gd[2]), None if gd[3] is None else bytes.fromhex(gd[3]))
        c = O.CanonicalTransition(bytes.fromhex(row_hash), evref, b["sifp_fencing_epoch"], bytes.fromhex(b["canonical_commit_point_id"]), b[RA.AT.TIME_KEY], b["available_asof"], gref, b["currentness_state_at_acceptance"], b["status_event"])
        try: th = X.transition_hash(RA.transition_independent_dict(self._t, c), self._t.enums); ok = th.hex() == b["transition_hash"] and O.transition_hash(self._t, c).hex() == b["transition_hash"]
        except (ValueError, KeyError, TypeError): ok = False                                  # a record whose fields do not form a valid typed transition is refused, not propagated untyped
        if not ok: raise Refusal(row_hash, code="ROW_ACCEPTED_TRANSITION_HASH_MISMATCH")
        tref = Ref("CANONICAL_TRANSITION_REF", bytes.fromhex(rec.record_hash), RA.VERSION_TAG.encode(), th)
        sup = SuppliedRowInputs(row.feature_id, row.instrument_id, row.timeframe_id, row.materialization_version, row.step_index, row.event_time, row.logical_encoding_version, row.published_projection_name, row.published_projection_bits,
                                published_projection_hash, row.fit_generation_ref, data_vintage_mode, b["available_asof"], visible_at, source_or_causal_policy_ref, tref)
        return sup, {"row_accepted_seq": rec.seq, "row_accepted_hash": rec.record_hash, "row_content_hash": row_hash, "token_basis": b["currentness_state_at_acceptance"]}

    def publish(self, feature_key, row_hash, token, *, sequence, visible_at, published_projection_hash, data_vintage_mode, source_or_causal_policy_ref, attempts=4):
        """ONE SIM_STATUS_FACT append derived from the accepted row. The side HEAD is PINNED before the replay lookup and the sequence validation, and the single append is compare-and-append against that SAME basis
        (the StatusEmitter pattern): a concurrent publisher that lands first moves the HEAD, the append fails closed (HeadMismatch), and everything is re-read and re-validated - an exact replay of the same row+token then returns the
        genuine winner and appends nothing; a different row taking the same (feature, version, instrument, timeframe, materialization version) sequence is refused. An UnknownCommit that landed is found by the replay lookup on the next
        attempt; one that did not is re-attempted. Exhaustion refuses. No cross-HEAD atomicity is claimed (owning-head advance is guarded by the path's pinned source head). An exact replay returns the existing record; a different token is refused."""
        sp = self._path; spec = sp._spec
        for _ in range(attempts):
            src = sp.feature_journal.head(); side = sp._sj.head()                                           # both basis heads BEFORE any state is read
            sup, origin = self._derive(feature_key, row_hash, visible_at, published_projection_hash, data_vintage_mode, source_or_causal_policy_ref)
            mine = None; seqs = []; asofs = []
            for r in (sp._sj.read_from(1) if side != GENESIS_HEAD else []):
                if r.seq > side.seq: break
                bd = json.loads(r.body_json)
                if bd.get("origin", {}).get("row_content_hash") == row_hash: mine = (r, bd); break
                if all(bd.get(n) == v for n, v in zip(spec["mv"], self._mv(sup, feature_key))): seqs.append(bd[spec["sequence_field"]]); asofs.append(bd[spec["available_asof_field"]])
            if mine is not None:
                if mine[1][spec["status_field"]] != token: raise Refusal(row_hash, code="ROW_PUBLICATION_REPLAY_DIFFERS")
                return mine[0]
            if seqs and (type(sequence) is not int or sequence <= max(seqs)): raise Refusal(str(sequence), code="ROW_PUBLICATION_SEQUENCE_NOT_INCREASING")
            if asofs and sup.available_asof < max(asofs): raise Refusal(str(sup.available_asof), code="ROW_PUBLICATION_ASOF_DECREASED")        # chain-status rule: AVAILABLE_ASOF is non-decreasing per MV; a cold projection would refuse the whole journal
            try: return sp.commit(feature_key, sup, token, sequence=sequence, origin=origin, expected_source_head=src, expected_side_head=side)
            except HeadMismatch: continue                                                                      # the side HEAD moved after validation: re-read and re-validate
            except UnknownCommit: continue                                                                     # landed => found as the replay next attempt; absent => re-attempted
            except Refusal as e:
                if e.code == "SIM_PUBLICATION_SOURCE_HEAD_ADVANCED": continue
                raise
        raise Refusal(row_hash, code="ROW_PUBLICATION_RACE_EXHAUSTED")

    def _mv(self, sup, feature_key):
        bf = self._path._spec["bytes_fields"]; vals = (sup.feature_id, feature_key.feature_version, sup.instrument_id, sup.timeframe_id, sup.materialization_version)
        return [v.hex() if n in bf else v for n, v in zip(self._path._spec["mv"], vals)]
