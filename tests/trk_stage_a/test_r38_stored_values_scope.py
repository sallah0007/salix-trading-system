"""R38 L2 scope: per-(accepted materialization, source segment) stored values; a later legitimate segment does not hit immutability; as-found comparison over every segment; due/trigger wiring through the same Core."""
import json, unittest
from stage_a.errors import Refusal, IntegrityFailure
from stage_a.tracker import stored_values as SV
from .test_r37_stored_values import Stored, SER, H, code
from .test_r25_scheduler import core
SER2 = [200.0 + i * 0.25 for i in range(30)]
class Scope(unittest.TestCase):
    def setUp(self):
        t = Stored("test_stored_values_equal_the_independent_recomputation_positive_and_retry_idempotent"); t.setUp(); self.t = t; self.kw = t.kw
        self.b2 = {"close": {"ref": "SRC/close-seg2", "hash": H(SER2)}}; self.kw2 = dict(self.kw, bindings=self.b2, fetch=lambda ref: SER2)
    def test_a_second_legitimate_segment_is_a_new_record_not_an_immutability_failure_and_ids_differ(self):
        r1 = SV.persist_stored_values(**self.kw); r2 = SV.persist_stored_values(**self.kw2); self.assertNotEqual(r1["segment_id"], r2["segment_id"]); self.assertEqual(r1["materialization_hash"], r2["materialization_hash"])
        for kw in (self.kw, self.kw2): self.assertEqual(SV.verify_stored_values(**kw)["overall"], "VERIFIED_STORED_EQUALS_RECOMPUTED")
        self.assertEqual(SV.persist_stored_values(**self.kw), r1)                                                 # same segment retry: idempotent
    def test_stored_segment_swapped_between_segments_or_missing_is_detected(self):
        SV.persist_stored_values(**self.kw); SV.persist_stored_values(**self.kw2); d = self.t.rig.raw_store._d; from stage_a.storage.authority_class import _PREFIX
        k1 = _PREFIX + SV.stored_values_key(self.t.body["materialization_hash"], SV.segment_id(self.kw["bindings"])); k2 = _PREFIX + SV.stored_values_key(self.t.body["materialization_hash"], SV.segment_id(self.b2))
        d[k1], d[k2] = d[k2], d[k1]; v = SV.verify_stored_values(**self.kw); self.assertEqual((v["overall"], v["reason"]), ("FAIL", "STORED_VALUES_NOT_BOUND_TO_ACCEPTED_MATERIALIZATION"))      # record's own segment_id != the key's segment
    def test_as_found_all_segments_verified_fail_unavailable_and_none(self):
        a = dict(journal=self.kw["journal"], store=self.kw["store"], feature_key=self.kw["feature_key"], series_hash=H); res = {"SRC/close": SER, "SRC/close-seg2": SER2}; fetch = lambda ref: res.get(ref)
        self.assertEqual((SV.verify_all_stored_segments(fetch=fetch, **a)["overall"], SV.verify_all_stored_segments(fetch=fetch, **a)["reason"]), ("UNAVAILABLE", "STORED_VALUES_ABSENT"))      # zero rows is not a completed search
        SV.persist_stored_values(**self.kw); SV.persist_stored_values(**self.kw2); v = SV.verify_all_stored_segments(fetch=fetch, **a); self.assertEqual((v["overall"], v["l2"], len(v["segments"])), ("VERIFIED_STORED_EQUALS_RECOMPUTED", "PASS", 2))
        res["SRC/close-seg2"] = None; self.assertEqual(SV.verify_all_stored_segments(fetch=fetch, **a)["overall"], "UNAVAILABLE")                      # one unresolved input segment: never VERIFIED
        res["SRC/close-seg2"] = SER2[:-1] + [1.0]; self.assertEqual(SV.verify_all_stored_segments(fetch=fetch, **a)["overall"], "FAIL")                    # source changed under a stored segment
    def test_pass_runs_only_due_subjects_records_in_the_same_core_and_bounds_and_unbound(self):
        c = core(); key = self.kw["feature_key"].key(); SV.persist_stored_values(**self.kw); b = SV.StoredBinding(self.kw["journal"], self.kw["store"], self.kw["feature_key"], lambda ref: SER, H)
        o = SV.run_stored_value_pass(c, {key: b}, [key], now=10, max_age=50, max_items=4); self.assertEqual([(x[0], x[1], x[2]) for x in o], [(key, "ABSENT", "VERIFIED")]); self.assertEqual(c.recording_health(key, "1", 11).local_state, "HEALTHY")
        self.assertEqual(SV.run_stored_value_pass(c, {key: b}, [key], now=11, max_age=50, max_items=4), [])                                           # fresh: nothing due, nothing re-run (unrelated healthy baseline untouched)
        self.assertEqual([x[2] for x in SV.run_stored_value_pass(c, {key: b}, [key], [(key, "SCHEDULED")], now=11, max_age=50, max_items=4)], ["VERIFIED"])    # supplied event trigger
        self.assertEqual([x[2] for x in SV.run_stored_value_pass(c, {}, [key], [(key, "SCHEDULED")], now=11, max_age=50, max_items=4)], ["UNBOUND"])
        self.assertEqual([x[2] for x in SV.run_stored_value_pass(core(), {key: b}, [key, "other/key"], now=10, max_age=50, max_items=1)], ["VERIFIED", "SKIPPED_BOUND_EXCEEDED"])
        self.assertEqual(code(SV.run_stored_value_pass, c, {}, [], now=1, max_age=1, max_items=0), "SCHEDULER_BOUND_INVALID")
    def test_same_class_preflight_applies_to_the_all_segment_recording(self):
        from .test_r38_stored_values_class import qcore
        SV.persist_stored_values(**self.kw); q = qcore(); h0 = q._j.head()
        self.assertEqual(code(SV.record_stored_value_maintenance_all, q, journal=self.kw["journal"], store=self.kw["store"], feature_key=self.kw["feature_key"], fetch=lambda r: SER, series_hash=H, now=10, max_age=50), "STORED_VALUES_CLASS_MISMATCH"); self.assertEqual(q._j.head(), h0)
if __name__ == "__main__": unittest.main()
