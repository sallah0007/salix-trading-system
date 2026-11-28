"""R46 typed fixed-shape candidate operators (Annex III state schema typing; SQE_OPSET_V1_1 vector/matrix/FIXED_SUM/FIXED_DOT rules). Not wired into the manifest DAG (named residual). A pass clears no gate."""
import unittest, struct
from fractions import Fraction
from stage_a.errors import Refusal
from stage_a.composer.expression import typed_shapes as T
from stage_a.composer.expression.typed_shapes import Typed, elementwise, fixed_sum, fixed_dot, validate_state_schema
VEC, MAT, SC = "FIXED_VECTOR_BINARY64", "FIXED_MATRIX_BINARY64", "BINARY64_SCALAR"
def code(f, *a, **k):
    try: f(*a, **k)
    except Refusal as e: return e.code
def comp(n="v", t=VEC, r=1, d=(3,), p=True): return {"COMPONENT_NAME": n, "COMPONENT_TYPE": t, "SHAPE_RANK": r, "SHAPE_DIMENSIONS": list(d), "PUBLISHED": p}
CEIL = {"MAX_VECTOR_LENGTH": 4, "MAX_MATRIX_ROWS": 2, "MAX_MATRIX_COLS": 2}
class Schema(unittest.TestCase):
    def test_valid_schema_in_order_and_each_closed_rule(self):
        out = validate_state_schema([comp("a", SC, 0, ()), comp("v"), comp("m", MAT, 2, (2, 2))], CEIL); self.assertEqual([c["COMPONENT_NAME"] for c in out], ["a", "v", "m"])
        for bad, c in ((comp("v", "FIXED_TENSOR"), "STATE_COMPONENT_TYPE_NOT_ADMITTED"), (comp("v", r=2), "STATE_SHAPE_DIMENSIONS_DO_NOT_MATCH_RANK"), (comp("v", d=(0,)), "STATE_SHAPE_DIMENSIONS_DO_NOT_MATCH_RANK"),
                       (comp("s", SC, 1, (2,)), "STATE_SCALAR_HAS_DIMENSIONS"), (comp("v", VEC, 2, (2, 2)), "STATE_VECTOR_NEEDS_ONE_DIMENSION"), (comp("m", MAT, 1, (2,)), "STATE_MATRIX_NEEDS_TWO_DIMENSIONS"),
                       (comp("v", p="yes"), "STATE_COMPONENT_PUBLISHED_NOT_BOOL"), (comp(""), "STATE_COMPONENT_NAME"), (comp("v", d=(5,)), "CEILING_VECTOR_LENGTH_EXCEEDED"), (comp("m", MAT, 2, (3, 1)), "CEILING_MATRIX_SHAPE_EXCEEDED")):
            self.assertEqual(code(validate_state_schema, [bad], CEIL), c)
        self.assertEqual(code(validate_state_schema, [comp("v"), comp("v")]), "STATE_COMPONENT_NAME"); self.assertEqual(code(validate_state_schema, []), "STATE_SCHEMA_COMPONENTS_REQUIRED")
        self.assertEqual(code(validate_state_schema, [dict(comp("v"), EXTRA=1)]), "STATE_COMPONENT_FIELD_SET")
