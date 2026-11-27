"""R19: MLCore union-closure duties at the ML_STANDALONE boundary. Edge classes are source-given; kinds/schema are not invented; qualification stays HELD."""
import unittest
from stage_a.errors import Refusal
from stage_a.fw.lanes import ConsumerManifest as M
from stage_a.ml import receiver as R
def code(fn, *a, **k):
    try: return fn(*a, **k)
    except Refusal as e: return e.code
C, A = R.CONTENT_CARRYING, R.ADMINISTRATIVE_ONLY
Q = b"q"
class Union(unittest.TestCase):
    def test_no_edges_supplied_is_unproven_not_independent(self):
        g = {"m": M("m", "ML", (b"a",))}; r = R.check_standalone(g["m"], Q, g, "ML_STANDALONE"); self.assertEqual(r.union_closure, R.UNION_CLOSURE_UNPROVEN)
    def test_content_carrying_path_to_a_taint_source_is_refused_across_edge_kinds(self):
        edges = [("m", "feat", C), ("feat", "model", C), ("model", "gen-fw", C)]
        self.assertEqual(code(R.union_closure, "m", edges, {"gen-fw"}), "HIDDEN_FW_ANCESTRY")
    def test_administrative_only_edge_does_not_taint_but_unknown_class_fails_closed(self):
        self.assertEqual(R.union_closure("m", [("m", "gen-fw", A), ("m", "feat", C)], {"gen-fw"}), ("feat",))
        for cls in ("UNKNOWN", "", None, "content_carrying"): self.assertEqual(code(R.union_closure, "m", [("m", "x", cls)], set()), "UNCLASSIFIED_EDGE", cls)
    def test_unclassified_edge_off_the_reachable_set_is_not_traversed(self):
        self.assertEqual(R.union_closure("m", [("other", "x", "???"), ("m", "p", C)], set()), ("p",))
    def test_cycles_terminate_and_malformed_edges_refuse(self):
        self.assertEqual(R.union_closure("a", [("a", "b", C), ("b", "a", C)], set()), ("b",))
        self.assertEqual(code(R.union_closure, "m", [("m", "x")], set()), "EDGE_MALFORMED")
    def test_traversed_result_is_still_never_qualified(self):
        g = {"m": M("m", "ML", (b"a",))}; r = R.check_standalone(g["m"], Q, g, "ML_STANDALONE", edges=[("m", "p", C)])
        self.assertEqual((r.union_closure, r.reached), (R.UNION_CLOSURE_TRAVERSED, ("p",)))
        for chk in (r, R.check_standalone(g["m"], Q, g, "ML_STANDALONE"), None, "x"): self.assertEqual(code(R.require_standalone_qualified, chk), "UNION_CLOSURE_COMPLETENESS_UNPROVEN")
    def test_linear_checks_still_run_first(self):
        g = {"fw": M("fw", "FW", ()), "m": M("m", "ML", (), derived_from="fw")}; self.assertEqual(code(R.check_standalone, g["m"], Q, g, "ML_STANDALONE", edges=[]), "HIDDEN_FW_ANCESTRY")
if __name__ == "__main__": unittest.main()
