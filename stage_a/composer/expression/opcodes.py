"""Admitted opcode table. ALIGNED (R11) to SQE_OPSET_V1_1 (Parent V1.2 Drive 1i5P8zxQmvBDKz397BxIUKM8AnBY00-ItzLMOjNGOkRM lines 116-204;
Annex V1.2 Drive 13PE_pli3ZlFjjPdhHtWtLyyH2XdAv8XGA4FN0KGcIlA lines 84-121). Names are THIS repository's lowercase identifiers; numeric opcode codes and the
canonical program byte grammar are NOT assigned by any source read and are NOT invented here.
Mapping to the source operator names (documentary; no rename):
  add->ADD  sub->SUBTRACT  mul->MULTIPLY  div->DIVIDE_GUARDED  neg->NEGATE  abs->ABS  sqrt->SQRT_GUARDED  min->MIN_TOTAL  max->MAX_TOTAL
  rolling_sum ~ FIXED_SUM (ascending sequential accumulation from +0); rolling_mean = FIXED_SUM then DIVIDE_GUARDED by the declared length (composite)
  input, const, lag: structural / state-table constructs NOT named in the SQE_OPSET_V1_1 operator list (source-unbound; retained as prototype constructs)
NOT admitted (PROFILE_ONLY): log (removed in R11; it was wrongly admitted), exp, pow, any transcendental; vector/matrix/FIXED_DOT are admitted by the source but NOT implemented here (no shape typing exists in this prototype; absent behaviour, not invented).
R45 adds lt/le/gt/ge/eq_canonical + select with an explicit boolean TYPE (never a number: no 0/1 encoding is invented); numeric wire codes remain unassigned.
Arithmetic semantics are in evaluator.py. UNDEFINED (None) = missing-input propagation only (source-unbound)."""
from collections import namedtuple

OpSpec = namedtuple("OpSpec", "arity windowed capability")

OPCODES = {
    "input":        OpSpec(0, False, "INPUT_SERIES"),
    "const":        OpSpec(0, False, "CONST_BINARY64"),
    "add":          OpSpec(2, False, "ARITH_BINARY64"),
    "sub":          OpSpec(2, False, "ARITH_BINARY64"),
    "mul":          OpSpec(2, False, "ARITH_BINARY64"),
    "div":          OpSpec(2, False, "ARITH_BINARY64"),
    "min":          OpSpec(2, False, "ARITH_BINARY64"),
    "max":          OpSpec(2, False, "ARITH_BINARY64"),
    "neg":          OpSpec(1, False, "ARITH_BINARY64"),
    "abs":          OpSpec(1, False, "ARITH_BINARY64"),
    "sqrt":         OpSpec(1, False, "ELEMENTARY_BINARY64"),
    "lt":           OpSpec(2, False, "COMPARE_BINARY64"),   # R45: boolean-typed result (see schema.py type check); consumable ONLY as select's first arg
    "le":           OpSpec(2, False, "COMPARE_BINARY64"),
    "gt":           OpSpec(2, False, "COMPARE_BINARY64"),
    "ge":           OpSpec(2, False, "COMPARE_BINARY64"),
    "eq_canonical": OpSpec(2, False, "COMPARE_BINARY64"),   # equality after +0 canonicalisation of both operands
    "select":       OpSpec(3, False, "SELECT_BOUNDED"),     # args (cond:boolean, if_true, if_false); LAZY: only the taken branch is evaluated at an index
    "lag":          OpSpec(1, True, "WINDOW_LAG"),
    "rolling_sum":  OpSpec(1, True, "WINDOW_ROLLING"),
    "rolling_mean": OpSpec(1, True, "WINDOW_ROLLING"),
}
EMULATED = frozenset({"exp", "pow", "tanh", "sin", "cos", "tan", "erf"})
# Refused distinctly: named by SQE_OPSET_V1_1 as NOT ADMITTED for PROFILE_ONLY (a later governed operator-set successor would be required).
NOT_ADMITTED_PROFILE_ONLY = frozenset({"log"})
