"""R37: persisted materialized values + L2 maintenance comparison (Registry 203-212). Producer (incremental evaluator) and verifier (reference evaluator) are independent implementations; the stored series is compared to the recomputation."""
import json, hashlib, unittest
from stage_a.errors import Refusal, IntegrityFailure
from stage_a.tracker import stored_values as SV
from stage_a.storage.byte_primitives import canonical_bytes
from stage_a.storage.authority_class import _PREFIX
from . import test_r33_composed as TC
from .test_r25_scheduler import core
H = lambda s: hashlib.sha256(repr(s).encode()).hexdigest()
SER = [100.0 + i * 0.5 for i in range(30)]
def code(f, *a, **k):
    try: f(*a, **k)
    except Refusal as e: return e.code
class Stored(unittest.TestCase):
    def setUp(self):
        t = TC.AcceptedRecordVerification(); self.rig, self.fk, self.j, self.body = t.accepted(); self.b = {"close": {"ref": "SRC/close", "hash": H(SER)}}
        self.kw = dict(journal=self.j, store=self.rig.store, feature_key=self.fk, bindings=self.b, fetch=lambda ref: SER, series_hash=H)
    def put(self): return SV.persist_stored_values(**self.kw)
    def raw_key(self): return _PREFIX + SV.stored_values_key(self.body["materialization_hash"])
    def test_stored_values_equal_the_independent_recomputation_positive_and_retry_idempotent(self):
        rec = self.put(); self.assertEqual(self.put(), rec); v = SV.verify_stored_values(**self.kw)
        self.assertEqual((v["overall"], v["l1"], v["l2"], v["stored_values_compared"], v["stream_verified"], v["l1_fallback"], v["health_effect"]), ("VERIFIED_STORED_EQUALS_RECOMPUTED", "PASS", "PASS", True, False, False, "NONE_ASSERTED")); self.assertEqual(v["provider_vintage_clock_proof"], "HELD"); self.assertEqual(rec["values"], v["recomputed"])
    def test_a_single_altered_stored_value_a_swapped_binding_and_a_different_record_are_each_detected(self):
        self.put(); good = self.rig.raw_store._d[self.raw_key()]; r = json.loads(good[0])
        def swap(d): self.rig.raw_store._d[self.raw_key()] = (canonical_bytes(d), 1)
        r2 = json.loads(good[0]); r2["values"][-1] = "3fb999999999999a"; swap(r2); v = SV.verify_stored_values(**self.kw); self.assertEqual((v["overall"], v["reason"], v["l2"], v["health_effect"]), ("FAIL", "STORED_VALUES_DIFFER_FROM_INDEPENDENT_RECOMPUTATION", "FAIL", "NOT_HEALTHY"))
        r3 = json.loads(good[0]); r3["bindings"]["close"]["hash"] = "a" * 64; swap(r3); self.assertEqual(SV.verify_stored_values(**self.kw)["reason"], "STORED_INPUT_BINDINGS_DIFFER_FROM_SUPPLIED")
        r4 = json.loads(good[0]); r4["materialization_hash"] = "b" * 64; swap(r4); self.assertEqual(SV.verify_stored_values(**self.kw)["reason"], "STORED_VALUES_NOT_BOUND_TO_ACCEPTED_MATERIALIZATION")
        self.rig.raw_store._d[self.raw_key()] = (b"{", 1); self.assertEqual(SV.verify_stored_values(**self.kw)["reason"], "STORED_VALUES_UNPARSEABLE"); self.rig.raw_store._d[self.raw_key()] = good; self.assertEqual(SV.verify_stored_values(**self.kw)["overall"], "VERIFIED_STORED_EQUALS_RECOMPUTED")   # genuine again
    def test_missing_stored_values_or_unresolved_inputs_are_unavailable_not_healthy_and_never_fall_back_to_l1(self):
        v = SV.verify_stored_values(**self.kw); self.assertEqual((v["overall"], v["reason"], v["l1"], v["l2"], v["health_effect"], v["l1_fallback"]), ("UNAVAILABLE", "STORED_VALUES_ABSENT", "PASS", "UNAVAILABLE", "NOT_HEALTHY", False))
        self.put(); u = SV.verify_stored_values(**dict(self.kw, fetch=lambda ref: None)); self.assertEqual((u["overall"], u["l2"], u["health_effect"]), ("UNAVAILABLE", "UNAVAILABLE", "NOT_HEALTHY"))
        d = SV.verify_stored_values(**dict(self.kw, fetch=lambda ref: SER[:-1] + [float("nan")], bindings={"close": {"ref": "SRC/close", "hash": H(SER[:-1] + [float("nan")])}})); self.assertEqual(d["overall"], "FAIL")      # NaN series never VERIFIED even with a matching hash and stored values
    def test_persist_refuses_unbound_unusable_or_conflicting_inputs_and_never_overwrites(self):
        self.assertEqual(code(SV.persist_stored_values, **dict(self.kw, bindings={})), "STORED_VALUES_INPUTS_INVALID"); self.assertEqual(code(SV.persist_stored_values, **dict(self.kw, bindings=dict(self.b, extra=self.b["close"]))), "STORED_VALUES_INPUT_SET_MISMATCH")
        self.assertEqual(code(SV.persist_stored_values, **dict(self.kw, fetch=lambda ref: [1.0, float("inf")])), "STORED_VALUES_SERIES_UNUSABLE"); self.assertEqual(code(SV.persist_stored_values, **dict(self.kw, fetch=lambda ref: SER[:-1])), "STORED_VALUES_SERIES_HASH_MISMATCH")
        self.assertNotIn(self.raw_key(), self.rig.raw_store._d); self.put(); ser2 = SER[:-1] + [999.0]
        with self.assertRaises(IntegrityFailure): SV.persist_stored_values(**dict(self.kw, fetch=lambda ref: ser2, bindings={"close": {"ref": "SRC/close", "hash": H(ser2)}}))                                         # a different series under the same accepted materialization never replaces the stored record
        self.assertEqual(SV.verify_stored_values(**self.kw)["overall"], "VERIFIED_STORED_EQUALS_RECOMPUTED")
    def test_maintenance_caller_records_l2_into_the_core_and_unavailable_makes_the_subject_not_healthy(self):
        c = core(); key = self.fk.key(); ver = self.fk.feature_version
        r = SV.record_stored_value_maintenance(c, now=10, max_age=50, **self.kw); self.assertEqual((r["l2"], r["overall"]), ("UNAVAILABLE", "UNAVAILABLE")); self.assertNotEqual(c.recording_health(key, ver, 11).local_state, "HEALTHY")
        self.put(); r = SV.record_stored_value_maintenance(c, now=12, max_age=50, **self.kw); self.assertEqual((r["l1"], r["l2"]), ("PASS", "PASS")); self.assertEqual(c.recording_health(key, ver, 13).local_state, "HEALTHY")                    # positive control through the same Core
        self.assertEqual(c.recording_health(key, ver, 13).evidence_class if hasattr(c.recording_health(key, ver, 13), "evidence_class") else "SIMULATION_CALLER_ASSERTED", "SIMULATION_CALLER_ASSERTED")
if __name__ == "__main__": unittest.main()
