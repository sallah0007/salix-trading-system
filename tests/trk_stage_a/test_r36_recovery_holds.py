"""R36 (root review of 7c4e216): holds survive a FAILED recover; a committed identity keeps its request reservation after a request-binding fault (live and after restart); source-value series must be finite."""
import struct, unittest
from stage_a.errors import Refusal, IntegrityFailure
from stage_a.gateway import contracts as G
from stage_a.gateway import durable_final_store as D
from stage_a.gateway.v038 import FinalResolutionIdentity as FI
from .test_r36_commit_point import Flaky, gw, W, code
from .test_boundaries import _entry, _health, I
W2 = FI("FW", "B1", "XAUUSD", "WINDOW-2")
class Listy(Flaky):
    def __init__(self): super().__init__(); self.list_dead = False
    def list_prefix(self, p):
        if self.list_dead: raise OSError("LIST_FAILED")
        return super().list_prefix(p)
class RecoverIsTransactional(unittest.TestCase):
    def held(self):
        raw = Listy(); g = gw(raw); raw.fail("final-resolution/id/", "after_noread"); e = _entry()
        self.assertEqual(code(g.resolve_window, "R1", W, e, I, I, 3, 10, _health()), "FINAL_RESOLUTION_RECOVERY_REQUIRED"); return raw, g, e
    def test_failed_recover_keeps_the_hold_and_never_permits_a_second_decision_then_a_successful_recover_returns_the_stored_outcome(self):
        raw, g, e = self.held(); raw.dead = False; raw.list_dead = True
        self.assertEqual(code(g.final_store.recover), "OSError")                                           # recovery failed
        raw.list_dead = False                                                                              # backend restored
        self.assertEqual(code(g.resolve_window, "R2", W, e, I, I, 3, 10, _health()), "FINAL_RESOLUTION_RECOVERY_REQUIRED"); self.assertEqual(g.final_store.evaluations, 1)      # hold NOT released
        g.set_watermark(0)                                                                                 # a second evaluation would now DENY
        self.assertEqual(g.final_store.recover(), 1)
        b = g.resolve_window("R2", W, e, I, I, 3, 10, _health()); self.assertIsInstance(b, G.Binding); self.assertEqual(g.final_store.evaluations, 1)                           # control: stored outcome, no re-evaluation
    def test_a_corrupt_or_unreadable_record_during_recover_also_keeps_the_hold_and_the_live_maps(self):
        raw, g, e = self.held(); raw.dead = True; self.assertIsNotNone(code(g.final_store.recover)); raw.dead = False
        self.assertEqual(code(g.resolve_window, "R2", W, e, I, I, 3, 10, _health()), "FINAL_RESOLUTION_RECOVERY_REQUIRED")
        k = list(raw.list_prefix("final-resolution/id/"))[0]; good = raw._d[k]; raw._d[k] = (good[0].replace(b"WINDOW-1", b"WINDOW-X"), 1)
        self.assertEqual(code(g.final_store.recover), "INTEGRITY_FAILURE"); self.assertEqual(code(g.resolve_window, "R2", W, e, I, I, 3, 10, _health()), "FINAL_RESOLUTION_RECOVERY_REQUIRED"); raw._d[k] = good
        self.assertEqual(g.final_store.recover(), 1)
class RequestReservation(unittest.TestCase):
    def fault(self):
        raw = Flaky(); g = gw(raw); raw.fail("final-resolution/req/", "before"); e = _entry()
        self.assertEqual(code(g.resolve_window, "R1", W, e, I, I, 3, 10, _health()), "OSError"); return raw, g, e
    def test_live_process_refuses_a_different_window_for_the_same_request_and_the_same_window_retry_persists_the_binding(self):
        raw, g, e = self.fault()
        self.assertEqual(g.final_store.identity_of("FW", "R1"), W)                                         # reservation retained
        self.assertEqual(code(g.resolve_window, "R1", W2, e, I, I, 3, 10, _health()), "REQUEST_ID_REBOUND_TO_OTHER_IDENTITY"); self.assertIsNone(g.final_store.pin_of(W2)); self.assertEqual(g.final_store.evaluations, 1)
        self.assertEqual(g.final_store.identity_of("FW", "R1"), W)
        b = g.resolve_window("R1", W, e, I, I, 3, 10, _health()); self.assertIsInstance(b, G.Binding); self.assertEqual(len(list(raw.list_prefix("final-resolution/req/"))), 1)             # the binding is now durable
        self.assertEqual(code(g.resolve_window, "R1", W2, e, I, I, 3, 10, _health()), "REQUEST_ID_REBOUND_TO_OTHER_IDENTITY")
    def test_after_restart_the_original_association_is_derived_from_the_durable_identity_record_without_rewriting_the_outcome(self):
        raw, g, e = self.fault(); before = dict(raw._d); g2 = gw(raw, 0); g2.final_store.recover()
        self.assertEqual(g2.final_store.identity_of("FW", "R1"), W); self.assertEqual(code(g2.resolve_window, "R1", W2, e, I, I, 3, 10, _health()), "REQUEST_ID_REBOUND_TO_OTHER_IDENTITY")
        b = g2.resolve_window("R1", W, e, I, I, 3, 10, _health()); self.assertIsInstance(b, G.Binding); self.assertEqual(b.request_id, "R1"); self.assertEqual(g2.final_store.evaluations, 0)
        self.assertEqual({k: v for k, v in raw._d.items() if "/id/" in k}, {k: v for k, v in before.items() if "/id/" in k})            # identity/outcome bytes untouched
        self.assertIsInstance(g2.resolve_window("R7", W, e, I, I, 3, 10, _health()), G.Binding)                                             # positive: a new request id for the same window
    def test_two_identities_claiming_one_request_id_in_the_durable_record_fail_recovery(self):
        raw = Flaky(); g = gw(raw); e = _entry(); g.resolve_window("R1", W, e, I, I, 3, 10, _health()); g.resolve_window("R9", W2, e, I, I, 3, 10, _health())
        ks = sorted(raw.list_prefix("final-resolution/id/")); import json
        for k in ks:
            d = json.loads(raw._d[k][0])
            if d["outcome"]["f"].get("request_id") == "R9":
                d["outcome"]["f"]["request_id"] = "R1"; ident = D.decode(d["identity"]); nk = D._ident_key(ident); raw._d[k] = (D._dump(d), 1)
        self.assertEqual(code(gw(raw).final_store.recover), "INTEGRITY_FAILURE")
