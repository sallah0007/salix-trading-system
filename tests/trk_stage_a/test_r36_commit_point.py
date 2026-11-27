"""R36: durable window COMMIT POINT. A provisional outcome is published to no consumer until the durable final store holds it (root repro on the R35 runtime:
a failed identity write left gw.outcome('R1') and FW.receive_verified accepting a Binding the store never held)."""
import unittest
from stage_a.errors import Refusal, IntegrityFailure
from stage_a.gateway import contracts as G
from stage_a.gateway import durable_final_store as D
from stage_a.gateway.v038 import FinalResolutionIdentity as FI
from stage_a.fw.association import FwAssociation
from stage_a.fw import receiver as FWR
from stage_a.storage.object_store import InMemoryObjectStore
from .test_boundaries import _gw, _entry, _health, I, T
def code(f, *a, **k):
    try: f(*a, **k)
    except (Refusal, IntegrityFailure) as e: return getattr(e, "code", type(e).__name__)
    except Exception as e: return type(e).__name__
class Flaky(InMemoryObjectStore):
    """fail(op, key_fragment, mode): mode 'before' = raise without writing; 'after' = write then raise (unknown commit); 'after_noread' = write, raise, and make the read-back fail too."""
    def __init__(self): super().__init__(); self.rules = []; self.dead = False
    def fail(self, frag, mode): self.rules.append((frag, mode))
    def _hit(self, key): return next((m for f, m in self.rules if f in key), None)
    def put_if_absent(self, key, data):
        m = self._hit(key)
        if m == "before": self.rules = [r for r in self.rules if r[0] not in key]; raise OSError("WRITE_FAILED")
        r = super().put_if_absent(key, data)
        if m in ("after", "after_noread"):
            self.rules = [x for x in self.rules if x[0] not in key]; self.dead = m == "after_noread"; raise OSError("WRITE_FAILED_AFTER_COMMIT")
        return r
    def get(self, key):
        if self.dead: raise OSError("READ_FAILED")
        return super().get(key)
W = FI("FW", "B1", "XAUUSD", "WINDOW-1")
def gw(raw, wm=100):
    g = _gw(); g.final_store = D.DurableFinalResolutionStore(raw); g.set_watermark(wm); return g
class CommitPoint(unittest.TestCase):
    def test_identity_write_failure_publishes_nothing_to_any_consumer_and_a_retry_is_not_poisoned(self):
        raw = Flaky(); g = gw(raw); raw.fail("final-resolution/id/", "before"); e = _entry()
        self.assertEqual(code(g.resolve_window, "R1", W, e, I, I, 3, 10, _health()), "OSError")
        self.assertEqual(list(raw.list_prefix("final-resolution/id/")), []); self.assertIsNone(g.final_store.outcome_for(W))
        self.assertIsNone(g.outcome("R1")); self.assertIsNone(g.outcome("R1", "FW")); self.assertIsNone(g.outcome("R1", "ML"))
        self.assertEqual(g._window_issued, {}); self.assertEqual(g._window_outcome, {})
        self.assertEqual(code(FwAssociation(g.final_store).associate_request, "R1", W), "FW_REQUEST_NOT_BOUND_TO_IDENTITY_BY_STORE")
        b = g.resolve_window("R1", W, e, I, I, 3, 10, _health()); self.assertIsInstance(b, G.Binding)                              # the failed attempt committed nothing: a clean retry decides
        self.assertIs(FWR.receive_verified(b, e, I, I, T, g), b)
    def test_request_binding_failure_keeps_the_committed_identity_and_a_retry_never_evaluates_again(self):
        raw = Flaky(); g = gw(raw); raw.fail("final-resolution/req/", "before"); e = _entry()
        self.assertEqual(code(g.resolve_window, "R1", W, e, I, I, 3, 10, _health()), "OSError"); self.assertIsNone(g.outcome("R1", "FW"))      # not confirmed end to end: not published
        self.assertEqual(g.final_store.evaluations, 1); self.assertIsNotNone(g.final_store.outcome_for(W)); self.assertEqual(len(list(raw.list_prefix("final-resolution/id/"))), 1)
        g.set_watermark(0)                                                                                                         # the world moved: a second evaluation would now DENY
        b = g.resolve_window("R2", W, e, I, I, 3, 10, _health()); self.assertIsInstance(b, G.Binding); self.assertEqual(g.final_store.evaluations, 1)   # no second decision, no recover() needed
        self.assertIs(FWR.receive_verified(b, e, I, I, T, g), b)
    def test_unknown_commit_write_then_raise_is_confirmed_by_read_back(self):
        raw = Flaky(); g = gw(raw); raw.fail("final-resolution/id/", "after"); e = _entry()
        b = g.resolve_window("R1", W, e, I, I, 3, 10, _health()); self.assertIsInstance(b, G.Binding); self.assertEqual(g.final_store.evaluations, 1)
        self.assertEqual(len(list(raw.list_prefix("final-resolution/id/"))), 1)
    def test_unknown_commit_with_failed_read_back_holds_the_identity_until_recover_and_never_evaluates_twice(self):
        raw = Flaky(); g = gw(raw); raw.fail("final-resolution/id/", "after_noread"); e = _entry()
        self.assertEqual(code(g.resolve_window, "R1", W, e, I, I, 3, 10, _health()), "FINAL_RESOLUTION_RECOVERY_REQUIRED"); self.assertIsNone(g.outcome("R1", "FW"))
        self.assertEqual(code(g.resolve_window, "R2", W, e, I, I, 3, 10, _health()), "FINAL_RESOLUTION_RECOVERY_REQUIRED"); self.assertEqual(g.final_store.evaluations, 1)
        raw.dead = False; g2 = gw(raw, 0); self.assertEqual(g2.final_store.recover(), 1)                                                # genuine restart: the record the unknown write did land is recovered
        b = g2.resolve_window("R3", W, e, I, I, 3, 10, _health()); self.assertIsInstance(b, G.Binding); self.assertEqual(g2.final_store.evaluations, 0)
        g.final_store.recover(); self.assertEqual(g.final_store.evaluations, 1); self.assertIsInstance(g.resolve_window("R4", W, e, I, I, 3, 10, _health()), G.Binding)   # recover() lifts the hold on the old process too
    def test_a_known_absent_failed_read_back_hold_is_not_applied_when_the_write_provably_did_not_land(self):
        raw = Flaky(); g = gw(raw); raw.fail("final-resolution/pin/", "before"); e = _entry()
        self.assertEqual(code(g.resolve_window, "R1", W, e, I, I, 3, 10, _health()), "OSError"); self.assertIsNone(g.final_store.pin_of(W))
        self.assertIsInstance(g.resolve_window("R1", W, e, I, I, 3, 10, _health()), G.Binding)
