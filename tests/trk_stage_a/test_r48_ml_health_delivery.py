"""R48: Health carried-upstream impact applied at the ACTUAL ML consumer delivery (real separated path). Required-unknown ancestry is denied, a proven dependency blocks, the unrelated
proven-independent baseline still delivers, a foreign consumer's impact cannot allow this consumer, and an omitted impact is held visibly. Source-held: who computes/supplies the impact and the non-required UNDETERMINED consequence."""
import unittest
from stage_a.gateway import contracts as G
from stage_a.ml import consumer_path as CP, dataset_manifest as DM, dataset_authority as DA, generation_lifecycle as GL, writer_finalizer as WF
from stage_a.health.blast_radius import CarriedUpstreamImpact as CI, AFFECTED, UNAFFECTED, UNDETERMINED
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
        Q = b"\x01" * 4
        imp = lambda v, c="CONS1", r="": CI(c, v, Q, (), r)
        base = go(); self.assertEqual(base.blockers, ()); self.assertIn("HEALTH_CARRIED_UPSTREAM_IMPACT_NOT_EVALUATED", base.held)       # omitted impact is visible
        ok = go(health_impact=imp(UNAFFECTED), health_consumer_id="CONS1"); self.assertEqual(ok.blockers, ()); self.assertTrue(ok.usable_for_simulation); self.assertNotIn("HEALTH_CARRIED_UPSTREAM_IMPACT_NOT_EVALUATED", ok.held)   # unrelated baseline delivers
        self.assertIn("HEALTH_PROVEN_DEPENDENCY_ON_FAILED_SUBJECT", go(health_impact=imp(AFFECTED), health_consumer_id="CONS1").blockers)
        un = go(health_impact=imp(UNDETERMINED, r="DERIVED_FROM_UNRESOLVED"), health_consumer_id="CONS1"); self.assertIn("HEALTH_REQUIRED_ANCESTRY_UNPROVEN:DERIVED_FROM_UNRESOLVED", un.blockers); self.assertFalse(un.usable_for_simulation)
        nr = go(health_impact=imp(UNDETERMINED), health_consumer_id="CONS1", health_required=False); self.assertEqual(nr.blockers, ()); self.assertIn("HEALTH_NO_SOURCE_RULE_UNDETERMINED_NON_REQUIRED_USE", nr.held)
        self.assertIn("HEALTH_IMPACT_FOR_A_DIFFERENT_CONSUMER", go(health_impact=imp(UNAFFECTED, c="OTHER"), health_consumer_id="CONS1").blockers)           # foreign verdict cannot allow
        self.assertIn("HEALTH_IMPACT_FOR_A_DIFFERENT_CONSUMER", go(health_impact=imp(UNAFFECTED)).blockers)                                              # no consumer id => cannot bind
        self.assertIn("HEALTH_IMPACT_FOR_A_DIFFERENT_CONSUMER", go(health_impact=CI(None, UNAFFECTED, Q, (), "")).blockers)                                   # None == None must not bind
if __name__ == "__main__": unittest.main()
