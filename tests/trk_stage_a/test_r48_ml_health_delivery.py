"""R48/R49: Health carried-upstream impact at the ACTUAL ML consumer delivery (real separated path), supplied by `health.impact_supplier` from the governed ConsumerManifest closure.
Requiredness is DERIVED from the entry (never passed/demoted by the caller); a required use with no supplier is BLOCKED; the consumer relation is the manifest registry, not two caller assertions.
Source-held: the failed-subject source, the lineage graph instance, and the consequence for an UNDETERMINED NON-REQUIRED use (named only)."""
import unittest
from stage_a.gateway import contracts as G
from stage_a.ml import consumer_path as CP, dataset_manifest as DM, dataset_authority as DA, generation_lifecycle as GL, writer_finalizer as WF
from stage_a.fw import lanes as LN
from stage_a.tracker.health_wiring import make_supplier as HS
from .health_fixtures import ml_supplier
from .test_r41_separated_caller import FB, supplied, AP, T, R
from .test_r35_dataset_manifest import ds
from .test_r29_generation_lifecycle import man, ev
from .test_r43_ml_integration import MLIntegration, NONE_, EXCL
from .test_r46_ml_j2 import J2Correlation

class HealthDelivery(J2Correlation):
    test_j2_naming_another_known_feature_does_not_pass_but_the_genuine_j2_and_unrelated_baseline_do = None
    def test_health_impact_at_delivery(self):
        pb, fkb, cob = self._feature("mom4", 2)
        rb = cob.accept_and_publish(pb, supplied(feature_id=FB), "SIM_CUR", sequence=1, now=10, max_age=50, l2_applicability=AP, accept_fn=self.acc)
        self.c.declare_ancestry_complete(fkb.key(), "src")
        reg = GL.GenerationRegistry(); wf = WF.GenerationAuthority(reg, {"MANIFEST_WRITER": {"w1"}, "FINALIZER": {"f1"}}, "TEST-LABELS-NOT-PRINCIPALS")
        wf.write_manifest("w1", man("G1")); wf.finalize("f1", "G1", 10, "cert")
        dsr = DM.DatasetRegistry({"w"}, "TEST-GRANT-LABEL"); auth = DA.DatasetAuthority(dsr, reg); dsr.register("w", ds("D1")); auth.declare_union("w", "D1", ())
        eb, ob = self._ml(cob, fkb, rb, "B1", FB, "BIND-B1"); self.assertIsInstance(ob, G.Binding)
        cat = {(eb.feature_id.hex(), eb.feature_version): ("d", "f", "g")}
        def go(**k):
            j = self.joins(eb, "BIND-B1", "D1", "G1", reg.manifest_of("G1"), reg)
            return CP.MLConsumerPath(gateway=cob.gateway, final_store=cob.gateway.final_store, authority=auth, generations=reg, writer=wf, tables=T).consume(
                "w", ds("D1"), eb, ob, "ml-B1", row_id="row-B1", generation_ref=R("gen"), generation_manifest_id="G1", event=ev(100), request_start_ts=100, fence=10,
                eligibility_reason=NONE_, exclusion_reason_for_missing=lambda x: EXCL, catalog_snapshot=cat, joins=j, **k)
        Q = b"\x01" * len(eb.feature_id); other = b"\x4a" * len(eb.feature_id)
        base = go(); self.assertIn("HEALTH_IMPACT_NOT_EVALUATED_FOR_REQUIRED_USE", base.blockers); self.assertFalse(base.usable_for_simulation)      # omission never allows a REQUIRED use
        ok = go(health=ml_supplier(eb)); self.assertEqual(ok.blockers, ()); self.assertTrue(ok.usable_for_simulation); self.assertFalse(ok.qualified)          # genuine, no failed subject known
        ok2 = go(health=ml_supplier(eb, failed=(Q,), deps={eb.feature_id: ()})); self.assertEqual(ok2.blockers, ())                                       # failed subject, proven independent baseline delivers
        aff = go(health=ml_supplier(eb, failed=(Q,), deps={eb.feature_id: (Q,)}, closure=(eb.feature_id,)))
        self.assertIn("HEALTH_PROVEN_DEPENDENCY_ON_FAILED_SUBJECT", aff.blockers)                                                                            # failed subject reachable through lineage
        self.assertIn("HEALTH_PROVEN_DEPENDENCY_ON_FAILED_SUBJECT", go(health=ml_supplier(eb, failed=(eb.feature_id,))).blockers)                            # the consumed feature itself failed
        un = go(health=ml_supplier(eb, failed=(Q,), deps={}))                                                                                                 # lineage of the consumed feature unread
        self.assertTrue(any(b.startswith("HEALTH_REQUIRED_ANCESTRY_UNPROVEN") for b in un.blockers)); self.assertFalse(un.usable_for_simulation)
        self.assertIn("HEALTH_REFUSE_CONSUMER_UNBOUND", go(health=ml_supplier(eb, dsid="OTHER")).blockers)                                                    # supplier knows another consumer only
        self.assertIn("HEALTH_REFUSE_CONSUMER_UNBOUND", go(health=ml_supplier(eb, kind="FW")).blockers)                                                      # wrong kind
        self.assertIn("HEALTH_REFUSE_ENTRY_NOT_IN_CONSUMER_CLOSURE", go(health=ml_supplier(eb, closure=(other,))).blockers)                                  # entry is not this consumer's dependency
        self.assertIn("HEALTH_REFUSE_HEALTH_UNREADABLE", go(health=HS({"D1": LN.ConsumerManifest("D1", "ML", (eb.feature_id,))}, {eb.feature_id: ()}, lambda: 1 / 0)).blockers)
        s_ = ml_supplier(eb, failed=(Q,), deps={}); use, imp = s_.decide("D1", "ML", eb); self.assertEqual(use, "REFUSE_UNPROVEN_INDEPENDENCE")
        import dataclasses
        opt = dataclasses.replace(eb, requirement_class=G.OPTIONAL, absence_rule_ref=eb.scope_ref)
        use, _ = s_.decide("D1", "ML", opt); self.assertEqual(use, "NO_SOURCE_RULE_UNDETERMINED_NON_REQUIRED_USE")                                          # named, not decided
        self.assertEqual(s_.decide("D1", "ML", dataclasses.replace(opt, requirement_class=G.REQUIRED, absence_rule_ref=None))[0], "REFUSE_UNPROVEN_INDEPENDENCE")   # requiredness comes from the entry
