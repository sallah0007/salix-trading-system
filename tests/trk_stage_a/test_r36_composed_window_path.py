"""R36: ONE composed candidate path (explicit simulation) THROUGH THE WINDOW GATEWAY: order -> build gate -> actual TrackerPipeline.run (CANONICAL_ACCEPTED) -> Core real re-verification of THAT accepted record -> Core health (required unknown ancestry) -> `resolve_window` with the DURABLE final store
-> FW and ML consumers read the consumer-qualified outcome. Same path: unknown required ancestry fails closed (NON_DELIVERY at FW, refused at ML), an UNRELATED baseline is delivered, declaring ancestry complete delivers a NEW window, a restart returns the stored outcome without re-evaluation.
Simulated Gateway, in-memory object store: nothing here is a real provider or an acceptance."""
import json, unittest
from stage_a.errors import Refusal
from stage_a.gateway import contracts as G, durable_final_store as D
from stage_a.gateway.v038 import FinalResolutionIdentity as FI
from stage_a.storage.object_store import InMemoryObjectStore
from stage_a.tracker import chain_status as C, reverification as RV
from stage_a.tracker.quant_intake_adapter import admit
from stage_a.composer import order_authority as OA
from stage_a.composer.build_gate import accept_build_start as abs_
from stage_a.fw import receiver as FWR
from stage_a.ml import receiver as MLR
from .fixtures import Rig, package, SIM_CONF
from .strict_gateway import sgw
from .test_boundaries import _entry, _row, I, R
from .test_r25_scheduler import core, ver
from .test_r29_intake_order import issue, br
from .test_r24_core import T, NONE_
def code(f, *a, **k):
    try: f(*a, **k)
    except Refusal as e: return e.code