class RetryAndScope(unittest.TestCase):
    def test_a_later_retry_clock_is_not_a_different_window_but_a_different_governing_parameter_is(self):
        raw = InMemoryObjectStore(); g = gw(raw); e = _entry()
        o1 = g.resolve_window("R1", W, e, I, I, 3, 10, _health(), observed_at=None); self.assertIsInstance(o1, G.Binding)
        self.assertIs(g.resolve_window("R3", W, e, I, I, 3, 10, _health(), observed_at=25), o1)                                          # natural later retry: stored outcome, no refusal, no re-evaluation
        self.assertEqual(g.final_store.facts_of(W), {"observed_at": None, "watermark": 100})                                          # the FIRST evaluation's facts stay immutable
        self.assertEqual(code(g.resolve_window, "R4", W, e, I, I, 3, 11, _health()), "RESOLUTION_IDENTITY_PARAMETERS_DIFFER")            # fence is governing
        g2 = gw(raw, 5); g2.final_store.recover(); self.assertIs(type(g2.resolve_window("R5", W, e, I, I, 3, 10, _health(), observed_at=99)), G.Binding)   # after a restart and at a late observation time
        self.assertEqual(g2.final_store.facts_of(W), {"observed_at": None, "watermark": 100}); self.assertEqual(g2.final_store.evaluations, 0)
    def test_the_same_local_request_id_for_two_independent_consumers_is_two_windows(self):
        g = gw(InMemoryObjectStore()); e = _entry(); fw = g.resolve_window("R1", W, e, I, I, 3, 10, _health()); ml = g.resolve_window("R1", FI("ML", "B2", "XAUUSD", "WINDOW-1"), e, I, I, 3, 10, _health())
        self.assertIsInstance(fw, G.Binding); self.assertIsInstance(ml, G.Binding); self.assertIsNot(fw, ml); self.assertIs(g.outcome("R1", "FW"), fw); self.assertIs(g.outcome("R1", "ML"), ml)
        g.resolve("legacy", e, I, I, 3, 10, _health()); self.assertEqual(code(g.resolve_window, "legacy", W, e, I, I, 3, 10, _health()), "REQUEST_ID_USED_OUTSIDE_THIS_WINDOW")   # the misuse guard for the legacy global cache is kept
if __name__ == "__main__": unittest.main()
