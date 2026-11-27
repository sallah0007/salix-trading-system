import unittest
from stage_a.errors import Refusal
from stage_a.ml import generation_lifecycle as GL
from stage_a.ml import writer_finalizer as WF
from stage_a.ml import six_joins as SJ
from .test_r29_generation_lifecycle import man
def code(f, *a, **k):
    try: f(*a, **k)
    except Refusal as e: return e.code
GR = {"MANIFEST_WRITER": {"w1"}, "FINALIZER": {"f1"}}
def auth(grants=GR): return GL.GenerationRegistry(), grants
class WriterFinalizer(unittest.TestCase):
    def mk(self, grants=GR, ref="SRC-GRANT-1"):
        r = GL.GenerationRegistry(); return r, WF.GenerationAuthority(r, grants, ref if grants else None)
    def test_no_grants_holds_every_write_and_finalize_and_appoints_nobody(self):
        r, a = self.mk(None); self.assertEqual(code(a.write_manifest, "w1", man("M1")), "ML_PRINCIPAL_GRANTS_UNBOUND_HELD"); self.assertIsNone(r.manifest_of("M1"))
        self.assertEqual(code(a.finalize, "f1", "M1", 10, "x"), "ML_PRINCIPAL_GRANTS_UNBOUND_HELD"); self.assertEqual(a.correlate("M1")["status"], "MISMATCH:GRANTS_UNBOUND")
        for bad in ({"OTHER": {"x"}}, {"FINALIZER": set()}, {"FINALIZER": {"f"}}):                         # malformed grants / missing source ref refuse
            self.assertEqual(code(WF.GenerationAuthority, GL.GenerationRegistry(), bad, None if bad == {"FINALIZER": {"f"}} else "ref"), "ML_PRINCIPAL_GRANTS_INVALID")
    def test_granted_callers_write_and_finalize_and_correlation_is_against_the_registry_ledger(self):
        r, a = self.mk(); a.write_manifest("w1", man("M1")); self.assertFalse(r.eligible("M1"))
        self.assertEqual(code(a.write_manifest, "f1", man("M2")), "ML_CALLER_NOT_GRANTED"); self.assertEqual(code(a.finalize, "w1", "M1", 10, "x"), "ML_CALLER_NOT_GRANTED")
        self.assertEqual(code(a.finalize, "f1", "M-never", 10, "x"), "ML_FINALIZE_WITHOUT_RECORDED_WRITE")
        a.finalize("f1", "M1", 10, "cert"); c = a.correlate("M1"); self.assertEqual((c["status"], c["writer"], c["finalizers"], c["qualified"], c["writer_equals_finalizer"]), ("VERIFIED_AGAINST_REGISTRY", "w1", ("f1",), False, False)); self.assertTrue(r.eligible("M1"))
    def test_a_ledger_entry_written_around_the_facade_or_by_an_ungranted_caller_is_reported(self):
        r, a = self.mk(); a.write_manifest("w1", man("M1")); r.append_lifecycle("M1", "COMPLETE_CERTIFIED", 10, "direct", "ROGUE")             # bypass of the facade
        self.assertEqual(a.correlate("M1")["status"], "MISMATCH:LEDGER_ENTRY_NOT_FROM_A_RECORDED_GRANTED_FINALIZE")
        r2, a2 = self.mk(); r2.register_manifest(man("M9")); self.assertEqual(a2.correlate("M9")["status"], "MISMATCH:NO_SINGLE_RECORDED_WRITE_MATCHING_REGISTRY_HASH")          # registered without a recorded writer
        r3, a3 = self.mk(); a3.write_manifest("w1", man("M3")); self.assertEqual(a3.correlate("M3")["status"], "MISMATCH:NO_CERTIFIED_LEDGER_ENTRY")
        r4, a4 = self.mk(); a4.write_manifest("w1", man("M4")); a4.finalize("f1", "M4", 10, "c"); r4.append_lifecycle("M4", "COMPLETE_CERTIFIED", 11, "again", "ROGUE")
        self.assertTrue(a4.correlate("M4")["status"].startswith("MISMATCH"))                                                                               # one good finalize does not excuse a later foreign one
    def test_same_principal_is_reported_not_forbidden_and_six_joins_still_never_qualify(self):
        r, a = self.mk({"MANIFEST_WRITER": {"p"}, "FINALIZER": {"p"}}); a.write_manifest("p", man("M1")); a.finalize("p", "M1", 10, "c"); self.assertTrue(a.correlate("M1")["writer_equals_finalizer"])
        m = r.manifest_of("M1"); j = {"J1_DATASET_MANIFEST": {"binding_id": "b", "dataset_manifest_id": "d", "dataset_manifest_hash": "h"}, "J2_INCLUDED_FEATURES": [{"feature_id": "f", "feature_version": "1", "definition_hash": "d", "formula_hash": "fo", "graph_hash": "g", "closure_ref": "c"}],
             "J3_BIND_TIME_HEALTH": {"EVIDENCE_REF": "e"}, "J4_GENERATION_COMPONENTS": {"manifest_id": "M1", "manifest_hash": m.manifest_hash, "components": dict(m.components)}, "J5_LIFECYCLE_LEDGER": {"manifest_id": "M1", "manifest_hash": m.manifest_hash, "epoch": r.epoch},
             "J6_RESEARCH_FAMILY_EXPOSURE": {"family_ref": "fam", "ledger_ref": "l", "ledger_version": "1", "ledger_hash": "lh", "consulted_available_asof": 5}}
        self.assertFalse(SJ.check_six_joins(j, r, fence=10).qualified)
class ExactReceiptsAndIdempotentRetry(unittest.TestCase):
    def mk(self):
        r = GL.GenerationRegistry(); return r, WF.GenerationAuthority(r, GR, "SRC-GRANT-1")
    def test_a_direct_append_with_the_same_granted_name_is_not_a_recorded_finalize_but_repeat_facade_finalizes_are(self):
        r, a = self.mk(); a.write_manifest("w1", man("M1")); a.finalize("f1", "M1", 10, "facade"); self.assertEqual(a.correlate("M1")["status"], "VERIFIED_AGAINST_REGISTRY")
        r.append_lifecycle("M1", "COMPLETE_CERTIFIED", 11, "DIRECT NOT THROUGH FACADE", "f1")                       # SAME granted caller, around the facade
        self.assertEqual(a.correlate("M1")["status"], "MISMATCH:LEDGER_ENTRY_NOT_FROM_A_RECORDED_GRANTED_FINALIZE")
        r2, a2 = self.mk(); a2.write_manifest("w1", man("M2")); a2.finalize("f1", "M2", 10, "one"); a2.finalize("f1", "M2", 11, "two")   # genuine repeated legitimate finalizations
        self.assertEqual(a2.correlate("M2")["status"], "VERIFIED_AGAINST_REGISTRY")
    def test_identical_write_retry_is_idempotent_and_foreign_or_altered_retries_are_refused(self):
        r, a = self.mk(); m = man("M1"); a.write_manifest("w1", m); a.write_manifest("w1", m); a.finalize("f1", "M1", 10, "c")
        self.assertEqual(a.correlate("M1")["status"], "VERIFIED_AGAINST_REGISTRY")
        a_ = WF.GenerationAuthority(GL.GenerationRegistry(), {"MANIFEST_WRITER": {"w1", "w2"}, "FINALIZER": {"f1"}}, "S"); a_.write_manifest("w1", m)
        self.assertEqual(code(a_.write_manifest, "w2", m), "ML_MANIFEST_ALREADY_WRITTEN_BY_OTHER_CALLER")

if __name__ == "__main__": unittest.main()