class WindowPath(unittest.TestCase):
    def build(self):
        rig = Rig(); oid = OA.order_id_for("cand-1"); p = package(order_id=oid); sk = admit(p, accepted_fit_generations=rig.fits, conformance=SIM_CONF).subject_key
        issue(rig.claims, subject_key=sk); abs_(rig.claims, oid, br()); out = rig.pipe.run(p); self.assertEqual(out.accepted.kind, "CANONICAL_ACCEPTED")
        fk = admit(p, accepted_fit_generations=rig.fits, conformance=SIM_CONF).feature_key; key = json.loads(out.accepted.body_json)["feature_key"]; self.assertEqual(fk.key(), key); c = core()
        c.declare_dependency(key, "UP"); ver(c, "UP", version="1", at=9, age=50); ver(c, "BASE", version="1", at=9, age=50)
        res, st = RV.reverify_accepted(c, journal=rig.journals.journal(fk.namespace()), store=rig.store, feature_key=fk, now=10, max_age=50); self.assertEqual((res.status, st), ("PASS", "ACCEPTED_RECORD_AS_FOUND"))
        F2 = b"\x02" * 16; b1 = G.HealthBinding(I, "1", I, I); b2 = G.HealthBinding(F2, "1", I, I)
        c.associate_subject(key, b1, "assoc-accepted"); c.associate_subject("BASE", b2, "assoc-base"); c.declare_ancestry_complete("BASE", "src")
        raw = InMemoryObjectStore(); gw = sgw(c); gw.final_store = D.DurableFinalResolutionStore(raw); gw.set_watermark(100); gw.publish(_row(fid=F2, ver="1")); gw.status.append(C.StatusFact((F2, "1", I, I, "m1"), 1, C.CURRENT, 1, False))
        hs = lambda subj, b: c.gateway_health(subj, "1", 12, R("hl"), 11, binding=b, require_ancestry=True)
        return c, key, F2, b1, b2, raw, gw, hs
    def test_same_path_required_unknown_ancestry_fails_closed_unrelated_baseline_delivers_and_restart_never_reevaluates(self):
        c, key, F2, b1, b2, raw, gw, hs = self.build(); e1 = _entry(ver="1"); eb = _entry(fid=F2, ver="1")
        dep = gw.resolve_window("fw-d1", FI("FW", "B-DEP", "XAUUSD", "WIN-1"), e1, I, I, 3, 20, hs(key, b1)); self.assertEqual((type(dep).__name__, dep.reason), ("NonDeliveryResolution", "HEALTH_UNACCEPTABLE"))
        self.assertEqual(code(FWR.receive_verified, dep, e1, I, I, T, gw), "NON_DELIVERY")                                         # consumer-qualified outcome, through the window path
        base = gw.resolve_window("fw-b1", FI("FW", "B-BASE", "XAUUSD", "WIN-1"), eb, I, I, 3, 20, hs("BASE", b2)); self.assertIsInstance(base, G.Binding); self.assertIs(FWR.receive_verified(base, eb, I, I, T, gw), base)      # unrelated BASE delivered, SAME path
        self.assertEqual(c.recording_health(key, "1", 12).local_state, "HEALTHY")                                                  # carried-upstream denial never overwrote LOCAL_STATE
        c.declare_ancestry_complete("UP", "src"); c.declare_ancestry_complete(key, "src")
        again = gw.resolve_window("fw-d2", FI("FW", "B-DEP", "XAUUSD", "WIN-1"), e1, I, I, 3, 20, hs(key, b1)); self.assertEqual(type(again).__name__, "NonDeliveryResolution"); self.assertEqual(gw.final_store.evaluations, 2)             # SAME window: the stored outcome is reused, no re-evaluation
        d2 = gw.resolve_window("fw-d3", FI("FW", "B-DEP", "XAUUSD", "WIN-2"), e1, I, I, 3, 20, hs(key, b1)); self.assertIsInstance(d2, G.Binding); self.assertIs(FWR.receive_verified(d2, e1, I, I, T, gw), d2)                               # a NEW window delivers
        m = gw.resolve_window("ml-d1", FI("ML", "DS-B1", "XAUUSD", "WIN-2"), e1, I, I, 3, 20, hs(key, b1)); self.assertTrue(MLR.build_row("r-w", R("gen"), [e1], [m], gw, "ORIGINAL_AS_OBSERVED", NONE_, lambda o: NONE_, tables=gw.t).included)        # ML's OWN window outcome
        self.assertEqual(code(MLR.build_row, "r-w2", R("gen"), [e1], [d2], gw, "ORIGINAL_AS_OBSERVED", NONE_, lambda o: NONE_, tables=gw.t), "BINDING_NOT_FROM_GATEWAY")            # FW's window Binding is not ML's issued outcome
        gw2 = sgw(c); gw2.final_store = D.DurableFinalResolutionStore(raw); gw2.set_watermark(0); gw2.final_store.recover(); gw2.publish(_row(fid=F2, ver="1"))
        r = gw2.resolve_window("fw-after-restart", FI("FW", "B-DEP", "XAUUSD", "WIN-2"), e1, I, I, 3, 20, hs(key, b1)); self.assertEqual(r, d2); self.assertEqual(gw2.final_store.evaluations, 0)                                 # restart: stored outcome, the world has moved (watermark 0) and nothing re-decides
    def test_the_same_path_without_the_window_store_is_refused_and_a_forged_dependent_outcome_is_not_consumable(self):
        c, key, F2, b1, b2, raw, gw, hs = self.build(); e1 = _entry(ver="1"); c.declare_ancestry_complete("UP", "src"); c.declare_ancestry_complete(key, "src")
        d = gw.resolve_window("fw-1", FI("FW", "B-DEP", "XAUUSD", "WIN-1"), e1, I, I, 3, 20, hs(key, b1)); self.assertIsInstance(d, G.Binding)
        forged = G.Binding("fw-forged", d.entry, d.delivered_feature_hash, d.fence); self.assertIsNotNone(code(FWR.receive_verified, forged, e1, I, I, T, gw))
        gw.final_store = None; self.assertEqual(code(gw.resolve_window, "x", FI("FW", "B", "X", "W"), e1, I, I, 3, 20, hs(key, b1)), "GATEWAY_FINAL_RESOLUTION_STORE_NOT_CONFIGURED")
if __name__ == "__main__": unittest.main()