def bits(*xs): return struct.pack(">%dd" % len(xs), *xs)
class FiniteSeries(unittest.TestCase):
    """Exact genuine Rig accepted manifest reduced to input-only, as in the root repro; hashes are caller-supplied (TEST-ONLY codec)."""
    def setUp(self):
        import hashlib
        from . import test_r33_composed as TC
        from stage_a.tracker import source_inputs as SI
        self.SI = SI; t = TC.AcceptedRecordVerification(); self.rig, self.fk, self.j, self.body = t.accepted(); self.H = lambda s: hashlib.sha256(bits(*s)).hexdigest()
        orig = SI._as_found
        def reduced(j, st, fk):
            n, raw, p, why = orig(j, st, fk)
            if p is None: return n, raw, p, why
            p = dict(p); p["nodes"] = [x for x in p["nodes"] if x["op"] == "input"][:1]; p["output"] = p["nodes"][0]["id"]; return {p["nodes"][0]["name"]}, raw, p, why
        SI._as_found = reduced; self.addCleanup(setattr, SI, "_as_found", orig); self.name = None
    def v(self, ser, exp=None):
        names = self.SI._as_found(self.j, self.rig.store, self.fk)[0]; n = next(iter(names))
        return self.SI.verify_source_values(journal=self.j, store=self.rig.store, feature_key=self.fk, bindings={n: {"ref": "SRC", "hash": self.H(ser)}}, fetch=lambda ref: ser, series_hash=self.H, expected_output=exp)
    def test_finite_positive_and_nonfinite_values_with_matching_hashes_are_refused(self):
        r = self.v([1.0, 2.0]); self.assertEqual(r["overall"], "VERIFIED_RECOMPUTED"); self.assertEqual(r["recomputed"], [struct.pack(">d", 1.0).hex(), struct.pack(">d", 2.0).hex()])
        for bad in (float("nan"), float("inf"), float("-inf")):
            for ser in ([bad], [1.0, bad], [bad, 2.0]):
                r = self.v(ser); self.assertEqual((r["overall"], r["reason"], list(r["inputs"].values())), ("FAIL", "INPUTS_NOT_VERIFIED", ["SERIES_NONFINITE"])); self.assertIsNone(r["recomputed"])
    def test_signed_zero_is_canonicalised_to_positive_zero_and_subnormals_are_preserved(self):
        r = self.v([-0.0, 0.0]); self.assertEqual((r["overall"], r["recomputed"]), ("VERIFIED_RECOMPUTED", ["0" * 16, "0" * 16]))
        sub = 5e-324; r = self.v([sub, -sub, 2.2250738585072014e-308]); self.assertEqual(r["overall"], "VERIFIED_RECOMPUTED"); self.assertEqual(r["recomputed"], [struct.pack(">d", x).hex() for x in (sub, -sub, 2.2250738585072014e-308)])
    def test_the_reference_evaluator_itself_refuses_a_nonfinite_input_and_the_lag_and_operator_paths_are_covered(self):
        from stage_a.tracker.verification.independent_traversal import reference_evaluate, RefEvalError
        for p in ({"nodes": [{"id": "a", "op": "input", "name": "x"}], "output": "a"}, {"nodes": [{"id": "a", "op": "input", "name": "x"}, {"id": "b", "op": "lag", "args": ["a"], "n": 1}], "output": "b"}, {"nodes": [{"id": "a", "op": "input", "name": "x"}, {"id": "b", "op": "neg", "args": ["a"]}], "output": "b"}):
            with self.assertRaises(RefEvalError): reference_evaluate(p, {"x": [1.0, float("nan")]})
if __name__ == "__main__": unittest.main()
