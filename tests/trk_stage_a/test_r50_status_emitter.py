"""R50: the owning status emitter over the REAL accepted record and the REAL SimulationPublicationPath (SIMULATION class; no principal/mapping appointed)."""
import json, unittest
from stage_a.errors import Refusal
from stage_a.tracker import chain_status as C
from stage_a.tracker.status_emitter import StatusEmitter
from stage_a.tracker.status_projection import StatusProjection
from stage_a.gateway import contracts as G
from tracker_component.journal_port import GENESIS_HEAD
from tracker_component.audit import UNBOUND
from .test_r37_sim_publication_path import build, supplied, gw, F, I
from .test_boundaries import _entry, _health

MAP = {"CANONICAL_ACCEPTED": "SIM_CUR"}                       # TEST mapping supplied by the test; nothing in the repository defines one
def code(f, *a, **k):
    try: f(*a, **k)
    except Refusal as e: return e.code
def boundary(**o):
    d = {k: "x" for k in ("SUBJECT_TYPE", "MACHINE_REASON_CODE", "MACHINE_REASON_CODE_VERSION", "DECISION_CONTEXT_ID", "AUTHORITY_STATE")}
    d.update(PRIOR_STATE="TEST_INITIAL_STATE", CREATED_AT=1, AVAILABLE_ASOF=1, EFFECTIVE_AT=1, RELATED_EVIDENCE_REFS=["e"]); d.update(o); return d
AUD = dict(actor_service_identity="svc", idempotency_key="k1", epoch_fence=1, decision_accepted_timestamp=5, available_as_of=5, evidence_refs=("r",))
def kw(**o):
    d = dict(sequence=1, boundary_evidence=boundary(), context_known=True, audit_fields=AUD); d.update(o); return d

