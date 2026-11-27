import copy, unittest
from stage_a.errors import Refusal
from stage_a.ml import six_joins as SJ
from .test_r29_generation_lifecycle import reg
def code(f, *a, **k):
    try: f(*a, **k)
    except Refusal as e: return e.code
def good(r):
    m = r.manifest_of("M1")
    return {"J1_DATASET_MANIFEST": {"binding_id": "b1", "dataset_manifest_id": "dm1", "dataset_manifest_hash": "h1"},
            "J2_INCLUDED_FEATURES": [{"feature_id": "f", "feature_version": "1", "definition_hash": "d", "formula_hash": "fo", "graph_hash": "g", "closure_ref": "c"}],
            "J3_BIND_TIME_HEALTH": {"EVIDENCE_REF": "ev1"},
            "J4_GENERATION_COMPONENTS": {"manifest_id": "M1", "manifest_hash": m.manifest_hash, "components": dict(m.components)},
            "J5_LIFECYCLE_LEDGER": {"manifest_id": "M1", "manifest_hash": m.manifest_hash, "epoch": r.epoch},
            "J6_RESEARCH_FAMILY_EXPOSURE": {"family_ref": "fam", "ledger_ref": "l", "ledger_version": "1", "ledger_hash": "lh", "consulted_available_asof": 5}}
class Joins(unittest.TestCase):
    def st(self, rep): return {j: s for j, s, _ in rep.statuses}
    def test_positive_verifies_registry_joins_leaves_unbound_instances_unverified_and_is_never_qualified(self):
        r = reg("M1"); rep = SJ.check_six_joins(good(r), r, fence=10)
        s = self.st(rep); self.assertEqual((s["J4_GENERATION_COMPONENTS"], s["J5_LIFECYCLE_LEDGER"]), (SJ.VERIFIED_AGAINST_REGISTRY,) * 2)
        self.assertTrue(all(s[j] == SJ.PRESENT_UNVERIFIED for j in ("J1_DATASET_MANIFEST", "J3_BIND_TIME_HEALTH", "J6_RESEARCH_FAMILY_EXPOSURE")))
        self.assertEqual((rep.complete, rep.qualified, rep.writer_principal), (True, False, "UNBOUND_NOT_IN_SOURCE"))
    def test_each_join_missing_or_altered_is_reported_and_unrelated_joins_stay_intact(self):
        r = reg("M1", "M2")
        for j in SJ.JOINS:
            d = good(r); del d[j]; rep = SJ.check_six_joins(d, r, fence=10); self.assertEqual((self.st(rep)[j], rep.complete), (SJ.MISSING, False), j)
            self.assertEqual(sum(1 for x in self.st(rep).values() if x == SJ.MISSING), 1)
        for mut in (lambda d: d["J4_GENERATION_COMPONENTS"].update(manifest_hash="x"), lambda d: d["J4_GENERATION_COMPONENTS"]["components"].pop("calibrator"), lambda d: d["J4_GENERATION_COMPONENTS"]["components"].update(calibrator="evil"),
                    lambda d: d["J5_LIFECYCLE_LEDGER"].update(epoch=999), lambda d: d["J5_LIFECYCLE_LEDGER"].update(manifest_hash="x"), lambda d: d["J5_LIFECYCLE_LEDGER"].update(manifest_id="M-unknown"),
                    lambda d: d["J6_RESEARCH_FAMILY_EXPOSURE"].update(consulted_available_asof=10), lambda d: d["J3_BIND_TIME_HEALTH"].update(ML_LOCAL_STATE="x"), lambda d: d["J3_BIND_TIME_HEALTH"].update(EVIDENCE_REFS="x"),
                    lambda d: d["J1_DATASET_MANIFEST"].update(extra="x"), lambda d: d["J2_INCLUDED_FEATURES"].clear()):
            d = good(r); mut(d); self.assertFalse(SJ.check_six_joins(d, r, fence=10).complete)
    def test_catalog_snapshot_membership_is_supplied_not_admitted_and_unknown_join_or_fence_refused(self):
        r = reg("M1"); d = good(r); cat = {("f", "1"): ("d", "fo", "g")}
        self.assertEqual(self.st(SJ.check_six_joins(d, r, fence=10, catalog_snapshot=cat))["J2_INCLUDED_FEATURES"], SJ.VERIFIED_AGAINST_REGISTRY)
        self.assertEqual(self.st(SJ.check_six_joins(d, r, fence=10, catalog_snapshot={("f", "1"): ("d", "other", "g")}))["J2_INCLUDED_FEATURES"], SJ.MISMATCH)
        self.assertEqual(code(SJ.check_six_joins, dict(d, J7="x"), r, fence=10), "ML_JOINS_UNKNOWN_JOIN"); self.assertEqual(code(SJ.check_six_joins, d, r, fence=-1), "ML_JOINS_FENCE_INVALID"); self.assertEqual(code(SJ.check_six_joins, [], r, fence=1), "ML_JOINS_NOT_A_RECORD")
    def test_revoked_later_epoch_still_matches_only_an_existing_epoch_triple(self):
        r = reg("M1"); d = good(r); e0 = r.epoch; r.append_lifecycle("M1", "REVOKED", 50, "x", "A")
        self.assertEqual(self.st(SJ.check_six_joins(d, r, fence=10))["J5_LIFECYCLE_LEDGER"], SJ.VERIFIED_AGAINST_REGISTRY)           # the recorded epoch is still a real ledger epoch (history is append-only)
        d["J5_LIFECYCLE_LEDGER"]["epoch"] = r.epoch + 1; self.assertEqual(self.st(SJ.check_six_joins(d, r, fence=10))["J5_LIFECYCLE_LEDGER"], SJ.MISMATCH)