if __name__ == "__main__": unittest.main()


class FWHealth(unittest.TestCase):
    """The SAME supplier on the ACTUAL composed FW delivery (Composition.deliver): block/refuse before resolution, baseline delivers."""
    def test_fw_delivery_uses_supplier_and_baseline_still_delivers(self):
        from .test_r38_composition import comp, F, I, W, AP, _entry
        from stage_a.errors import Refusal
        rig, pkg, fk, c, co, path = comp(); key = fk.key(); r = co.accept_and_publish(pkg, supplied(), "SIM_CUR", sequence=1, now=10, max_age=50, l2_applicability=AP)
        c.declare_ancestry_complete(key, "src"); b1 = G.HealthBinding(F, fk.feature_version, I, I); c.associate_subject(key, b1, "assoc"); e = _entry(fid=F, ver=fk.feature_version)
        kw = dict(binding=b1, now=12, ref=R("hl"), resolved_at=11, tables=T)
        Q = b"\x01" * len(F)
        def go(n, sup, mid="MF1"): return co.deliver("fw-" + n, W("W" + n), e, I, I, 3, 20, r, health=sup, consumer_manifest_id=mid, **kw)
        def code(sup, **k):
            with self.assertRaises(Refusal) as x: go("x", sup, **k)
            return x.exception.code
        self.assertIsInstance(go("1", ml_supplier(e, "MF1", kind="FW")), G.Binding)                                                       # baseline positive
        self.assertIsInstance(go("2", ml_supplier(e, "MF1", kind="FW", failed=(Q,), deps={F: ()})), G.Binding)                           # failed subject elsewhere, proven independent
        self.assertEqual(code(ml_supplier(e, "MF1", kind="FW", failed=(Q,), deps={F: (Q,)})), "HEALTH_IMPACT_BLOCK_PROVEN_DEPENDENCY")
        self.assertEqual(code(ml_supplier(e, "MF1", kind="FW", failed=(Q,), deps={})), "HEALTH_IMPACT_REFUSE_UNPROVEN_INDEPENDENCE")
        self.assertEqual(code(ml_supplier(e, "MF1", kind="ML")), "HEALTH_IMPACT_REFUSE_CONSUMER_UNBOUND")
        self.assertEqual(code(ml_supplier(e, "MF1", kind="FW"), mid="NOPE"), "HEALTH_IMPACT_REFUSE_CONSUMER_UNBOUND")
