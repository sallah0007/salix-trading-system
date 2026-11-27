"""R16: ML_STANDALONE transitive FW ancestry (Build Plan 13.1). The whole derivation chain is traversed; unknown required ancestry refuses; the unaffected baseline passes."""
import unittest
from stage_a.errors import Refusal
from stage_a.fw.lanes import ConsumerManifest as M, BASELINE
from stage_a.ml import receiver as R
Q = b"q"
def code(fn, *a, **k):
    try: return fn(*a, **k)
    except Refusal as e: return e.code
S = lambda g, k: R.check_generation(g[k], Q, g, "ML_STANDALONE")
class Transitive(unittest.TestCase):
    def test_reported_reproduction_two_hops_now_refused(self):
        g = {"fw": M("fw", "FW", ()), "ml1": M("ml1", "ML", (), derived_from="fw"), "ml2": M("ml2", "ML", (), derived_from="ml1")}
        self.assertEqual(code(S, g, "ml2"), "HIDDEN_FW_ANCESTRY")
        self.assertEqual(code(S, g, "ml1"), "HIDDEN_FW_ANCESTRY")                     # one hop still refused
    def test_many_hops(self):
        g = {"fw": M("fw", "FW", ())}; prev = "fw"
        for i in range(8): g["m%d" % i] = M("m%d" % i, "ML", (), derived_from=prev); prev = "m%d" % i
        self.assertEqual(code(S, g, "m7"), "HIDDEN_FW_ANCESTRY")
    def test_unresolved_ancestry_refuses_at_any_depth(self):
        g = {"ml1": M("ml1", "ML", (), derived_from="gone"), "ml2": M("ml2", "ML", (), derived_from="ml1")}
        self.assertEqual(code(S, g, "ml2"), "DERIVED_FROM_UNRESOLVED"); self.assertEqual(code(S, g, "ml1"), "DERIVED_FROM_UNRESOLVED")
    def test_cycle_refuses(self):
        g = {"a": M("a", "ML", (), derived_from="b"), "b": M("b", "ML", (), derived_from="a")}
        self.assertEqual(code(S, g, "a"), "DERIVATION_CYCLE")
        g = {"a": M("a", "ML", (), derived_from="a")}; self.assertEqual(code(S, g, "a"), "DERIVATION_CYCLE")
    def test_graph_entry_under_another_id_refuses(self):
        g = {"p": M("other", "ML", ()), "m": M("m", "ML", (), derived_from="p")}; self.assertEqual(code(S, g, "m"), "GRAPH_KEY_MISMATCH")
    def test_ancestry_itself_refuses_a_misbound_entry(self):       # R18: lanes.closure_contains_target now also checks the key, so this pins ancestry() directly
        g = {"p": M("other", "ML", ()), "m": M("m", "ML", (), derived_from="p")}; self.assertEqual(code(R.ancestry, g["m"], g), "GRAPH_KEY_MISMATCH")
    def test_unknown_ancestor_kind_refuses(self):
        g = {"p": M("p", "X", ()), "m": M("m", "ML", (), derived_from="p")}; self.assertEqual(code(S, g, "m"), "UNKNOWN_ANCESTOR_KIND")
    def test_unaffected_baseline_positive_controls(self):
        self.assertEqual(S({"m": M("m", "ML", (b"a",))}, "m"), BASELINE)                                   # no ancestry
        g = {"p": M("p", "ML", ()), "q": M("q", "ML", (), derived_from="p"), "m": M("m", "ML", (), derived_from="q")}
        self.assertEqual(S(g, "m"), BASELINE)                                                              # ML-only chain: not blocked
    def test_kind_and_manifest_type_fail_closed(self):
        g = {"m": M("m", "ML", ())}
        self.assertEqual(code(R.check_generation, g["m"], Q, g, "ML_OTHER"), "UNKNOWN_GENERATION_KIND")
        g = {"f": M("f", "FW", ())}; self.assertEqual(code(R.check_generation, g["f"], Q, g, "ML_STANDALONE"), "STANDALONE_REQUIRES_ML_MANIFEST")
    def test_target_in_closure_still_hidden_quant(self):
        g = {"p": M("p", "ML", (Q,)), "m": M("m", "ML", (), derived_from="p")}; self.assertEqual(code(S, g, "m"), "HIDDEN_QUANT_ANCESTOR")
if __name__ == "__main__": unittest.main()
class AsOfStamps(unittest.TestCase):
    def test_as_of_visible_fails_closed_on_malformed_stamps_and_ignores_effective_time(self):
        from stage_a.context.decision_context import as_of_visible
        ok = {"CREATED_AT": 5, "AVAILABLE_ASOF": 6, "EFFECTIVE_AT": 1}
        self.assertTrue(as_of_visible(ok, 6)); self.assertFalse(as_of_visible(ok, 5))          # EFFECTIVE_AT=1 never makes it visible earlier
        for bad in ("5", 5.0, True, None):
            self.assertEqual(code(as_of_visible, dict(ok, CREATED_AT=bad), 9), "AS_OF_TIMESTAMP_MALFORMED")
            self.assertEqual(code(as_of_visible, dict(ok, AVAILABLE_ASOF=bad), 9), "AS_OF_TIMESTAMP_MALFORMED")
            self.assertEqual(code(as_of_visible, ok, bad), "AS_OF_TIMESTAMP_MALFORMED")
        self.assertEqual(code(as_of_visible, {"CREATED_AT": 1}, 9), "AS_OF_TIMESTAMP_MALFORMED")