class Emitter(unittest.TestCase):
    def test_positive_committed_lifecycle_record_to_status_event_audit_projection_and_gateway_delivery(self):
        rig, fk, fj, path, body = build(); em = StatusEmitter(path, kind_to_token=MAP); r = em.emit(fk, supplied(), **kw())
        rec = fj.read_from(1)[0]
        self.assertEqual(r["status_event"]["EVENT_HASH"], rec.record_hash); self.assertEqual(r["status_event"]["NEW_STATE"], "CANONICAL_ACCEPTED"); self.assertEqual(r["status_event"]["SUBJECT_ID"], fk.key())
        self.assertTrue(r["audit"]["complete"]) ; self.assertEqual(r["audit"]["subject"], fk.key()); self.assertEqual(r["audit"]["new_hash"], rec.record_hash); self.assertFalse(r["audit"]["authoritative"])
        proj = path.status_projection(); self.assertTrue(proj.authoritative and proj.simulation); g = gw(proj); path.feed(g)
        self.assertIsInstance(g.resolve("r1", _entry(fid=F, ver=fk.feature_version), I, I, 3, 10, _health()), G.Binding)
        self.assertEqual(json.loads(path._sj.read_from(1)[0].body_json)["origin"]["record_hash"], rec.record_hash)
    def test_no_mapping_unmapped_kind_and_bad_boundary_write_nothing(self):
        rig, fk, fj, path, body = build(); n = path._sj.head()
        self.assertEqual(code(StatusEmitter(path).emit, fk, supplied(), **kw()), "STATUS_MAPPING_HELD")                      # no mapping is defaulted
        self.assertEqual(code(StatusEmitter(path, kind_to_token={"PUBLISHABLE": "SIM_CUR"}).emit, fk, supplied(), **kw()), "STATUS_KIND_UNMAPPED")   # the committed kind is CANONICAL_ACCEPTED; nothing is inferred
        em = StatusEmitter(path, kind_to_token=MAP)
        self.assertEqual(code(em.emit, fk, supplied(), **kw(boundary_evidence=boundary(MACHINE_REASON_CODE=None))), "STATUS_EVENT_FIELD_MISSING")
        self.assertEqual(code(em.emit, fk, supplied(), **kw(boundary_evidence=boundary(PRIOR_STATE=None))), "STATUS_EVENT_FIELD_MISSING")          # the journal has no initial-state value: HELD, never defaulted
        self.assertEqual(code(em.emit, fk, supplied(), **kw(context_known=False)), "STATUS_WITHOUT_REQUIRED_CONTEXT")
        self.assertEqual(code(em.emit, fk, supplied(), **kw(boundary_evidence=boundary(SUBJECT_ID="other"))), "BOUNDARY_EVIDENCE_CONFLICTS_WITH_COMMITTED_RECORD")
        self.assertEqual(code(em.emit, fk, supplied(), **kw(audit_fields=dict(AUD, bogus=1))), "AUDIT_UNKNOWN_FIELD")
        self.assertEqual(code(StatusEmitter, path, kind_to_token={"X": 5}), "STATUS_MAPPING_INVALID")
        self.assertEqual(path._sj.head(), GENESIS_HEAD)
    def test_unsupplied_audit_items_stay_unbound_never_complete(self):
        rig, fk, fj, path, body = build(); r = StatusEmitter(path, kind_to_token=MAP).emit(fk, supplied(), **kw(audit_fields={}))
        self.assertFalse(r["audit"]["complete"]); self.assertEqual(r["audit"]["actor_service_identity"], UNBOUND)
    def test_replay_appends_nothing_a_different_token_is_refused_and_sequence_must_increase(self):
        rig, fk, fj, path, body = build(); em = StatusEmitter(path, kind_to_token=MAP); em.emit(fk, supplied(), **kw()); h = path._sj.head()
        r = em.emit(fk, supplied(), **kw(sequence=2)); self.assertTrue(r["replay"]) ; self.assertEqual(path._sj.head(), h)
        self.assertEqual(code(StatusEmitter(path, kind_to_token={"CANONICAL_ACCEPTED": "SIM_OUT"}).emit, fk, supplied(), **kw(sequence=2)), "STATUS_EMIT_REPLAY_DIFFERS")
    def test_stale_owning_head_fails_closed_after_a_later_feature_record(self):
        rig, fk, fj, path, body = build(); StatusEmitter(path, kind_to_token=MAP).emit(fk, supplied(), **kw())
        fj.append(fj.head(), "PUBLISHABLE", {"feature_key": fk.key(), "feature_version": fk.feature_version, "accepted_seq": 1, "accepted_hash": json.loads(fj.read_from(1)[0].body_json)["verification_hash"], "verification_hash": "v"})
        proj = path.status_projection(); self.assertFalse(proj.authoritative)                                                # the owning HEAD advanced: the cached status is not authority until re-emitted

    def test_a_second_lifecycle_record_emits_its_own_event_audit_predecessor_and_requires_a_higher_sequence(self):
        rig, fk, fj, path, body = build(); m = {"CANONICAL_ACCEPTED": "SIM_CUR", "PUBLISHABLE": "SIM_OUT"}        # TEST mapping only (no source defines one)
        em = StatusEmitter(path, kind_to_token=m); em.emit(fk, supplied(), **kw()); acc = fj.read_from(1)[0]
        fj.append(fj.head(), "PUBLISHABLE", {"feature_key": fk.key(), "feature_version": fk.feature_version, "accepted_seq": acc.seq, "accepted_hash": acc.record_hash, "verification_hash": body["verification_hash"]})
        self.assertEqual(code(em.emit, fk, supplied(), **kw(sequence=1, boundary_evidence=boundary(PRIOR_STATE="CANONICAL_ACCEPTED"))), "STATUS_SEQUENCE_NOT_INCREASING")
        self.assertEqual(code(em.emit, fk, supplied(), **kw(sequence=2)), "BOUNDARY_EVIDENCE_CONFLICTS_WITH_COMMITTED_RECORD")          # a stale supplied prior state is refused: prior is derived from the journal
        r = em.emit(fk, supplied(), **kw(sequence=2, boundary_evidence=boundary(PRIOR_STATE="CANONICAL_ACCEPTED")))
        self.assertEqual(r["status_event"]["NEW_STATE"], "PUBLISHABLE"); self.assertEqual(r["status_event"]["PRIOR_STATE"], "CANONICAL_ACCEPTED"); self.assertEqual(r["audit"]["predecessor_hash"], acc.record_hash); self.assertEqual(r["audit"]["operation"], "PUBLISHABLE")


# ---- R51: pinned owning/side HEAD races (genuine interleavings through public journal/path hooks; SIMULATION, TEST mapping) ----------------------------------------------------------
from stage_a.tracker.status_projection import StatusProjection
def publishable(fj, fk, body):
    acc = fj.read_from(1)[0]
    return lambda: fj.append(fj.head(), "PUBLISHABLE", {"feature_key": fk.key(), "feature_version": fk.feature_version, "accepted_seq": acc.seq, "accepted_hash": acc.record_hash, "verification_hash": body["verification_hash"]})
