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
