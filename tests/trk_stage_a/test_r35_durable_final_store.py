import json, unittest
from stage_a.errors import Refusal, IntegrityFailure
from stage_a.gateway import contracts as G
from stage_a.gateway import durable_final_store as D
from stage_a.gateway.v038 import FinalResolutionIdentity as FI
from stage_a.storage.object_store import InMemoryObjectStore
from .test_boundaries import _gw, _entry, _health, I, R
def code(f, *a, **k):
    try: f(*a, **k)
    except (Refusal, IntegrityFailure) as e: return getattr(e, "code", type(e).__name__)
W1 = FI("FW", "B1", "XAUUSD", "WINDOW-1")
def gw(raw, watermark=100):
    g = _gw(); g.final_store = D.DurableFinalResolutionStore(raw); g.set_watermark(watermark); return g
class Restart(unittest.TestCase):
    def test_a_restarted_process_returns_the_stored_nondelivery_for_a_new_request_id_without_reevaluating(self):
        raw = InMemoryObjectStore(); g = gw(raw, 5); o1 = g.resolve_window("req1", W1, _entry(), I, I, 3, 10, _health()); self.assertEqual(o1.reason, "STALE_WATERMARK")
        g2 = gw(raw, 20); self.assertEqual(g2.final_store.recover(), 1)                                                                # restart: new process objects, the world moved on
        o2 = g2.resolve_window("req2", W1, _entry(), I, I, 3, 10, _health()); self.assertEqual((type(o2).__name__, o2.reason), ("NonDeliveryResolution", "STALE_WATERMARK")); self.assertEqual(g2.final_store.evaluations, 0)
        self.assertEqual(code(g2.final_store.resolve, "req1", D.V.FinalResolutionIdentity("FW", "B1", "XAUUSD", "OTHER"), lambda: "x"), "REQUEST_ID_REBOUND_TO_OTHER_IDENTITY")      # request binding survived restart
    def test_the_parameter_pin_survives_restart_so_another_window_cannot_borrow_the_stored_outcome(self):
        raw = InMemoryObjectStore(); gw(raw).resolve_window("req1", W1, _entry(), I, I, 3, 10, _health()); g2 = gw(raw); g2.final_store.recover()
        self.assertEqual(code(g2.resolve_window, "req2", W1, _entry(), I, I, 3, 11, _health()), "RESOLUTION_IDENTITY_PARAMETERS_DIFFER"); self.assertEqual(code(g2.resolve_window, "req2", W1, _entry(), I, I, 4, 10, _health()), "RESOLUTION_IDENTITY_PARAMETERS_DIFFER")
    def test_a_delivered_binding_round_trips_exactly(self):
        raw = InMemoryObjectStore(); g = gw(raw); b = g.resolve_window("req1", W1, _entry(), I, I, 3, 10, _health()); self.assertIsInstance(b, G.Binding)
        g2 = gw(raw); g2.final_store.recover(); b2 = g2.resolve_window("req9", W1, _entry(), I, I, 3, 10, _health()); self.assertEqual(b2, b); self.assertEqual(g2.final_store.evaluations, 0)
    def test_fresh_window_after_restart_evaluates_and_a_changed_stored_record_is_never_overwritten(self):
        raw = InMemoryObjectStore(); g = gw(raw); g.resolve_window("req1", W1, _entry(), I, I, 3, 10, _health()); g2 = gw(raw); g2.final_store.recover()
        self.assertIsInstance(g2.resolve_window("req5", D.V.FinalResolutionIdentity("FW", "B1", "XAUUSD", "W2"), _entry(), I, I, 3, 10, _health()), G.Binding); self.assertEqual(g2.final_store.evaluations, 1)
        k = [k for k in raw.list_prefix("final-resolution/id/")][0]; before = raw.get(k)[0]; raw._d[k] = (before.replace(b"WINDOW-1", b"WINDOW-X"), 1)                       # tamper the stored identity record
        self.assertEqual(code(gw(raw).final_store.recover), "INTEGRITY_FAILURE")
    def test_orphan_request_binding_without_identity_record_and_unknown_codec_tags_fail_closed(self):
        raw = InMemoryObjectStore(); g = gw(raw); g.resolve_window("req1", W1, _entry(), I, I, 3, 10, _health())
        raw._d = {k: v for k, v in raw._d.items() if "/id/" not in k}; self.assertEqual(code(gw(raw).final_store.recover), "INTEGRITY_FAILURE")
        self.assertEqual(code(D.decode, {"$t": "os.system", "f": {}}), "FINAL_OUTCOME_CODEC_UNKNOWN_TAG"); self.assertEqual(code(D.decode, {"$t": "Ref", "f": {"ref_type": "x"}}), "FINAL_OUTCOME_CODEC_FIELDS_MISMATCH"); self.assertEqual(code(D.encode, object()), "FINAL_OUTCOME_CODEC_TYPE_NOT_ALLOWED")
class PersistedRecordsAreNeverOverwritten(unittest.TestCase):
    """R35 sweep: a fresh process that did NOT recover must still fail closed on a differing stored pin / outcome (put_if_absent loser compares bytes)."""
    def test_unrecovered_store_cannot_replace_a_stored_pin(self):
        raw = InMemoryObjectStore(); a = D.DurableFinalResolutionStore(raw); a.set_pin(W1, ["a"]); b = D.DurableFinalResolutionStore(raw)
        self.assertEqual(code(b.set_pin, W1, ["b"]), "INTEGRITY_FAILURE"); self.assertIsNone(b.pin_of(W1)); self.assertIsNone(code(b.set_pin, W1, ["a"]))        # the failed attempt left no in-memory pin
    def test_unrecovered_store_cannot_store_a_different_outcome_for_the_identity(self):
        raw = InMemoryObjectStore(); gw(raw, 5).resolve_window("req1", W1, _entry(), I, I, 3, 10, _health()); g2 = gw(raw, 20)             # no recover(): the world moved on, evaluation would now DELIVER
        self.assertEqual(code(g2.resolve_window, "req2", W1, _entry(), I, I, 3, 10, _health()), "INTEGRITY_FAILURE")
        self.assertIsNone(g2.final_store.outcome_for(W1)); self.assertIsNone(g2.final_store.identity_of("FW", "req2"))                    # memory never keeps an outcome / request binding the durable store rejected
    def test_a_pin_record_stored_under_the_wrong_key_fails_recovery(self):
        raw = InMemoryObjectStore(); a = D.DurableFinalResolutionStore(raw); a.set_pin(W1, ["a"]); k = list(raw.list_prefix("final-resolution/pin/"))[0]
        raw._d["final-resolution/pin/" + "0" * 64] = raw._d.pop(k); self.assertEqual(code(D.DurableFinalResolutionStore(raw).recover), "INTEGRITY_FAILURE")
if __name__ == "__main__": unittest.main()