class Races(unittest.TestCase):
    M2 = {"CANONICAL_ACCEPTED": "SIM_CUR", "PUBLISHABLE": "SIM_OUT"}                 # TEST mapping: old -> CURRENT, new -> SUPERSEDED (no source defines one)
    def test_a_publishable_append_between_the_origin_read_and_the_commit_never_leaves_an_old_origin_stamped_with_the_new_head(self):
        rig, fk, fj, path, body = build(); em = StatusEmitter(path, kind_to_token=self.M2); real = fj.head; n = [0]; act = publishable(fj, fk, body)
        def head():
            n[0] += 1
            if n[0] == 2: act()                                                # 1 = emitter's pinned basis, 2 = the path.commit capture: the owning HEAD moves between them
            return real()
        fj.head = head
        r = em.emit(fk, supplied(), **kw(boundary_evidence=boundary(PRIOR_STATE="CANONICAL_ACCEPTED")))
        recs = path.records(); self.assertEqual([b["origin"]["kind"] for b in recs], ["PUBLISHABLE"]); self.assertEqual(recs[0]["source_head_seq"], 2); self.assertEqual(r["status_event"]["NEW_STATE"], "PUBLISHABLE")      # re-derived from the NEW record, never CANONICAL_ACCEPTED/CURRENT on head 2
        proj = path.status_projection(); self.assertTrue(proj.authoritative); g = gw(proj); path.feed(g)
        self.assertNotIsInstance(g.resolve("r1", _entry(fid=F, ver=fk.feature_version), I, I, 3, 10, _health()), G.Binding)          # SUPERSEDED: the genuine latest-source result denies
    def test_the_same_race_with_a_boundary_evidence_that_cannot_describe_the_new_record_refuses_and_writes_nothing(self):
        rig, fk, fj, path, body = build(); em = StatusEmitter(path, kind_to_token=self.M2); real = fj.head; n = [0]; act = publishable(fj, fk, body)
        def head():
            n[0] += 1
            if n[0] == 2: act()
            return real()
        fj.head = head
        self.assertEqual(code(em.emit, fk, supplied(), **kw()), "BOUNDARY_EVIDENCE_CONFLICTS_WITH_COMMITTED_RECORD"); self.assertEqual(path.records(), [])
    def test_two_emitters_one_effect_when_the_second_runs_between_the_first_ones_validation_and_append(self):
        rig, fk, fj, path, body = build(); e1, e2 = StatusEmitter(path, kind_to_token=MAP), StatusEmitter(path, kind_to_token=MAP); real = path.records; fired = []
        def records():
            out = real()
            if not fired: fired.append(1); self.assertFalse(e2.emit(fk, supplied(), **kw())["replay"])          # inner emitter commits seq1 AFTER the outer validated mine=[]
            return out
        path.records = records
        r = e1.emit(fk, supplied(), **kw()); path.records = real
        self.assertTrue(r["replay"]); self.assertEqual(len(path.records()), 1); p = path.status_projection(); self.assertTrue(p.authoritative)               # cold projection does NOT raise SEQUENCE_NOT_INCREASING
    def test_different_origins_racing_keep_strictly_increasing_sequences_or_refuse(self):
        rig, fk, fj, path, body = build(); e1 = StatusEmitter(path, kind_to_token=self.M2); e1.emit(fk, supplied(), **kw()); publishable(fj, fk, body)()
        e2 = StatusEmitter(path, kind_to_token=self.M2); real = path.records; fired = []
        def records():
            out = real()
            if not fired: fired.append(1); e2.emit(fk, supplied(), **kw(sequence=2, boundary_evidence=boundary(PRIOR_STATE="CANONICAL_ACCEPTED")))
            return out
        path.records = records
        self.assertTrue(e1.emit(fk, supplied(), **kw(sequence=2, boundary_evidence=boundary(PRIOR_STATE="CANONICAL_ACCEPTED")))["replay"]); path.records = real
        self.assertEqual(sorted(b["seq"] for b in path.records()), [1, 2]); path.status_projection()
    def test_write_then_raise_restart_retry_makes_one_effect_and_unrelated_next_status_still_works(self):
        rig, fk, fj, path, body = build(); em = StatusEmitter(path, kind_to_token=self.M2); sj = path._sj; real = sj.append; state = [0]
        def flaky(h, k, b):
            r = real(h, k, b)
            if not state[0]: state[0] = 1; raise RuntimeError("WRITE_LANDED_OUTCOME_UNKNOWN")
            return r
        sj.append = flaky
        with self.assertRaises(RuntimeError): em.emit(fk, supplied(), **kw())
        sj.append = real; r = StatusEmitter(path, kind_to_token=self.M2).emit(fk, supplied(), **kw(sequence=2)); self.assertTrue(r["replay"]); self.assertEqual(len(path.records()), 1)       # restart + retry: the durable record is found by origin
        publishable(fj, fk, body)(); r2 = em.emit(fk, supplied(), **kw(sequence=2, boundary_evidence=boundary(PRIOR_STATE="CANONICAL_ACCEPTED"))); self.assertFalse(r2["replay"]); self.assertEqual(len(path.records()), 2); path.status_projection()
    def test_a_race_that_never_settles_refuses_closed(self):
        rig, fk, fj, path, body = build(); em = StatusEmitter(path, kind_to_token=MAP); sj = path._sj; real = sj.head; n = [0]
        def head():
            h = real(); n[0] += 1
            if n[0] % 2 == 1: return h
            return h
        from tracker_component.journal_port import HeadMismatch, Head
        orig_append = sj.append
        def append(h, k, b): raise HeadMismatch(h, h)
        sj.append = append
        self.assertEqual(code(em.emit, fk, supplied(), **kw()), "STATUS_EMIT_RACE_EXHAUSTED"); sj.append = orig_append; self.assertEqual(path.records(), [])
