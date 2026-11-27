"""R12: SQE_OPSET_V1_1 reference semantics (comparison, SELECT, elementwise, FIXED_SUM/FIXED_DOT). Evidence at the semantic level only."""
import math, struct, unittest
from fractions import Fraction
from stage_a.errors import Refusal
from stage_a.composer.expression import sqe_opset as S
from tests.trk_stage_a.fixtures import CEILINGS
C = dict(CEILINGS, MAX_BRANCH_COUNT=2, MAX_VECTOR_LENGTH=4, MAX_MATRIX_ROWS=2, MAX_MATRIX_COLS=2, MAX_REDUCTION_LENGTH=4)
def bits(x): return struct.pack(">d", x).hex()
def code(fn, *a):
    try: fn(*a)
    except Refusal as e: return e.code
class T(unittest.TestCase):
    def test_comparisons_and_eq_canonical(self):
        self.assertTrue(S.compare("LT", 1.0, 2.0)); self.assertTrue(S.compare("LE", 2.0, 2.0)); self.assertFalse(S.compare("GT", 1.0, 2.0)); self.assertTrue(S.compare("GE", 2.0, 2.0))
        self.assertTrue(S.eq_canonical(-0.0, 0.0)); self.assertFalse(S.eq_canonical(1.0, 1.0000000000000002))
        self.assertTrue(S.compare("LE", -0.0, 0.0)); self.assertFalse(S.compare("LT", -0.0, 0.0))
    def test_non_finite_inputs_fail_closed(self):
        for bad in (float("nan"), float("inf"), -float("inf")):
            for f in (lambda: S.compare("LT", bad, 1.0), lambda: S.eq_canonical(1.0, bad), lambda: S.scalar("ADD", bad, 1.0), lambda: S.fixed_sum((bad,), 1, C)):
                self.assertEqual(code(f), "NON_FINITE_INPUT")
        self.assertEqual(code(S.compare, "LT", 1, 2.0), "NON_FINITE_INPUT")        # not a binary64 value
    def test_overflow_fails_closed_and_domain_guard(self):
        self.assertEqual(code(S.scalar, "MULTIPLY", 1e308, 10.0), "NON_FINITE_RESULT"); self.assertEqual(code(S.scalar, "DIVIDE_GUARDED", 1.0, -0.0), "DOMAIN_DIV_ZERO")
    def test_signed_zero_canonical_and_subnormal_preserved(self):
        self.assertEqual(bits(S.scalar("ADD", -0.0, -0.0)), bits(0.0)); self.assertEqual(bits(S.scalar("MULTIPLY", -1.0, 0.0)), bits(0.0))
        sub = 5e-324; self.assertEqual(S.scalar("ADD", sub, 0.0), sub); self.assertEqual(S.fixed_sum((sub, sub), 2, C), 1e-323)
    def test_select_is_lazy_and_bounded(self):
        boom = lambda: 1 / 0
        self.assertEqual(S.select(True, lambda: 1.0, boom, C), 1.0); self.assertEqual(S.select(False, boom, lambda: 2.0, C), 2.0)
        self.assertEqual(code(S.select, 1, lambda: 1.0, lambda: 2.0, C), "SELECT_CONDITION_NOT_BOOLEAN")
        self.assertEqual(code(S.select, True, lambda: 1.0, lambda: 2.0, dict(C, MAX_BRANCH_COUNT=1)), "CEILING_BRANCH_COUNT_EXCEEDED")
        self.assertEqual(code(S.select, True, lambda: float("nan"), lambda: 2.0, C), "NON_FINITE_INPUT")
    def test_select_untaken_domain_failure_does_not_refuse(self):
        self.assertEqual(S.select(S.compare("GT", 0.0, 1.0), lambda: S.scalar("DIVIDE_GUARDED", 1.0, 0.0), lambda: 7.0, C), 7.0)
    def test_vector_and_matrix_elementwise_and_shape_failures(self):
        self.assertEqual(S.vector_elementwise("ADD", (1.0, 2.0), (3.0, 4.0), 2, C), (4.0, 6.0))
        self.assertEqual(S.matrix_elementwise("MULTIPLY", ((1.0, 2.0), (3.0, 4.0)), ((2.0, 2.0), (2.0, 2.0)), (2, 2), C), ((2.0, 4.0), (6.0, 8.0)))
        self.assertEqual(code(S.vector_elementwise, "ADD", (1.0,), (3.0, 4.0), 2, C), "SHAPE_MISMATCH")
        self.assertEqual(code(S.vector_elementwise, "DIVIDE_GUARDED", (1.0, 1.0), (1.0, 0.0), 2, C), "DOMAIN_DIV_ZERO")
        self.assertEqual(code(S.vector_elementwise, "ADD", (1.0,) * 5, (1.0,) * 5, 5, C), "CEILING_VECTOR_LENGTH_EXCEEDED")
        self.assertEqual(code(S.vector_elementwise, "ADD", (1.0,), (1.0,), None, C), "SHAPE_NOT_DECLARED")
        self.assertEqual(code(S.matrix_elementwise, "ADD", ((1.0,),) * 3, ((1.0,),) * 3, (3, 1), C), "CEILING_MATRIX_ROWS_EXCEEDED")
        self.assertEqual(code(S.matrix_elementwise, "ADD", ((1.0, 1.0, 1.0),), ((1.0, 1.0, 1.0),), (1, 3), C), "CEILING_MATRIX_COLS_EXCEEDED")
        self.assertEqual(code(S.matrix_elementwise, "ADD", ((1.0, 2.0),), ((1.0,),), (1, 2), C), "SHAPE_MISMATCH")
    def test_fixed_sum_is_sequential_not_pairwise(self):
        v = (1e16, 1.0, 1.0, -1e16)                                      # sequential: ((1e16+1)+1)-1e16 = 0.0 ; pairwise/exact would give 2.0
        self.assertEqual(S.fixed_sum(v, 4, C), 0.0); self.assertEqual(math.fsum(v), 2.0)
    def test_fixed_dot_rounds_product_first_and_differs_from_fma(self):
        a, b, c = 1.0 + 2.0 ** -27, 1.0 + 2.0 ** -27, -(1.0 + 2.0 ** -26)
        fused = float(Fraction(a) * Fraction(b) + Fraction(c))                # correctly rounded single-rounding FMA result
        unfused = (a * b) + c
        self.assertNotEqual(fused, unfused)                               # the chosen inputs genuinely separate FMA from separate rounding
        self.assertEqual(S.fixed_dot((a, 0.0), (b, 0.0), 2, C) + c, unfused)   # (a*b rounded) then + c
        self.assertEqual(S.fixed_dot((a, 1.0), (b, c), 2, dict(C)), (a * b) + c)
        self.assertNotEqual(S.fixed_dot((a, 1.0), (b, c), 2, C), fused)
    def test_reduction_declared_length_and_ceiling(self):
        self.assertEqual(code(S.fixed_sum, (1.0, 2.0), 3, C), "SHAPE_MISMATCH"); self.assertEqual(code(S.fixed_sum, (1.0,) * 5, 5, C), "CEILING_REDUCTION_LENGTH_EXCEEDED")
        self.assertEqual(code(S.fixed_dot, (1.0,), (1.0, 2.0), 1, C), "SHAPE_MISMATCH"); self.assertEqual(S.fixed_sum((), 0, C), 0.0)
        self.assertEqual(code(S.fixed_sum, (1.0,), None, C), "LENGTH_NOT_DECLARED")
    def test_reduction_overflow_midway_fails_closed(self):
        self.assertEqual(code(S.fixed_sum, (1e308, 1e308, -1e308), 3, C), "NON_FINITE_RESULT")     # exact sum would be finite; sequential partial overflows
if __name__ == "__main__": unittest.main()
