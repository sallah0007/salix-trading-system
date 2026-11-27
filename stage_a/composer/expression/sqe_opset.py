"""SQE_OPSET_V1_1 reference semantics for the source-ADMITTED operations that the prototype manifest does not carry as opcodes:
comparison (LT/LE/GE/GT/EQ_CANONICAL), SELECT, VECTOR_/MATRIX_ELEMENTWISE_*, FIXED_SUM, FIXED_DOT.
Source: Parent V1.2 (Drive 1i5P8zxQmvBDKz397BxIUKM8AnBY00-ItzLMOjNGOkRM) lines ~116-204; Annex V1.2 (Drive 13PE_pli3ZlFjjPdhHtWtLyyH2XdAv8XGA4FN0KGcIlA) lines 84-121.
SEMANTIC library only. It is NOT wired into manifest admission and is NOT claimed as a full SQE_OPSET implementation: no numeric opcode table and no program
byte grammar exist in any source read, so these operations cannot be admitted into a canonical program encoding yet (that blocks encoding/admission, not
semantic evaluation or reference validation). Every size/shape bound comes from the caller's validated governed ceilings: nothing is defaulted.
NOT implemented (exact missing semantic rule): multi-branch CASE (the source gives no priority/tie rule when several conditions hold); boolean typing inside
the manifest graph; MIN_TOTAL/MAX_TOTAL beyond the manifest min/max already present."""
import math, struct
from ...errors import Refusal
from .evaluator import canon

def _in(x):
    if type(x) is not float or not math.isfinite(x):
        raise Refusal(repr(x), code="NON_FINITE_INPUT")                      # every operator input must be finite binary64
    return canon(x)
def _out(x):
    if not math.isfinite(x):
        raise Refusal("non-finite result", code="NON_FINITE_RESULT")
    return canon(x)

def _div(a, b):
    if b == 0.0: raise Refusal("zero denominator", code="DOMAIN_DIV_ZERO")
    return a / b
_BIN = {"ADD": lambda a, b: a + b, "SUBTRACT": lambda a, b: a - b, "MULTIPLY": lambda a, b: a * b, "DIVIDE_GUARDED": _div}

def scalar(op, a, b):
    return _out(_BIN[op](_in(a), _in(b)))

# --- comparison / control --------------------------------------------------------------------------------------------
_CMP = {"LT": lambda a, b: a < b, "LE": lambda a, b: a <= b, "GE": lambda a, b: a >= b, "GT": lambda a, b: a > b}
def compare(op, a, b) -> bool:
    return _CMP[op](_in(a), _in(b))
def eq_canonical(a, b) -> bool:
    """Exact 64-bit equality of the canonical binary64 encodings after signed-zero canonicalisation."""
    return struct.pack(">d", _in(a)) == struct.pack(">d", _in(b))
def select(cond, then_thunk, else_thunk, ceilings):
    """Declared bounded branches only: exactly two. The untaken branch is never evaluated (no side effects, no domain failure)."""
    if type(cond) is not bool: raise Refusal(repr(cond), code="SELECT_CONDITION_NOT_BOOLEAN")
    if 2 > ceilings["MAX_BRANCH_COUNT"]: raise Refusal("2>%d" % ceilings["MAX_BRANCH_COUNT"], code="CEILING_BRANCH_COUNT_EXCEEDED")
    return _in((then_thunk if cond else else_thunk)())

# --- fixed-shape elementwise ------------------------------------------------------------------------------------------
def vector_elementwise(op, a, b, shape, ceilings):
    if not (isinstance(shape, int) and not isinstance(shape, bool) and shape >= 0): raise Refusal(repr(shape), code="SHAPE_NOT_DECLARED")
    if shape > ceilings["MAX_VECTOR_LENGTH"]: raise Refusal(str(shape), code="CEILING_VECTOR_LENGTH_EXCEEDED")
    if len(a) != shape or len(b) != shape: raise Refusal("%d/%d vs %d" % (len(a), len(b), shape), code="SHAPE_MISMATCH")
    return tuple(scalar(op, x, y) for x, y in zip(a, b))
def matrix_elementwise(op, a, b, shape, ceilings):
    if not (isinstance(shape, tuple) and len(shape) == 2 and all(isinstance(s, int) and not isinstance(s, bool) and s >= 0 for s in shape)):
        raise Refusal(repr(shape), code="SHAPE_NOT_DECLARED")
    r, c = shape
    if r > ceilings["MAX_MATRIX_ROWS"]: raise Refusal(str(r), code="CEILING_MATRIX_ROWS_EXCEEDED")
    if c > ceilings["MAX_MATRIX_COLS"]: raise Refusal(str(c), code="CEILING_MATRIX_COLS_EXCEEDED")
    for m in (a, b):
        if len(m) != r or any(len(row) != c for row in m): raise Refusal("matrix shape", code="SHAPE_MISMATCH")
    return tuple(tuple(scalar(op, x, y) for x, y in zip(ra, rb)) for ra, rb in zip(a, b))

# --- reductions: ascending declared index order, sequential, no reassociation, no FMA ---------------------------------
def _check_len(vs, declared_length, ceilings):
    if not (isinstance(declared_length, int) and not isinstance(declared_length, bool) and declared_length >= 0): raise Refusal(repr(declared_length), code="LENGTH_NOT_DECLARED")
    if declared_length > ceilings["MAX_REDUCTION_LENGTH"]: raise Refusal(str(declared_length), code="CEILING_REDUCTION_LENGTH_EXCEEDED")
    if any(len(v) != declared_length for v in vs): raise Refusal("length", code="SHAPE_MISMATCH")
def fixed_sum(v, declared_length, ceilings):
    _check_len((v,), declared_length, ceilings)
    acc = 0.0                                                                # canonical +0
    for x in v: acc = _out(acc + _in(x))                                      # sequential ADD only
    return acc
def fixed_dot(a, b, declared_length, ceilings):
    _check_len((a, b), declared_length, ceilings)
    acc = 0.0
    for x, y in zip(a, b):
        p = _out(_in(x) * _in(y))                                             # the product is ROUNDED first (a separate binary64 operation) ...
        acc = _out(acc + p)                                                   # ... then added sequentially: never contracted into an FMA
    return acc
