"""R53: the separated per-ROW route (real OS child processes over a shared FileObjectStore): row_verify (independent verifier) and row_accept (epoch-fenced RowAcceptor, cross-process re-derivation) -> RowPublication -> Composition -> Core -> Gateway -> BOTH FW and ML.
#149 is the feature-VERSION separated route; this is the per-ROW route. NOTE: rows live in the shared FileObjectStore (child processes); the test Gateway factory uses a fresh IN-MEMORY consumer final store - durable/cold consumer recovery is covered separately (test_r53_row_route_delivery cold restart, #157). SIM profile/clock/commit-point/tables UNADMITTED (tests/trk_stage_a/row_profile_sim.py). Clears no gate/hold."""
import dataclasses, json, os, tempfile, unittest
from stage_a.errors import Refusal
from stage_a.gateway import contracts as G
from stage_a.gateway.v038 import FinalResolutionIdentity as FI
from stage_a.ops import workers as W
from stage_a.ops.process_supervisor import ProcessSupervisor
from stage_a.tracker import row_acceptance as RA, row_publication as RP, accepted_manifest as AM
from stage_a.tracker.materialization import row_store as RS
from stage_a.tracker.materialization.state_rows import StateRowBuilder
from . import test_r41_separated_caller as RC
from .test_r40_separated_handlers import HS
from .test_boundaries import I, R
from .test_r24_core import NONE_
from .test_r53_row_acceptance import T, FX, kw as rkw, SCHEMA, enc, dec, step_fn, H as RH
from .test_r53_row_route_delivery import GTAB, _gw
from stage_a.tracker.registry import FeatureJournalSet
SEP = "stage_a.ops.separated_row_handlers:"
ROWHS = {"row.verify": ("tracker-verifier-worker", SEP + "row_verify"), "row.accept": ("tracker-acceptance-worker", SEP + "row_accept")}
FID = bytes(range(16, 32))

