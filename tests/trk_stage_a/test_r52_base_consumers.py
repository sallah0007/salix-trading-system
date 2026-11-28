"""R52: an INDEPENDENT BASE feature (its own order, ClaimService claim, pipeline acceptance, Core re-verification and own supplied ancestry declaration) is ACTUALLY delivered to BOTH the FW and the ML consumer through the same Core + durable window Gateway WHILE the affected feature's required ancestry stays UNKNOWN. The affected feature is never cleared in this test (clearing then delivering is not this control); its denial is asserted before, between and after the BASE deliveries.
Simulated Gateway, in-memory stores, synthetic gateway rows: nothing here is a provider, an acceptance or a gate."""
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
from .fixtures import Rig, package, SIM_CONF, momentum_manifest
from .strict_gateway import sgw
from .test_boundaries import _entry, _row, I, R
from .test_r25_scheduler import core, ver
from .test_r29_intake_order import issue, br, rec, lk
from .test_r24_core import T, NONE_
def code(f, *a, **k):
    try: f(*a, **k)
    except Refusal as e: return e.code
class BaseWhileAffectedUnknown(unittest.TestCase):
    def build(self):
        rig = Rig(); keys = {}
        for cand, fid, rid, att, win in (("cand-1", "mom3", "REQ-1", "ATT-1", 3), ("cand-2", "base7", "REQ-2", "ATT-2", 5)):          # the BASE has a genuinely DIFFERENT program (identical content would be the same subject: SUBJECT_ALREADY_CLAIMED)
            oid = OA.order_id_for(cand); p = package(momentum_manifest(feature_id=fid, window=win), order_id=oid, request_id=rid, attempt_id=att, package_id="PKG-" + rid); a = admit(p, accepted_fit_generations=rig.fits, conformance=SIM_CONF)
            issue(rig.claims, rec(CANDIDATE_IDENTITY=cand), subject_key=a.subject_key); abs_(rig.claims, oid, br(CANDIDATE_IDENTITY=cand)); out = rig.pipe.run(p); self.assertEqual(out.accepted.kind, "CANONICAL_ACCEPTED", cand); keys[cand] = a.feature_key
        ka, kb = keys["cand-1"], keys["cand-2"]; self.assertNotEqual(ka.key(), kb.key()); c = core(); c.declare_dependency(ka.key(), "UP"); ver(c, "UP", version="1", at=9, age=50)
        for k in (ka, kb):
            res, st = RV.reverify_accepted(c, journal=rig.journals.journal(k.namespace()), store=rig.store, feature_key=k, now=10, max_age=50); self.assertEqual(res.status, "PASS")
        FB = b"\x02" * 16; ba = G.HealthBinding(I, ka.feature_version, I, I); bb = G.HealthBinding(FB, kb.feature_version, I, I)
        c.associate_subject(ka.key(), ba, "assoc-affected"); c.associate_subject(kb.key(), bb, "assoc-base"); c.declare_ancestry_complete(kb.key(), "src-base")                       # ONLY the BASE feature's own ancestry is declared (supplied ref)
        gw = sgw(c); gw.final_store = D.DurableFinalResolutionStore(InMemoryObjectStore()); gw.set_watermark(100); gw.publish(_row(fid=FB, ver=kb.feature_version)); gw.status.append(C.StatusFact((FB, kb.feature_version, I, I, "m1"), 1, C.CURRENT, 1, False))
        hs = lambda k, b: c.gateway_health(k.key(), k.feature_version, 12, R("hl"), 11, binding=b, require_ancestry=True)
        return c, ka, kb, ba, bb, FB, gw, hs
    def test_base_delivers_to_fw_and_ml_while_the_affected_required_ancestry_stays_unknown_before_between_and_after(self):
        c, ka, kb, ba, bb, FB, gw, hs = self.build(); ea = _entry(ver=ka.feature_version); eb = _entry(fid=FB, ver=kb.feature_version)
        def affected(tag, cons, win):
            return gw.resolve_window("%s-a" % tag, FI(cons, "A-" + cons, "XAUUSD", win), ea, I, I, 3, 20, hs(ka, ba))
        a1 = affected("fw1", "FW", "W1"); self.assertEqual((type(a1).__name__, a1.reason), ("NonDeliveryResolution", "HEALTH_UNACCEPTABLE")); self.assertEqual(code(FWR.receive_verified, a1, ea, I, I, T, gw), "NON_DELIVERY")                    # BEFORE
        fw = gw.resolve_window("fw-b", FI("FW", "B-FW", "XAUUSD", "W1"), eb, I, I, 3, 20, hs(kb, bb)); self.assertIsInstance(fw, G.Binding); self.assertIs(FWR.receive_verified(fw, eb, I, I, T, gw), fw)                  # BASE -> FW, actual delivery
        a2 = affected("ml1", "ML", "W1"); self.assertEqual((type(a2).__name__, a2.reason), ("NonDeliveryResolution", "HEALTH_UNACCEPTABLE"))                                                                                    # BETWEEN
        ml = gw.resolve_window("ml-b", FI("ML", "B-ML", "XAUUSD", "W1"), eb, I, I, 3, 20, hs(kb, bb)); self.assertIsInstance(ml, G.Binding); row = MLR.build_row("r-b", R("gen"), [eb], [ml], gw, "ORIGINAL_AS_OBSERVED", NONE_, lambda o: None, tables=gw.t)
        self.assertTrue(row.included); self.assertEqual(len(row.bindings), 1)                                                                                                                                              # BASE -> ML, actual delivery, callback never consulted
        self.assertIsNot(fw, ml); self.assertEqual(code(MLR.build_row, "r-x", R("gen"), [eb], [fw], gw, "ORIGINAL_AS_OBSERVED", NONE_, lambda o: None, tables=gw.t), "BINDING_NOT_FROM_GATEWAY")                               # FW's Binding is not ML's
        self.assertEqual(type(affected("fw2", "FW", "W2")).__name__, "NonDeliveryResolution"); self.assertEqual(type(affected("ml2", "ML", "W2")).__name__, "NonDeliveryResolution")                                      # AFTER (new windows, both consumers)
        self.assertTrue(c._ancestry_blocks(c._replay(), ka.key())); self.assertFalse(c._ancestry_blocks(c._replay(), kb.key())); self.assertEqual(c.recording_health(ka.key(), ka.feature_version, 12).local_state, "HEALTHY")    # affected ancestry STILL unknown; its LOCAL health untouched
    def test_without_the_base_features_own_ancestry_declaration_the_base_is_not_delivered_so_the_control_is_not_vacuous(self):
        c, ka, kb, ba, bb, FB, gw, hs = self.build(); c2 = core(); c2.declare_dependency(ka.key(), "UP")                                                                                                                  # a Core where nobody declared BASE ancestry
        ver(c2, "UP", version="1", at=9, age=50); ver(c2, kb.key(), version=kb.feature_version, at=9, age=50); c2.associate_subject(kb.key(), bb, "assoc-base")
        h = c2.gateway_health(kb.key(), kb.feature_version, 12, R("hl"), 11, binding=bb, require_ancestry=True); self.assertFalse(h.acceptable if hasattr(h, "acceptable") else h.ok)
if __name__ == "__main__": unittest.main()
