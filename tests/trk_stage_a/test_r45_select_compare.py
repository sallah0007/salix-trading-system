"""R45: source-admitted comparison + bounded SELECT (lazy). Names are this repository's lowercase identifiers; numeric wire codes remain UNASSIGNED.
Booleans are a TYPE only (no 0/1 encoding is invented). Mutants: mutation_sweep_r45.py. A passing test clears no gate."""
import unittest
from stage_a.errors import Refusal
from stage_a.composer.expression.manifest import Manifest
from stage_a.composer.expression.evaluator import encode_const, evaluate, evaluate_lazy
from stage_a.composer.expression.ceilings import check_program_within, CEILING_KEYS
from stage_a.tracker.verification import independent_traversal as it
from stage_a.tracker.verification.independent_encoding import enc_bytes, parse
from .test_r11_arithmetic import man, A

C = lambda i, x: {"id": i, "op": "const", "value": encode_const(x)}
CAPS = ["ARITH_BINARY64", "COMPARE_BINARY64", "CONST_BINARY64", "INPUT_SERIES", "SELECT_BOUNDED"]
OPS = ["const", "div", "gt", "input", "select"]
# select(gt(a,0), div(1,a), 0): the untaken branch (div by zero) must NOT fire where a<=0
def guarded(cmp="gt"):
    return man([A, C("z", 0.0), C("o", 1.0), {"id": "c", "op": cmp, "args": ["a", "z"]}, {"id": "d", "op": "div", "args": ["o", "a"]},
                {"id": "s", "op": "select", "args": ["c", "d", "z"]}], sorted(set(["const", "div", cmp, "input", "select"])),
               CAPS, "s")
def ev(m, xs):
    M = Manifest.from_dict(m); return evaluate(M, {"close": xs})

class Select(unittest.TestCase):
    def test_untaken_branch_does_not_fire_and_taken_branch_value(self):
        self.assertEqual(ev(guarded(), [2.0, 0.0, -0.0, 4.0]), [0.5, 0.0, 0.0, 0.25])
    def test_taken_branch_domain_failure_surfaces(self):
        m = guarded("ge")                                   # now a==0 takes div(1,0)
        with self.assertRaises(Refusal) as c: ev(m, [2.0, 0.0])
        self.assertEqual(c.exception.code, "DOMAIN_DIV_ZERO")
    def test_missing_condition_propagates_undefined(self):
        self.assertEqual(ev(guarded(), [None, 2.0]), [None, 0.5])
    def test_comparisons_semantics_and_signed_zero(self):
        for op, want in (("lt", [True, False, False]), ("le", [True, True, False]), ("gt", [False, False, True]), ("ge", [False, True, True]), ("eq_canonical", [False, True, False])):
            m = man([A, C("z", 0.0), C("o", 1.0), {"id": "c", "op": op, "args": ["a", "z"]}, {"id": "s", "op": "select", "args": ["c", "o", "z"]}],
                    sorted(["const", op, "input", "select"]), ["COMPARE_BINARY64", "CONST_BINARY64", "INPUT_SERIES", "SELECT_BOUNDED"], "s")
            self.assertEqual(ev(m, [-1.0, -0.0, 1.0]), [1.0 if w else 0.0 for w in want], op)
    def test_lazy_equals_eager_on_programs_without_select(self):
        from .fixtures import momentum_manifest
        M = Manifest.from_dict(momentum_manifest()); s = {k: [1.0, 2.5, 4.0, 3.0, 9.0, 0.5, 7.0, 7.0] for k in M.data["inputs"]}
        self.assertEqual(evaluate(M, s), evaluate_lazy(M, s, 8))

class Typing(unittest.TestCase):
    def test_boolean_cannot_be_output_or_arithmetic_operand_or_select_value(self):
        bad = [man([A, C("z", 0.0), {"id": "c", "op": "gt", "args": ["a", "z"]}], ["const", "gt", "input"], ["COMPARE_BINARY64", "CONST_BINARY64", "INPUT_SERIES"], "c"),
               man([A, C("z", 0.0), {"id": "c", "op": "gt", "args": ["a", "z"]}, {"id": "x", "op": "add", "args": ["c", "a"]}], ["add", "const", "gt", "input"], ["ARITH_BINARY64", "COMPARE_BINARY64", "CONST_BINARY64", "INPUT_SERIES"], "x"),
               man([A, C("z", 0.0), {"id": "s", "op": "select", "args": ["a", "z", "z"]}], ["const", "input", "select"], ["CONST_BINARY64", "INPUT_SERIES", "SELECT_BOUNDED"], "s")]
        for m in bad:
            with self.assertRaises(Refusal) as c: Manifest.from_dict(m)
            self.assertIn(c.exception.code, ("OUTPUT_NOT_F64", "TYPE_MISMATCH"))

class Ceiling(unittest.TestCase):
    def test_branch_ceiling_enforced(self):
        M = Manifest.from_dict(guarded()); ok = {k: 100 for k in CEILING_KEYS}
        check_program_within(M, ok)
        with self.assertRaises(Refusal) as c: check_program_within(M, dict(ok, MAX_BRANCH_COUNT=0))
        self.assertEqual(c.exception.code, "CEILING_BRANCH_COUNT_EXCEEDED")

class IndependentAgreement(unittest.TestCase):
    def test_reference_agrees_including_lazy_failure_semantics(self):
        for m, xs in ((guarded(), [2.0, 0.0, -0.0, 4.0, -3.0]), (guarded("ge"), [2.0, 1.0])):
            M = Manifest.from_dict(m); p = parse(enc_bytes(M.data)); s = {"close": xs}
            try: want = evaluate(M, s)
            except Refusal: want = "FAIL"
            try: got = it.reference_evaluate(p, s)
            except it.RefEvalError: got = "FAIL"
            self.assertEqual(got, want)
    def test_reference_missing_condition_is_undefined_not_false(self):
        # reference_evaluate rejects None inputs? use a lag so the condition is undefined at warm-up row 0
        m = man([A, {"id": "l", "op": "lag", "args": ["a"], "n": 1}, C("z", 0.0), {"id": "c", "op": "gt", "args": ["l", "z"]},
                 {"id": "s", "op": "select", "args": ["c", "a", "z"]}], sorted(["const", "gt", "input", "lag", "select"]),
                ["COMPARE_BINARY64", "CONST_BINARY64", "INPUT_SERIES", "SELECT_BOUNDED", "WINDOW_LAG"], "s")
        M = Manifest.from_dict(m); p = parse(enc_bytes(M.data)); s = {"close": [5.0, 6.0, -1.0]}
        self.assertEqual(evaluate(M, s), [None, 6.0, -1.0]); self.assertEqual(it.reference_evaluate(p, s), [None, 6.0, -1.0])
    def test_reference_untaken_failure_does_not_surface_but_taken_does(self):
        M = Manifest.from_dict(guarded()); p = parse(enc_bytes(M.data))
        self.assertEqual(it.reference_evaluate(p, {"close": [0.0]}), [0.0])
        M2 = Manifest.from_dict(guarded("ge")); p2 = parse(enc_bytes(M2.data))
        with self.assertRaises(it.RefEvalError): it.reference_evaluate(p2, {"close": [0.0]})

if __name__ == "__main__":
    unittest.main()
