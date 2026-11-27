"""R33: ONE composed candidate path in explicit simulation: ClaimService order (via the order facade) -> build gate -> actual TrackerPipeline.run (CANONICAL_ACCEPTED) -> Core real re-verification of THAT accepted feature -> Core health snapshot -> actual SimulatedGateway.resolve. No second registry/issuer/Gateway. Subject->dependency association, ancestry declarations and the simulated gateway rows are SUPPLIED and UNADMITTED; nothing here is qualified."""
import json, unittest
from stage_a.gateway import contracts as G
from stage_a.tracker import chain_status as C
from stage_a.tracker import reverify_scheduler as S
from stage_a.composer.expression.manifest import Manifest
from stage_a.tracker.quant_intake_adapter import admit
from stage_a.composer import order_authority as OA
from stage_a.composer.build_gate import accept_build_start as abs_
from .fixtures import Rig, package, SIM_CONF, momentum_manifest
from .strict_gateway import sgw
from .test_boundaries import _entry, _row, I, R
from .test_r25_scheduler import core, ver, declared, SIMS
from .test_r29_intake_order import issue, br

class ComposedOrderToConsumer(unittest.TestCase):
    def test_order_to_pipeline_to_core_health_to_gateway_with_required_unknown_ancestry_and_unrelated_baseline(self):
        rig = Rig(); oid = OA.order_id_for("cand-1"); p = package(order_id=oid)
        sk = admit(p, accepted_fit_generations=rig.fits, conformance=SIM_CONF).subject_key
        self.assertEqual(issue(rig.claims, subject_key=sk)["order_id"], oid); abs_(rig.claims, oid, br())
        out = rig.pipe.run(p); self.assertEqual(out.accepted.kind, "CANONICAL_ACCEPTED")
        key = json.loads(out.accepted.body_json)["feature_key"]                                                   # the ACCEPTED feature, not a literal
        m = Manifest.from_dict(momentum_manifest()); c = core()
        c.declare_dependency(key, "UP"); ver(c, "UP", version="1", at=9, age=50); ver(c, "BASE", version="1", at=9, age=50)                 # upstream evidence precedes the dependent's
        res = S.reverify_pinned(c, manifest=m, declared=declared(m), store=SIMS(), now=10, max_age=50)[0]; self.assertEqual(res.status, "PASS")
        self.assertEqual(c.recording_health(key, "1", 11).state, "HEALTHY")                                       # same key the pipeline accepted
        F2 = b"\x02" * 16; b1 = G.HealthBinding(I, "1", I, I); b2 = G.HealthBinding(F2, "1", I, I)
        c.associate_subject(key, b1, "assoc-accepted"); c.associate_subject("BASE", b2, "assoc-base"); c.declare_ancestry_complete("BASE", "src")
        gw = sgw(c); gw.publish(_row(fid=F2, ver="1")); gw.status.append(C.StatusFact((F2, "1", I, I, "m1"), 1, C.CURRENT, 1, False))
        def hs(subj, b): return c.gateway_health(subj, "1", 12, R("hl"), 11, binding=b, require_ancestry=True)
        dep = gw.resolve("d1", _entry(ver="1"), I, I, 3, 20, hs(key, b1)); self.assertEqual((type(dep).__name__, dep.reason), ("NonDeliveryResolution", "HEALTH_UNACCEPTABLE"))        # required ancestor undeclared => fail closed
        self.assertIsInstance(gw.resolve("b1", _entry(fid=F2, ver="1"), I, I, 3, 20, hs("BASE", b2)), G.Binding)                                                                 # unrelated baseline delivered
        self.assertEqual(c.recording_health(key, "1", 12).local_state, "HEALTHY")                                    # Build Plan 14A: the carried-upstream denial never overwrites the subject's LOCAL_STATE
        c.declare_ancestry_complete("UP", "src"); c.declare_ancestry_complete(key, "src")
        self.assertIsInstance(gw.resolve("d2", _entry(ver="1"), I, I, 3, 20, hs(key, b1)), G.Binding)             # declared complete + healthy => delivered
    def test_qualified_rig_holds_an_unadmitted_issuer_before_any_pipeline_work(self):
        q = Rig(simulation=False)
        with self.assertRaises(Exception) as cm: abs_(q.claims, issue(q.claims, issued_by="UNADMITTED")["order_id"], br())
        self.assertEqual(getattr(cm.exception, "code", ""), "COMPOSER_BUILD_ORDER_NOT_VERIFIED:ISSUER_NOT_ANCHORED")
if __name__ == "__main__": unittest.main()