class Correlation(unittest.TestCase):
    """R33 finding: J4 and J5 were each valid but never correlated - M1 components with M2's ledger reported complete."""
    def corr(self, rep): return {c: s for c, s, _ in rep.correlation}
    def test_same_generation_positive_and_cross_generation_is_a_mismatch(self):
        from .test_r29_generation_lifecycle import ev
        r = reg("M1", "M2"); d = good(r)
        rep = SJ.check_six_joins(d, r, fence=10); self.assertTrue(rep.complete); self.assertEqual(self.corr(rep)["J4_J5_SAME_GENERATION"], SJ.VERIFIED_AGAINST_REGISTRY)
        m2 = r.manifest_of("M2"); d["J5_LIFECYCLE_LEDGER"] = {"manifest_id": "M2", "manifest_hash": m2.manifest_hash, "epoch": r.epoch}              # both individually VALID
        rep = SJ.check_six_joins(d, r, fence=10); self.assertEqual({j: s for j, s, _ in rep.statuses}["J5_LIFECYCLE_LEDGER"], SJ.VERIFIED_AGAINST_REGISTRY)
        self.assertEqual((self.corr(rep)["J4_J5_SAME_GENERATION"], rep.complete, rep.qualified), (SJ.MISMATCH, False, False))
        d = good(r); d["J5_LIFECYCLE_LEDGER"]["manifest_hash"] = m2.manifest_hash                                                                          # known-foreign hash under M1's id
        self.assertFalse(SJ.check_six_joins(d, r, fence=10).complete)
    def test_request_snapshot_must_be_issued_by_this_registry_for_the_same_manifest(self):
        from .test_r29_generation_lifecycle import ev
        import dataclasses
        r = reg("M1", "M2"); d = good(r); s1 = r.snapshot("q1", ev(), "M1", 100); s2 = r.snapshot("q2", ev(), "M2", 100)
        self.assertEqual(self.corr(SJ.check_six_joins(d, r, fence=10, request_snapshot=s1))["REQUEST_SNAPSHOT_SAME_GENERATION"], SJ.VERIFIED_AGAINST_REGISTRY)
        for bad in (s2, dataclasses.replace(s1, manifest_hash="x"), dataclasses.replace(s1, request_id="never-issued"), dataclasses.replace(s1, epoch_at_snapshot=s1.epoch_at_snapshot + 1)):
            rep = SJ.check_six_joins(d, r, fence=10, request_snapshot=bad); self.assertEqual((self.corr(rep)["REQUEST_SNAPSHOT_SAME_GENERATION"], rep.complete), (SJ.MISMATCH, False))
    def test_unlinkable_joins_are_reported_not_invented_and_never_qualified(self):
        r = reg("M1"); rep = SJ.check_six_joins(good(r), r, fence=10); self.assertEqual(self.corr(rep)["J1_J2_J3_J6_TO_GENERATION"], SJ.PRESENT_UNVERIFIED); self.assertFalse(rep.qualified)