class SepRows(unittest.TestCase):
    def setUp(self):
        os.environ["SALIX_ROW_PROFILE"] = "tests.trk_stage_a.row_profile_sim:profile"; self.base = RC.Caller("setUp"); self.base.setUp(); b = self.base
        self.crash = tempfile.TemporaryDirectory(); b.sup.close(); b.sup = ProcessSupervisor(b.q, dict(HS, **ROWHS), reply_timeout=90, max_attempts=2)
        pkg, self.fk, self.co = b._feature("mom3", 1); r = self.co.accept_and_publish(pkg, RC.supplied(), "SIM_CUR", sequence=1, now=10, max_age=50, l2_applicability=RC.AP, accept_fn=b.acc); assert r.outcome.stage == "SEPARATED_ACCEPTED"
        mh = AM.read_accepted_manifest(b.rig.journals.journal(self.fk.namespace()), b.rig.store, self.fk).manifest_hash; self.res = r
        fixed = dict(FX, feature_id=RC.supplied().feature_id, feature_version=self.fk.feature_version, quant_manifest_hash=bytes.fromhex(mh), instrument_id=I, timeframe_id=I, materialization_version="mrow")
        self.rows = RS.PendingRowStore(b.rig.store, T); ch = RS.CommittedRowChain(StateRowBuilder(SCHEMA, T, enc, dec, fixed), self.rows); self.out, ph = [], None
        for i, x in enumerate([1.0, 2.0, 4.0]):
            row, rc = ch.step(step_fn, ph, {"x": x}, **dict(rkw(i, origin=ph is None), event_time=30 + i)); self.out.append((row, rc)); ph = rc.row_hash
    def tearDown(self): self.base.tearDown(); os.environ.pop("SALIX_ROW_PROFILE", None); os.environ.pop("SALIX_SEP_CRASH_ONCE_DIR", None); self.crash.cleanup()
    def run_jobs(self, i, accept=True, rh=None):
        b = self.base; h = self.out[i][1].row_hash; b.q.submit(W.Job("rv%d" % i, "row.verify", "idem-rv%d" % i, (("row", h),))); done = list(b.sup.run_until_idle(20))
        rh = rh or (lambda g: None if g is None else g[0].decode())(b.rig.store.get("sep/row-ver-by-row/" + h))
        if accept and rh: b.q.submit(W.Job("ra%d" % i, "row.accept", "idem-ra%d" % i, (("row", h), ("verification", rh)))); done += b.sup.run_until_idle(20)
        return done, rh
    def accepted(self, i): return [json.loads(r.body_json) for r in self.base.rig.journals.journal(RA.row_namespace(self.out[i][0])).read_from(1)] if self.base.rig.journals.journal(RA.row_namespace(self.out[i][0])).head().seq else []
    def test_children_verify_and_accept_rows_then_rows_publish_and_deliver_to_FW_and_ML(self):
        rhs = []
        for i in (0, 1):
            done, rh = self.run_jobs(i); self.assertEqual([d[1] for d in done], ["DONE", "DONE"]); self.assertIsNotNone(rh); rhs.append(rh)
        self.assertNotEqual(rhs[0], rhs[1])                                                                                      # per-row verification identities differ
        recs = self.accepted(0); self.assertEqual([r["row_content_hash"] for r in recs], [self.out[0][1].row_hash, self.out[1][1].row_hash])
        for rec, rh, i in zip(recs, rhs, (0, 1)):                                                                                # each ROW_ACCEPTED names ITS OWN child-produced verification result
            self.assertEqual(rec["verification_evidence_ref"][3], rh); self.assertEqual(self.base.rig.store.get("sep/row-ver-by-row/" + self.out[i][1].row_hash)[0].decode(), rh)
        b = self.base; self.co._gf = lambda proj, c=b.c: _gw(proj, c, __import__("stage_a.storage.object_store", fromlist=["x"]).InMemoryObjectStore())
        rp = RP.RowPublication(self.co._path, b.rig.journals, self.rows, T, b.rig.store); res = self.co.recover_publication(self.fk)
        for i in (0, 1): self.co.publish_accepted_row(res, rp, self.out[i][1].row_hash, "SIM_CUR", sequence=i + 1, visible_at=50, published_projection_hash=RH, data_vintage_mode="ORIGINAL_AS_OBSERVED", source_or_causal_policy_ref=R("pol"))
        fid = RC.supplied().feature_id; b.c.declare_ancestry_complete(self.fk.key(), "src"); bind = G.HealthBinding(fid, self.fk.feature_version, I, I); b.c.associate_subject(self.fk.key(), bind, "assoc")
        e = dataclasses.replace(RC._entry(fid=fid, ver=self.fk.feature_version), expected_projection=self.out[0][0].published_projection_name); k = dict(binding=bind, now=12, ref=R("hl"), resolved_at=11, tables=GTAB)
        fw = self.co.deliver("fw-s", FI("FW", "M-s", "XAUUSD", "Ws"), e, I, I, 0, 60, res, **k); self.assertIsInstance(fw, G.Binding)
        ml = self.co.deliver_ml("ml-s", FI("ML", "D-s", "XAUUSD", "Ws"), e, I, I, 1, 60, res, row_id="row-s", generation_ref=R("gen"), vintage_mode="ORIGINAL_AS_OBSERVED", omissions=NONE_, exclusion_reason=lambda x: ("ENUM", "REASON", "X"), **k); self.assertTrue(ml.included)
        with self.assertRaises(Refusal) as ex: self.co.deliver("fw-u", FI("FW", "M-u", "XAUUSD", "Wu"), e, I, I, 2, 60, res, **k)                                     # row 2 never verified/accepted by a child
        self.assertEqual(ex.exception.code, "NON_DELIVERY")
    def test_accept_without_a_verifier_handler_link_and_a_failing_row_never_yield_acceptance(self):
        b = self.base; h = self.out[0][1].row_hash; b.q.submit(W.Job("ra", "row.accept", "idem-ra", (("row", h), ("verification", "0" * 64)))); done = b.sup.run_until_idle(20)
        self.assertEqual([d[1] for d in done][-1], "DEAD"); self.assertNotIn("DONE", [d[1] for d in done]); self.assertEqual(self.accepted(0), [])
        bad = StateRowBuilder(SCHEMA, T, enc, dec, dict(FX, feature_id=FID, feature_version=self.fk.feature_version, quant_manifest_hash=self.out[0][0].quant_manifest_hash, instrument_id=I, timeframe_id=I, materialization_version="mbad"))
        row, rc = RS.CommittedRowChain(bad, self.rows).step(lambda p, i: {"acc": 999.0, "vec": [999.0, 999.0]}, None, {"x": 1.0}, **rkw(0, origin=True))                      # a program that is NOT the reference
        b.q.submit(W.Job("rvb", "row.verify", "idem-rvb", (("row", rc.row_hash),))); self.assertEqual([d[1] for d in b.sup.run_until_idle(20)][-1], "DEAD"); self.assertIsNone(b.rig.store.get("sep/row-ver-by-row/" + rc.row_hash))
    def test_a_crash_after_the_accept_effect_before_the_reply_is_retried_to_exactly_one_ROW_ACCEPTED(self):
        self.base.sup.close(); os.environ["SALIX_SEP_CRASH_ONCE_DIR"] = self.crash.name; self.base.sup = ProcessSupervisor(self.base.q, dict(HS, **ROWHS), reply_timeout=90, max_attempts=3)
        done, rh = self.run_jobs(0); self.assertEqual([d[1] for d in done], ["DONE", "RETRY", "DONE"]); self.assertEqual(len(self.accepted(0)), 1)
    def test_without_the_supplied_profile_port_the_jobs_refuse_and_nothing_is_written(self):
        self.base.sup.close(); os.environ.pop("SALIX_ROW_PROFILE"); self.base.sup = ProcessSupervisor(self.base.q, dict(HS, **ROWHS), reply_timeout=90, max_attempts=1)
        done, rh = self.run_jobs(0); self.assertEqual([d[1] for d in done], ["DEAD"]); self.assertIsNone(rh); self.assertEqual(self.accepted(0), [])

    def test_a_mismatched_per_row_verification_reference_is_refused_and_writes_no_acceptance(self):
        d0, rh0 = self.run_jobs(0); d1, rh1 = self.run_jobs(1, accept=False); self.assertEqual(len(self.accepted(0)), 1)
        b = self.base; b.q.submit(W.Job("ra-x", "row.accept", "idem-ra-x", (("row", self.out[1][1].row_hash), ("verification", rh0)))); done = b.sup.run_until_idle(20)       # row 1 offered row 0's child result
        self.assertEqual([d[1] for d in done][-1], "DEAD"); self.assertNotIn("DONE", [d[1] for d in done]); self.assertEqual([r["row_content_hash"] for r in self.accepted(0)], [self.out[0][1].row_hash])
