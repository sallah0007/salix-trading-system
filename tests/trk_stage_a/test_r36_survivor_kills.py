"""R36: kills for survivors that the R33/R34 sweeps reported on UNCHANGED main (reproduced on a pristine f1a597a worktree; they pre-date R36 and were not named in any closeout)."""
import dataclasses, unittest
from stage_a.errors import Refusal
from stage_a.tracker import reverification as RV
from stage_a.ml import six_joins as SJ, writer_finalizer as WF, generation_lifecycle as GL
from . import test_r33_composed as TC
from .test_r32_six_joins import good, reg
def code(f, *a, **k):
    try: f(*a, **k)
    except Refusal as e: return e.code
class Survivors(unittest.TestCase):
    def test_accepted_as_found_refuses_a_feature_id_that_the_accepted_body_does_not_name(self):
        rig, fk, j, body = TC.AcceptedRecordVerification().accepted()
        self.assertEqual(RV.accepted_as_found(j, rig.store, fk)[2], "ACCEPTED_RECORD_AS_FOUND")                                                    # positive control
        orig = RV.replay                                                                                                                                   # the namespace already encodes the feature id, so a body naming another key can only come from a corrupted journal view: simulate exactly that
        def corrupt(field, value):
            def fake(ns, recs):
                import copy; d = orig(ns, recs); st = copy.copy(d[fk.feature_version]); st.accepted_body = dict(st.accepted_body, **{field: value}); return {fk.feature_version: st}
            return fake
        try:
            for field, value in (("feature_key", "XAUUSD/H4/other_feature"), ("feature_version", "9")):
                RV.replay = corrupt(field, value); self.assertEqual(code(RV.accepted_as_found, j, rig.store, fk), "ACCEPTED_RECORD_IDENTITY_MISMATCH", field)
        finally: RV.replay = orig
    def test_j3_competing_local_state_is_refused_for_that_reason_not_merely_as_a_shape_failure(self):
        g = reg("M1"); d = good(g)
        for extra in ({"ML_LOCAL_STATE": "HEALTHY"}, {"EVIDENCE_REFS": ["a", "b"]}):
            d["J3_BIND_TIME_HEALTH"] = dict({"EVIDENCE_REF": "ev1"}, **extra); r = {n: (s, det) for n, s, det in SJ.check_six_joins(d, g, fence=10).statuses}[SJ.JOINS[2]]
            self.assertEqual(r[0], SJ.MISMATCH); self.assertIn("competing/plural/local-state", r[1])
    def test_correlate_reports_a_recorded_write_whose_hash_differs_from_the_registry(self):
        from .test_r34_ml_writer import GR
        from .test_r29_generation_lifecycle import man
        r = GL.GenerationRegistry(); a = WF.GenerationAuthority(r, GR, "SRC"); w = next(iter(GR["MANIFEST_WRITER"])); f = next(iter(GR["FINALIZER"])); m = man("G1"); a.write_manifest(w, m); a.finalize(f, "G1", 1, "c")
        self.assertEqual(a.correlate("G1")["status"], "VERIFIED_AGAINST_REGISTRY")
        i = next(i for i, x in enumerate(a._audit) if x[0] == "WRITE"); a._audit[i] = a._audit[i][:3] + ("tampered-hash",) + a._audit[i][4:]
        self.assertEqual(a.correlate("G1")["status"], "MISMATCH:NO_SINGLE_RECORDED_WRITE_MATCHING_REGISTRY_HASH")
if __name__ == "__main__": unittest.main()