class Ops(unittest.TestCase):
    V = lambda s, *x: Typed(VEC, (len(x),), list(x))
    def test_vector_and_matrix_elementwise_and_signed_zero(self):
        self.assertEqual(elementwise("add", self.V(1.0, 2.0), self.V(3.0, 4.0)).data, (4.0, 6.0)); self.assertEqual(elementwise("mul", self.V(-0.0, 2.0), self.V(1.0, 1.0)).data, (0.0, 2.0)); self.assertEqual(struct.pack(">d", elementwise("mul", self.V(-0.0), self.V(1.0)).data[0]), struct.pack(">d", 0.0))
        m = lambda *r: Typed(MAT, (len(r), len(r[0])), list(r)); self.assertEqual(elementwise("sub", m([1.0, 2.0], [3.0, 4.0]), m([1.0, 1.0], [1.0, 1.0])).data, ((0.0, 1.0), (2.0, 3.0)))
    def test_guarded_divide_zero_denominator_in_any_position_fails_and_shape_mismatch_fails_closed(self):
        self.assertEqual(code(elementwise, "div", self.V(1.0, 2.0), self.V(1.0, 0.0)), "DOMAIN_DIV_ZERO"); self.assertEqual(code(elementwise, "div", self.V(1.0), self.V(-0.0)), "DOMAIN_DIV_ZERO")
        self.assertEqual(code(elementwise, "add", self.V(1.0, 2.0), self.V(1.0)), "SHAPE_MISMATCH"); self.assertEqual(code(elementwise, "add", self.V(1.0), Typed(SC, (), 1.0)), "SHAPE_MISMATCH")
        self.assertEqual(code(elementwise, "add", Typed(MAT, (1, 2), [[1.0, 2.0]]), Typed(MAT, (2, 1), [[1.0], [2.0]])), "SHAPE_MISMATCH")
        self.assertEqual(code(elementwise, "pow", self.V(1.0), self.V(1.0)), "UNKNOWN_OPCODE")
    def test_overflow_and_non_finite_fail_closed(self):
        self.assertEqual(code(elementwise, "mul", self.V(1e308), self.V(10.0)), "NON_FINITE_RESULT"); self.assertEqual(code(Typed, VEC, (1,), [float("nan")]), "SHAPE_ELEMENT_NOT_FINITE_BINARY64"); self.assertEqual(code(Typed, VEC, (2,), [1.0]), "SHAPE_MISMATCH"); self.assertEqual(code(Typed, VEC, (1,), [1]), "SHAPE_ELEMENT_NOT_FINITE_BINARY64")
    def test_fixed_sum_is_sequential_ascending_not_reassociated(self):
        v = self.V(1e16, 1.0, 1.0, -1e16)                   # sequential: ((1e16+1)=1e16, +1 = 1e16, -1e16 = 0.0); a pairwise/Kahan sum would give 2.0
        self.assertEqual(fixed_sum(v).data, 0.0); self.assertEqual(fixed_sum(self.V(-0.0)).data, 0.0)
        self.assertEqual(code(fixed_sum, Typed(SC, (), 1.0)), "SHAPE_MISMATCH")
    def test_fixed_dot_rounds_each_product_first_and_differs_from_fused(self):
        a = 134217729.0; p = a * a; self.assertNotEqual(Fraction(a) * Fraction(a) - Fraction(p), 0)      # the exact product is NOT representable: a fused op would keep the residual
        self.assertEqual(fixed_dot(self.V(a, 1.0), self.V(a, -p)).data, 0.0); self.assertEqual(fixed_dot(self.V(1.0, a), self.V(-p, a)).data, 0.0)      # second order: a fused multiply-add would give 1.0
        self.assertEqual(code(fixed_dot, self.V(1.0, 2.0), self.V(1.0)), "SHAPE_MISMATCH"); self.assertEqual(code(fixed_dot, Typed(MAT, (1, 1), [[1.0]]), Typed(MAT, (1, 1), [[1.0]])), "SHAPE_MISMATCH")
        self.assertEqual(fixed_dot(self.V(1.0, 2.0, 3.0), self.V(4.0, 5.0, 6.0)).data, 32.0)
    def test_not_admitted_operations_are_refused_by_name(self):
        for n in ("matmul", "transpose", "inverse", "solve", "decompose"): self.assertEqual(code(T.refuse_not_admitted, n), "OPCODE_NOT_ADMITTED_SQE_OPSET_V1_1")
        T.refuse_not_admitted("fixed_dot")
if __name__ == "__main__": unittest.main()
