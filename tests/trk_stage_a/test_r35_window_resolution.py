import unittest
from stage_a.errors import Refusal
from stage_a.gateway import contracts as G
from stage_a.gateway.v038 import FinalResolutionStore, FinalResolutionIdentity as FI
from stage_a.fw.association import FwAssociation
from stage_a.fw import receiver as FWR
from stage_a.ml import receiver as MLR
from .test_boundaries import _gw, _entry, _health, I, R, T
def code(f, *a, **k):
    try: f(*a, **k)
    except Refusal as e: return e.code
W1 = FI("FW", "B1", "XAUUSD", "WINDOW-1"); W2 = FI("FW", "B1", "XAUUSD", "WINDOW-2")
def gw():
    g = _gw(); g.final_store = FinalResolutionStore(); return g
class WindowLevelResolution(unittest.TestCase):
    def test_root_repro_new_request_id_same_window_reuses_the_stored_outcome_not_a_second_evaluation(self):
        g = gw(); g.set_watermark(5); e = _entry()
        o1 = g.resolve_window("req1", W1, e, I, I, 3, 10, _health()); self.assertEqual((type(o1).__name__, o1.reason), ("NonDeliveryResolution", "STALE_WATERMARK"))
        g.set_watermark(20)                                                                                                       # the world moved on; the final outcome for the window must not
        self.assertIs(g.resolve_window("req1", W1, e, I, I, 3, 10, _health()), o1)                                               # same request retry
        o2 = g.resolve_window("req2", W1, e, I, I, 3, 10, _health()); self.assertIs(o2, o1); self.assertEqual(g.final_store.evaluations, 1)   # NEW request id, same identity: reused (the pre-R35 resolve() re-evaluated this)
        self.assertIs(g.outcome("req2", "FW"), o1); self.assertIsNone(g.outcome("req2")); self.assertIsNone(g.outcome("req2", "ML"))        # consumer-local namespace: not a global request-id cache entry
    def test_without_the_window_path_the_request_id_keyed_resolver_still_reevaluates_so_the_new_path_is_the_one_that_matters(self):
        g = _gw(); g.set_watermark(5); e = _entry(); a = g.resolve("r1", e, I, I, 3, 10, _health()); g.set_watermark(20); b = g.resolve("r2", e, I, I, 3, 10, _health()); self.assertNotEqual(a.reason, getattr(b, "reason", None))
    def test_same_identity_with_other_parameters_is_refused_and_a_new_window_is_evaluated_fresh(self):
        g = gw(); g.set_watermark(5); e = _entry(); g.resolve_window("req1", W1, e, I, I, 3, 10, _health()); g.set_watermark(20)
        self.assertEqual(code(g.resolve_window, "req3", W1, e, I, I, 3, 11, _health()), "RESOLUTION_IDENTITY_PARAMETERS_DIFFER")        # other fence under the same identity
        self.assertEqual(code(g.resolve_window, "req3", W1, e, I, I, 4, 10, _health()), "RESOLUTION_IDENTITY_PARAMETERS_DIFFER")        # other step
        self.assertEqual(code(g.resolve_window, "req3", W1, _entry(ver="f2"), I, I, 3, 10, _health()), "RESOLUTION_IDENTITY_PARAMETERS_DIFFER")
        self.assertEqual(code(g.resolve_window, "req1", W2, e, I, I, 3, 10, _health()), "REQUEST_ID_REBOUND_TO_OTHER_IDENTITY")           # a request id belongs to one identity
        o = g.resolve_window("req4", W2, e, I, I, 3, 10, _health()); self.assertIsInstance(o, G.Binding)                                  # a different window, fresh evaluation
    def test_store_required_and_request_ids_used_outside_the_window_path_are_refused(self):
        self.assertEqual(code(_gw().resolve_window, "r", W1, _entry(), I, I, 3, 10, _health()), "GATEWAY_FINAL_RESOLUTION_STORE_NOT_CONFIGURED")
        g = gw(); g.resolve("legacy", _entry(), I, I, 3, 10, _health()); self.assertEqual(code(g.resolve_window, "legacy", W1, _entry(), I, I, 3, 10, _health()), "REQUEST_ID_USED_OUTSIDE_THIS_WINDOW")
    def test_one_window_outcome_flows_through_fw_association_and_the_exact_fw_and_ml_receivers(self):
        g = gw(); e = _entry(); a = FwAssociation(g.final_store)
        b1 = g.resolve_window("req1", W1, e, I, I, 3, 10, _health()); self.assertIsInstance(b1, G.Binding)
        b2 = g.resolve_window("req2", W1, e, I, I, 3, 10, _health()); assoc = a.associate_request("req2", W1); self.assertEqual(assoc, b1)                  # association over the SAME actual store and outcome
        self.assertIs(FWR.receive_verified(b2, e, I, I, T, g), b1)                                                                         # exact FW receive of the stored outcome (request id inside is req1: identity-preserved)
        from .test_boundaries import NONE_
        WM = FI("ML", "B2", "XAUUSD", "WINDOW-1"); m1 = g.resolve_window("req1", WM, e, I, I, 3, 10, _health())                  # an INDEPENDENT ML consumer reuses the same local request id "req1" (H1: REQUEST_ID is consumer-local)
        self.assertIsInstance(m1, G.Binding); self.assertIsNot(m1, b1)
        self.assertTrue(MLR.build_row("r", R("gen"), [e], [m1], g, "ORIGINAL_AS_OBSERVED", NONE_, lambda o: NONE_, tables=g.t).included)
        self.assertEqual(code(MLR.build_row, "r", R("gen"), [e], [b1], g, "ORIGINAL_AS_OBSERVED", NONE_, lambda o: NONE_, tables=g.t), "BINDING_NOT_FROM_GATEWAY")   # the FW consumer's window outcome is not an ML-issued outcome
        a.record_return("E1", "req2", "EVIDENCE"); self.assertEqual(a.returns_for(W1)[0].resolution_identity, W1)
class StoreHandlesAreDetached(unittest.TestCase):
    def test_outcomes_listing_is_a_detached_copy_and_a_pin_cannot_be_replaced(self):
        st = FinalResolutionStore(); i = FI("FW", "B1", "XAUUSD", "W1"); st.resolve("r1", i, lambda: {"o": [1]})
        for _, o in st.outcomes(): o["o"].append(2)
        self.assertEqual(st.outcomes()[0][1], {"o": [1]})
        st.set_pin(i, ["p"]); self.assertEqual(code(st.set_pin, i, ["q"]), "RESOLUTION_IDENTITY_PARAMETERS_DIFFER"); self.assertIsNone(code(st.set_pin, i, ["p"]))
if __name__ == "__main__": unittest.main()
