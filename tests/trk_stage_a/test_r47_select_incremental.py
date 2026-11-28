"""R47 (root group 1): batch/incremental/reference demand parity for select on the actual StatefulMaterializer; finite-constant validation consistent in every evaluator. A pass clears no gate."""
import unittest
from stage_a.errors import Refusal
from stage_a.storage.object_store import InMemoryObjectStore
from stage_a.composer.expression.manifest import Manifest
from stage_a.composer.expression.evaluator import evaluate
from stage_a.tracker.materialization.stateful_materializer import StatefulMaterializer, IncrementalEvaluator
from stage_a.tracker.verification import independent_traversal as it
from stage_a.tracker.verification.independent_encoding import enc_bytes, parse
from .test_r46_lazy_parity import mk, C, A
def GUARD(): return mk([A, C("z", 0.0), C("o", 1.0), {"id": "c", "op": "gt", "args": ["a", "z"]}, {"id": "d", "op": "div", "args": ["o", "a"]}, {"id": "s", "op": "select", "args": ["c", "d", "z"]}])
def code(f, *a):
    try: f(*a)
    except Refusal as e: return e.code
class IncrementalParity(unittest.TestCase):
    def test_materializer_batch_and_incremental_agree_when_the_untaken_branch_would_fail(self):
        M = Manifest.from_dict(GUARD()); r = StatefulMaterializer(InMemoryObjectStore()).materialize(M, {"close": [0.0]})
        self.assertEqual(r["probe_batch"], ["0000000000000000"]); self.assertEqual(r["probe_incremental"], ["0000000000000000"])
        r = StatefulMaterializer(InMemoryObjectStore()).materialize(M, {"close": [2.0, 4.0]}); self.assertEqual(r["probe_batch"], r["probe_incremental"])      # genuine control
    def test_taken_failure_is_recorded_identically_by_both_paths(self):
        m = mk([A, C("z", 0.0), C("o", 1.0), {"id": "c", "op": "ge", "args": ["a", "z"]}, {"id": "d", "op": "div", "args": ["o", "a"]}, {"id": "s", "op": "select", "args": ["c", "d", "z"]}])
        r = StatefulMaterializer(InMemoryObjectStore()).materialize(Manifest.from_dict(m), {"close": [0.0]}); self.assertEqual((r["probe_batch"], r["probe_incremental"]), ({"error": "DOMAIN_FAILURE"}, {"error": "DOMAIN_FAILURE"}))
    def test_incremental_with_lag_over_select_matches_batch_row_by_row(self):
        m = mk([A, C("z", 0.0), C("o", 1.0), {"id": "c", "op": "gt", "args": ["a", "z"]}, {"id": "d", "op": "div", "args": ["o", "a"]}, {"id": "s", "op": "select", "args": ["c", "d", "z"]}, {"id": "l", "op": "lag", "args": ["s"], "n": 1}])
        M = Manifest.from_dict(m); xs = [0.0, 2.0, -1.0, 4.0]; inc = IncrementalEvaluator(M); got = [inc.push({"close": x}) for x in xs]
        self.assertEqual(got, evaluate(M, {"close": xs})); self.assertEqual(got, it.reference_evaluate(parse(enc_bytes(M.data)), {"close": xs}))
class FiniteConstants(unittest.TestCase):
    def nf(self):
        return mk([A, {"id": "k", "op": "const", "value": "7ff0000000000000"}, C("z", 0.0), C("o", 1.0), {"id": "c", "op": "gt", "args": ["o", "z"]}, {"id": "s", "op": "select", "args": ["c", "a", "k"]}])
    def test_non_finite_constant_in_an_untaken_branch_is_refused_by_every_evaluator(self):
        M = Manifest.from_dict(self.nf())
        self.assertEqual(code(evaluate, M, {"close": [2.0]}), "NON_FINITE_CONST"); self.assertEqual(code(IncrementalEvaluator, M), "NON_FINITE_CONST")
        self.assertEqual(code(StatefulMaterializer(InMemoryObjectStore()).materialize, M, {"close": [2.0]}), "NON_FINITE_CONST")
        with self.assertRaises(it.RefEvalError): it.reference_evaluate(parse(enc_bytes(M.data)), {"close": [2.0]})
if __name__ == "__main__": unittest.main()
