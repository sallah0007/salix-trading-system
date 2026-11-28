"""R46 (root reproduction 2): J2 must list the features this consumer ACTUALLY consumed (exact id+version). Real separated path: acceptance -> committed SIM status
-> Core -> Gateway -> issued Binding -> dataset registry D1 -> writer/finalizer G1 -> MLConsumerPath.consume. Catalog membership of OTHER features is not evidence.
Unrelated baseline still delivers. Held (named): whether extra J2 entries beyond the consumed set are permitted is source-held; seeded candidate Gateway only."""
import unittest
from stage_a.gateway import contracts as G
from stage_a.ml import consumer_path as CP, dataset_manifest as DM, dataset_authority as DA, generation_lifecycle as GL, writer_finalizer as WF, six_joins as SJ
from .test_r41_separated_caller import FB, supplied, AP, T, R
from .test_r35_dataset_manifest import ds
from .test_r29_generation_lifecycle import man, ev
from .test_r43_ml_integration import MLIntegration, NONE_, EXCL

class J2Correlation(MLIntegration):
    test_separated_acceptance_to_both_consumers_then_ml_writer_dataset_union_request_reverse_h1_and_six_joins_on_the_same_objects = None
    test_ports_must_be_supplied = None
    test_the_ml_writer_finalizer_facade_and_six_joins_after_that_delivery_stay_unqualified = None
    def test_j2_naming_another_known_feature_does_not_pass_but_the_genuine_j2_and_unrelated_baseline_do(self):
        pa, fka, coa = self._feature("mom3", 1); pb, fkb, cob = self._feature("mom4", 2); coa._up = {fka.key(): ("UP",)}
        from .test_r41_separated_caller import ver; ver(self.c, "UP", version="1", at=9, age=50)
        ra = coa.accept_and_publish(pa, supplied(), "SIM_CUR", sequence=1, now=10, max_age=50, l2_applicability=AP, accept_fn=self.acc)
        rb = cob.accept_and_publish(pb, supplied(feature_id=FB), "SIM_CUR", sequence=1, now=10, max_age=50, l2_applicability=AP, accept_fn=self.acc)
        self.c.declare_ancestry_complete(fkb.key(), "src")
        reg = GL.GenerationRegistry(); wf = WF.GenerationAuthority(reg, {"MANIFEST_WRITER": {"w1"}, "FINALIZER": {"f1"}}, "TEST-LABELS-NOT-PRINCIPALS")
        wf.write_manifest("w1", man("G1")); wf.finalize("f1", "G1", 10, "cert")
        dsr = DM.DatasetRegistry({"w"}, "TEST-GRANT-LABEL"); auth = DA.DatasetAuthority(dsr, reg); dsr.register("w", ds("D1")); auth.declare_union("w", "D1", ())
        eb, ob = self._ml(cob, fkb, rb, "B1", FB, "BIND-B1"); self.assertIsInstance(ob, G.Binding)
        other = (b"\x4a" * len(eb.feature_id)).hex()                                      # a DIFFERENT known feature J with its own legitimate catalog entry
        cat = {(eb.feature_id.hex(), eb.feature_version): ("d", "f", "g"), (other, eb.feature_version): ("d", "f", "g")}
        def go(j2=None, **k):
            j = self.joins(eb, "BIND-B1", "D1", "G1", reg.manifest_of("G1"), reg)
            if j2 is not None: j["J2_INCLUDED_FEATURES"] = j2
            return CP.MLConsumerPath(gateway=cob.gateway, final_store=cob.gateway.final_store, authority=auth, generations=reg, writer=wf, tables=T).consume(
                "w", ds("D1"), eb, ob, "ml-B1", row_id="row-B1", generation_ref=R("gen"), generation_manifest_id="G1", event=ev(100), request_start_ts=100, fence=10,
                eligibility_reason=NONE_, exclusion_reason_for_missing=lambda x: EXCL, catalog_snapshot=cat, joins=j, **k)
        ent = lambda fid, ver: {"feature_id": fid, "feature_version": ver, "definition_hash": "d", "formula_hash": "f", "graph_hash": "g", "closure_ref": "c"}
        good = go(); self.assertEqual(good.blockers, ()); self.assertTrue(good.usable_for_simulation); self.assertFalse(good.qualified)           # genuine J2: baseline delivers
        bad = go([ent(other, eb.feature_version)])                                           # J2 replaced ONLY by the other known feature (catalog-valid)
        self.assertIn("JOIN_J2_INCLUDED_FEATURES_MISMATCH", bad.blockers); self.assertFalse(bad.usable_for_simulation)
        self.assertIn("JOIN_J2_INCLUDED_FEATURES_MISMATCH", go([ent(eb.feature_id.hex(), eb.feature_version + "x")]).blockers)          # exact version: same id, different version
        self.assertEqual(go([ent(eb.feature_id.hex(), eb.feature_version), ent(other, eb.feature_version)]).blockers, ())               # extras beyond the consumed set: NOT decided here (source-held)
        # direct unit boundary: consumed_features omitted keeps the legacy shape-and-catalog behaviour (explicitly NOT the consumer path)
        r = SJ.check_six_joins({"J2_INCLUDED_FEATURES": [ent(other, "1")]}, reg, fence=10, catalog_snapshot={(other, "1"): ("d", "f", "g")})
        self.assertEqual(dict((j, s) for j, s, _ in r.statuses)["J2_INCLUDED_FEATURES"], SJ.VERIFIED_AGAINST_REGISTRY)
        r = SJ.check_six_joins({"J2_INCLUDED_FEATURES": [ent(other, "1")]}, reg, fence=10, catalog_snapshot={(other, "1"): ("d", "f", "g")}, consumed_features={("aa", "1")})
        self.assertEqual(dict((j, s) for j, s, _ in r.statuses)["J2_INCLUDED_FEATURES"], SJ.MISMATCH)
if __name__ == "__main__": unittest.main()
