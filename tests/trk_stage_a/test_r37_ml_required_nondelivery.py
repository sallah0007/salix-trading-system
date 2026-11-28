"""R37 F2: ML build_row over the SAME composed window path: a REQUIRED non-delivery needs an explicit tagged exclusion reason; a missing/malformed one fails closed (never `included`)."""
import unittest
from stage_a.gateway import contracts as G
from stage_a.gateway.v038 import FinalResolutionIdentity as FI
from stage_a.ml import receiver as MLR
from . import test_r36_composed_window_path as W
code = W.code
from .test_boundaries import _entry, I, R
from .test_r24_core import NONE_
REASON = ("ENUM", "REASON", "REQUIRED_DEPENDENCY_ABSENT")
class MLRequiredND(unittest.TestCase):
    def test_actual_ml_window_non_delivery_without_a_reason_is_refused_with_a_reason_it_is_excluded_and_an_unrelated_base_is_included(self):
        c, key, F2, b1, b2, raw, gw, hs = W.WindowPath().build(); e1 = _entry(ver="1"); eb = _entry(fid=F2, ver="1")
        nd = gw.resolve_window("ml-nd", FI("ML", "DS-B1", "XAUUSD", "WIN-1"), e1, I, I, 3, 20, hs(key, b1)); self.assertEqual((type(nd).__name__, nd.reason), ("NonDeliveryResolution", "HEALTH_UNACCEPTABLE"))
        def build(cb): return MLR.build_row("r-nd", R("gen"), [e1], [nd], gw, "ORIGINAL_AS_OBSERVED", NONE_, cb, tables=gw.t)
        for bad in (None, (), "x", ("ENUM",), ("ENUM", "REASON"), ("ENUM", "", "X"), ("REF", "notref"), ("ZZZ", "a", "b"), 0, False, []):
            self.assertEqual(code(build, lambda o, b=bad: b), "EXCLUSION_REASON_REQUIRED_FOR_REQUIRED_NON_DELIVERY", bad)
        self.assertEqual(code(build, None), "EXCLUSION_REASON_REQUIRED_FOR_REQUIRED_NON_DELIVERY")
        ex = build(lambda o: REASON); self.assertFalse(ex.included); self.assertEqual((ex.row_exclusion_reason, ex.bindings), (REASON, ()))                      # explicit tagged reason: excluded
        base = gw.resolve_window("ml-b1", FI("ML", "DS-BASE", "XAUUSD", "WIN-1"), eb, I, I, 3, 20, hs("BASE", b2)); self.assertIsInstance(base, G.Binding)
        r = MLR.build_row("r-base", R("gen"), [eb], [base], gw, "ORIGINAL_AS_OBSERVED", NONE_, lambda o: None, tables=gw.t); self.assertTrue(r.included); self.assertEqual(len(r.bindings), 1)   # unrelated BASE: same Core/Gateway, delivered, callback never consulted
if __name__ == "__main__": unittest.main()
