"""R25 bounded trigger -> actual verifier -> Core Health -> Gateway consumption. Simulation-labelled; not a daemon; no host/scheduling qualification."""
import unittest
from stage_a.errors import Refusal
from stage_a.composer.expression.manifest import Manifest
from stage_a.gateway import contracts as G
from stage_a.tracker import reverify_scheduler as S
from stage_a.storage.object_store import InMemoryObjectStore
from stage_a.storage.authority_class import SimulationStore
from .fixtures import momentum_manifest
from .test_boundaries import _entry, _gw, I, R
from .test_r24_composed import core, declared, SIMS
from .test_r24_core import code, ver

KEY = "XAUUSD/H4/mom3/1"
class Scheduler(unittest.TestCase):
    def setUp(self): self.m = Manifest.from_dict(momentum_manifest()); self.b = {KEY: (self.m, declared(self.m), SIMS())}
    def test_absent_subject_is_verified_then_not_due_and_gateway_consumes_the_result(self):
        c = core(); r = S.run_reverification_pass(c, self.b, [KEY], now=10, max_age=50)
        self.assertEqual([(i.subject, i.trigger, i.outcome, i.detail) for i in r], [(KEY, "ABSENT", "VERIFIED", "PASS")])
        self.assertEqual([r_.kind for r_ in c._j.read_from(0) if r_.kind == "REVERIFY_REQUESTED"], ["REVERIFY_REQUESTED"])            # the trigger is journaled before the verifier runs
        self.assertEqual(S.run_reverification_pass(c, self.b, [KEY], now=11, max_age=50), [])                    # fresh evidence: nothing due, nothing re-run
        hs = c.gateway_health(KEY, "1", 12, R("hl"), 11); self.assertTrue(hs.acceptable); self.assertEqual(hs.evidence_class, "SIMULATION")
        self.assertIsInstance(_gw().resolve("o", _entry(), I, I, 3, 20, hs), G.Binding)
    def test_stale_future_epoch_and_unknown_l2_block_gateway_until_a_real_pass(self):
        c = core(); S.run_reverification_pass(c, self.b, [KEY], now=10, max_age=5)
        self.assertEqual([i.trigger for i in S.run_reverification_pass(c, self.b, [KEY], now=20, max_age=5)], ["STALE"])
        self.assertTrue(c.gateway_health(KEY, "1", 21, R("hl"), 20).acceptable)
        c.declare_dependency(KEY, "UP"); c.advance_epoch("UP", 1)
        self.assertFalse(c.gateway_health(KEY, "1", 21, R("hl"), 20).acceptable)                                  # invalidated: blocked before re-verification
        self.assertEqual(code(c.reresolve, KEY, "1", 21), "NO_FRESH_WITNESS")                                  # old evidence is no witness
        self.assertEqual([i.trigger for i in S.run_reverification_pass(c, self.b, [KEY], now=22, max_age=5)], ["EPOCH_ADVANCED"])
        c.reresolve(KEY, "1", 23); self.assertTrue(c.gateway_health(KEY, "1", 24, R("hl"), 23).acceptable)           # positive control: new verifier pass clears
    def test_corrupt_bytes_never_become_healthy_and_future_evidence_is_due(self):
        class Tamper(InMemoryObjectStore):
            def get(self, k):
                g = super().get(k); return None if g is None else (g[0][:-1] + bytes([g[0][-1] ^ 1]),) + tuple(g[1:])
        from stage_a.storage.authority_class import approve_test_adapter; approve_test_adapter(Tamper)
        c = core(); b = {KEY: (self.m, declared(self.m), SimulationStore(Tamper()))}
        r = S.run_reverification_pass(c, b, [KEY], now=10, max_age=5); self.assertEqual((r[0].outcome, r[0].detail), ("VERIFIED", "FAIL"))
        self.assertFalse(c.gateway_health(KEY, "1", 11, R("hl"), 10).acceptable)
        c2 = core(); c2.record_verification(KEY, "1", "REQUIRED", "PASS", "PASS", 50, 5, "v", "d")               # evidence dated in the future relative to now
        self.assertEqual([i.trigger for i in S.run_reverification_pass(c2, self.b, [KEY], now=10, max_age=5)], ["STALE"])
    def test_unbound_mismatched_and_bounded_items_are_reported_not_verified(self):
        c = core(); r = S.run_reverification_pass(c, {}, [KEY, "OTHER/H4/x/1"], now=10, max_age=5); self.assertEqual([i.outcome for i in r], ["UNBOUND", "UNBOUND"])
        self.assertEqual(c.recording_health(KEY, "1", 11).state, "UNKNOWN")
        r = S.run_reverification_pass(c, {"OTHER/H4/x/1": self.b[KEY]}, ["OTHER/H4/x/1"], now=10, max_age=5); self.assertEqual(r[0].outcome, "KEY_MISMATCH")
        r = S.run_reverification_pass(c, self.b, [KEY, "A/H4/a/1", "B/H4/b/1"], now=10, max_age=5, max_items=1); self.assertEqual([i.outcome for i in r], ["VERIFIED", "SKIPPED_BOUND_EXCEEDED", "SKIPPED_BOUND_EXCEEDED"])
        self.assertEqual(code(S.run_reverification_pass, c, self.b, [KEY], now=10, max_age=5, max_items=0), "SCHEDULER_BOUND_INVALID")
    def test_wrong_class_store_is_refused_and_leaves_no_writes_and_unrelated_baseline_is_untouched(self):
        c = core(); ver(c, "BASE", at=10, age=100); plain = InMemoryObjectStore()
        r = S.run_reverification_pass(c, {KEY: (self.m, declared(self.m), plain)}, [KEY, "BASE"], now=11, max_age=5)
        self.assertEqual([(i.subject, i.outcome, i.detail) for i in r], [(KEY, "REFUSED", "REVERIFY_CARRIER_CLASS_MISMATCH")]); self.assertEqual(plain.list_prefix(""), [])
        self.assertEqual(c.recording_health("BASE", "1", 12).state, "HEALTHY")
if __name__ == "__main__": unittest.main()
