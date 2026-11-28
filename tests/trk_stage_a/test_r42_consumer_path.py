"""R42: the separated caller/child acceptance path carried through the committed SIM status/Core/Gateway into BOTH consumers: FW receiver and the ML row builder, then the ML writer/finalizer facade and the six-join checker. Required unknown ancestry is denied (FW non-delivery; ML row EXCLUDED) and an UNRELATED baseline feature is really delivered to both consumers (a Binding re-verified by the consumer, not Health-only). Nothing here maps PUBLISHABLE=CURRENT or SIM->QUALIFIED, and the grants/principals are test-supplied labels."""
import unittest
from stage_a.errors import Refusal
from stage_a.fw import receiver as FWR
from stage_a.gateway import contracts as G
from stage_a.gateway.v038 import FinalResolutionIdentity as FI
from stage_a.ml import receiver as MLR, generation_lifecycle as GL, writer_finalizer as WF, six_joins as SJ
from .test_r41_separated_caller import Caller as _Caller, FB, supplied, AP, I, T, R, _entry, ver
from .test_r29_generation_lifecycle import man
NONE_ = ("ENUM", "REASON", "NONE"); EXCL = ("ENUM", "REASON", "REQUIRED_DEPENDENCY_NOT_DELIVERED")
class BothConsumers(_Caller):
    test_separated_child_acceptance_then_committed_status_core_gateway_with_unknown_ancestry_denied_and_the_unrelated_baseline_delivered = None
    test_a_failed_child_job_never_yields_an_acceptance_or_publication = None
    test_a_non_admissible_package_is_not_staged_claimed_or_run = None
    def _consumer(self, co, fk, r, consumer, tag, fid):
        self.c.declare_ancestry_complete(fk.key(), "src"); b = G.HealthBinding(fid, fk.feature_version, I, I); self.c.associate_subject(fk.key(), b, "assoc"); e = _entry(fid=fid, ver=fk.feature_version)
        health = self.c.gateway_health(fk.key(), fk.feature_version, 12, R("hl-" + tag), 11, binding=b, require_ancestry=True)          # the composed Core Health, as Composition.deliver reads it
        o = co.gateway.resolve_window(consumer.lower() + "-" + tag, FI(consumer, "M-A", "XAUUSD", tag), e, I, I, 3, 20, health); return e, o
    def test_unknown_ancestry_is_denied_and_the_unrelated_baseline_is_delivered_to_both_the_fw_receiver_and_the_ml_row_builder_after_separated_acceptance(self):
        pa, fka, coa = self._feature("mom3", 1); pb, fkb, cob = self._feature("mom4", 2); coa._up = {fka.key(): ("UP",)}; ver(self.c, "UP", version="1", at=9, age=50)
        ra = coa.accept_and_publish(pa, supplied(), "SIM_CUR", sequence=1, now=10, max_age=50, l2_applicability=AP, accept_fn=self.acc)
        rb = cob.accept_and_publish(pb, supplied(feature_id=FB), "SIM_CUR", sequence=1, now=10, max_age=50, l2_applicability=AP, accept_fn=self.acc)
        self.assertEqual((ra.status, rb.status), ("PUBLISHED_SIMULATION", "PUBLISHED_SIMULATION"))
        self.c.declare_ancestry_complete(fkb.key(), "src")
        # ---- FW consumer
        ea, oa = self._consumer(coa, fka, ra, "FW", "A1", supplied().feature_id); self.assertEqual(type(oa).__name__, "NonDeliveryResolution")
        eb, ob = self._consumer(cob, fkb, rb, "FW", "B1", FB); self.assertIsInstance(ob, G.Binding); self.assertIs(FWR.receive_verified(ob, eb, I, I, T, cob.gateway), ob)
        with self.assertRaises(Refusal) as nx: FWR.receive_verified(oa, ea, I, I, T, coa.gateway)
        self.assertEqual(nx.exception.code, "NON_DELIVERY")
        # ---- ML consumer: the same committed status, a different consumer identity at the same Gateway
        ea2, oa2 = self._consumer(coa, fka, ra, "ML", "A1", supplied().feature_id); self.assertEqual(type(oa2).__name__, "NonDeliveryResolution")
        eb2, ob2 = self._consumer(cob, fkb, rb, "ML", "B1", FB); self.assertIsInstance(ob2, G.Binding)
        rowa = MLR.build_row("rowA", R("gen"), [ea2], [oa2], coa.gateway, "ORIGINAL_AS_OBSERVED", NONE_, lambda o: EXCL, tables=T); self.assertFalse(rowa.included)
        rowb = MLR.build_row("rowB", R("gen"), [eb2], [ob2], cob.gateway, "ORIGINAL_AS_OBSERVED", NONE_, lambda o: EXCL, tables=T); self.assertTrue(rowb.included)
        with self.assertRaises(Refusal) as x: MLR.build_row("rowX", R("gen"), [eb2], [ob2], coa.gateway, "ORIGINAL_AS_OBSERVED", NONE_, lambda o: EXCL, tables=T)          # a Binding issued by a DIFFERENT gateway is not this one's
        self.assertEqual(x.exception.code, "BINDING_NOT_FROM_GATEWAY")
        # ---- after the denied feature's ancestry completes, it is delivered to ML too (the denial was the ancestry, not the path)
        self.c.declare_ancestry_complete("UP", "src"); ea3, oa3 = self._consumer(coa, fka, ra, "ML", "A2", supplied().feature_id); self.assertIsInstance(oa3, G.Binding)
        self.assertTrue(MLR.build_row("rowA2", R("gen"), [ea3], [oa3], coa.gateway, "ORIGINAL_AS_OBSERVED", NONE_, lambda o: EXCL, tables=T).included)
    def test_the_ml_writer_finalizer_facade_and_six_joins_after_that_delivery_stay_unqualified(self):
        r = GL.GenerationRegistry(); a = WF.GenerationAuthority(r, {"MANIFEST_WRITER": {"w1"}, "FINALIZER": {"f1"}}, "TEST-LABELS-NOT-PRINCIPALS"); a.write_manifest("w1", man("M1")); a.finalize("f1", "M1", 10, "cert")
        self.assertEqual(a.correlate("M1")["status"], "VERIFIED_AGAINST_REGISTRY"); self.assertFalse(a.correlate("M1")["qualified"])
        self.assertFalse(SJ.check_six_joins({}, r, fence=10).qualified)
if __name__ == "__main__": unittest.main()
