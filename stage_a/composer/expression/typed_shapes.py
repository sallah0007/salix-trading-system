"""Typed fixed-shape candidate operators (R46). SOURCE (read R46 via the Manager's quotation of, and R45 reads of, Parent V1.2 SQE_OPSET_V1_1 and Typed Annex V1.2 section III; cited by role):
 STATE SCHEMA component: COMPONENT_NAME, COMPONENT_TYPE in {BINARY64_SCALAR, FIXED_VECTOR_BINARY64, FIXED_MATRIX_BINARY64}, SHAPE_RANK, SHAPE_DIMENSIONS (per rank), PUBLISHED.
 OPSET: VECTOR_ELEMENTWISE_ADD/SUBTRACT/MULTIPLY/DIVIDE_GUARDED and MATRIX equivalents; shape STATICALLY declared; mismatch FAILS CLOSED. FIXED_SUM / FIXED_DOT: statically declared finite length, ascending
 index order; sum accumulator canonical +0 with sequential ADD only; dot = each product rounded FIRST then sequential ADD; no FMA / reassociation. NOT admitted: general matmul, transpose, inverse, solve, decomposition.
Scalar arithmetic is the SAME single-operation binary64 RNE rule as evaluator.py (canon/_fin reused, not re-derived).
NOT decided here (named residuals): the COMPONENT_TYPE<->SHAPE_RANK numeric pairing and any rank/flatten convention (this module takes the shape from the declared dims and requires the value's nesting to equal it; a
 vector value is a list of floats, a matrix a list of equal-length rows); numeric opcode codes; the program byte grammar and the manifest-DAG integration of these operators; the profile-owned ceiling VALUES (supplied by the caller);
 the STATE_TUPLE byte encoding. This module is NOT wired into manifest/evaluate(): vector/matrix nodes remain refused by schema.UNKNOWN_OPCODE until the grammar/manifest typing is supplied."""
import math
from ...errors import Refusal
from .evaluator import canon, _fin

TYPES = ("BINARY64_SCALAR", "FIXED_VECTOR_BINARY64", "FIXED_MATRIX_BINARY64")
def _int(v): return type(v) is int
def _f(x):
    if type(x) is not float or not math.isfinite(x): raise Refusal(repr(x), code="SHAPE_ELEMENT_NOT_FINITE_BINARY64")
    return canon(x)

def validate_state_schema(components, ceilings=None):
    """components: list of dicts {COMPONENT_NAME, COMPONENT_TYPE, SHAPE_RANK, SHAPE_DIMENSIONS, PUBLISHED[, INVARIANT_REF]}. Returns the tuple in schema order. Fails closed."""
    if not isinstance(components, list) or not components: raise Refusal("components", code="STATE_SCHEMA_COMPONENTS_REQUIRED")
    names, out = set(), []
    for c in components:
        if not isinstance(c, dict) or not {"COMPONENT_NAME", "COMPONENT_TYPE", "SHAPE_RANK", "SHAPE_DIMENSIONS", "PUBLISHED"} <= set(c) or not set(c) <= {"COMPONENT_NAME", "COMPONENT_TYPE", "SHAPE_RANK", "SHAPE_DIMENSIONS", "PUBLISHED", "INVARIANT_REF"}:
            raise Refusal("component", code="STATE_COMPONENT_FIELD_SET")
        n, t, r, d = c["COMPONENT_NAME"], c["COMPONENT_TYPE"], c["SHAPE_RANK"], c["SHAPE_DIMENSIONS"]
        if not (isinstance(n, str) and n) or n in names: raise Refusal(str(n), code="STATE_COMPONENT_NAME")
        if t not in TYPES: raise Refusal(str(t), code="STATE_COMPONENT_TYPE_NOT_ADMITTED")
        if not (_int(r) and 0 <= r <= 255) or not isinstance(d, list) or len(d) != r or not all(_int(x) and 1 <= x < 2 ** 32 for x in d): raise Refusal(n, code="STATE_SHAPE_DIMENSIONS_DO_NOT_MATCH_RANK")
        if not isinstance(c["PUBLISHED"], bool): raise Refusal(n, code="STATE_COMPONENT_PUBLISHED_NOT_BOOL")
        if t == "BINARY64_SCALAR" and d: raise Refusal(n, code="STATE_SCALAR_HAS_DIMENSIONS")
        if t == "FIXED_VECTOR_BINARY64" and len(d) != 1: raise Refusal(n, code="STATE_VECTOR_NEEDS_ONE_DIMENSION")       # candidate reading of the type name: see module residuals
        if t == "FIXED_MATRIX_BINARY64" and len(d) != 2: raise Refusal(n, code="STATE_MATRIX_NEEDS_TWO_DIMENSIONS")
        if ceilings is not None:
            if t == "FIXED_VECTOR_BINARY64" and d[0] > ceilings["MAX_VECTOR_LENGTH"]: raise Refusal(n, code="CEILING_VECTOR_LENGTH_EXCEEDED")
            if t == "FIXED_MATRIX_BINARY64" and (d[0] > ceilings["MAX_MATRIX_ROWS"] or d[1] > ceilings["MAX_MATRIX_COLS"]): raise Refusal(n, code="CEILING_MATRIX_SHAPE_EXCEEDED")
        names.add(n); cc = dict(c); cc["SHAPE_DIMENSIONS"] = list(d); out.append(cc)      # R53: detach the nested dims list from the caller's component dict
    return tuple(out)

class Typed:
    """A value with its STATICALLY declared type and dims. Construction validates the nesting and every element (finite binary64, -0 -> +0). The instance is IMMUTABLE (attribute assignment refused;
    data is a tuple / tuple of tuples) and every operation REVALIDATES shape, so a value cannot drift from its declared dimensions. Dimensions are strict UINT32-range ints (not bool, not float)."""
    __slots__ = ("kind", "dims", "data")
    def __init__(self, kind, dims, data):
        if kind not in TYPES: raise Refusal(str(kind), code="STATE_COMPONENT_TYPE_NOT_ADMITTED")
        dims = tuple(dims)
        if not all(type(d) is int and 1 <= d < 2 ** 32 for d in dims): raise Refusal(str(dims), code="SHAPE_DIMENSION_NOT_UINT32")
        if kind == "BINARY64_SCALAR":
            if dims: raise Refusal("dims", code="STATE_SCALAR_HAS_DIMENSIONS")
            data = _f(data)
        elif kind == "FIXED_VECTOR_BINARY64":
            if len(dims) != 1 or not isinstance(data, (list, tuple)) or len(data) != dims[0]: raise Refusal(str(dims), code="SHAPE_MISMATCH")
            data = tuple(_f(x) for x in data)
        else:
            if len(dims) != 2 or not isinstance(data, (list, tuple)) or len(data) != dims[0] or any(not isinstance(r, (list, tuple)) or len(r) != dims[1] for r in data): raise Refusal(str(dims), code="SHAPE_MISMATCH")
            data = tuple(tuple(_f(x) for x in r) for r in data)
        object.__setattr__(self, "kind", kind); object.__setattr__(self, "dims", dims); object.__setattr__(self, "data", data)
    def __setattr__(self, k, v): raise Refusal(k, code="TYPED_VALUE_IMMUTABLE")
    def __delattr__(self, k): raise Refusal(k, code="TYPED_VALUE_IMMUTABLE")

def _recheck(a):
    """invariant: the held data still has exactly the declared shape (defence against any bypass of immutability)."""
    if not isinstance(a, Typed): raise Refusal(type(a).__name__, code="SHAPE_MISMATCH")
    Typed(a.kind, a.dims, a.data)

def _same(a, b):
    _recheck(a) if isinstance(a, Typed) else None; _recheck(b) if isinstance(b, Typed) else None
    if not (isinstance(a, Typed) and isinstance(b, Typed)) or a.kind != b.kind or a.dims != b.dims: raise Refusal("%s%s vs %s%s" % (getattr(a, "kind", a), getattr(a, "dims", ""), getattr(b, "kind", b), getattr(b, "dims", "")), code="SHAPE_MISMATCH")

def _elem(op, x, y):
    if op == "add": return _fin(x + y)
    if op == "sub": return _fin(x - y)
    if op == "mul": return _fin(x * y)
    if op == "div":
        if y == 0.0: raise Refusal("zero denominator", code="DOMAIN_DIV_ZERO")
        return _fin(x / y)
    raise Refusal(op, code="UNKNOWN_OPCODE")

def elementwise(op, a, b):
    """VECTOR_/MATRIX_ELEMENTWISE_{ADD,SUBTRACT,MULTIPLY,DIVIDE_GUARDED}; scalars are NOT broadcast (shape mismatch fails closed). Ascending index order."""
    _same(a, b)
    if a.kind == "BINARY64_SCALAR": return Typed(a.kind, (), _elem(op, a.data, b.data))
    if a.kind == "FIXED_VECTOR_BINARY64": return Typed(a.kind, a.dims, [_elem(op, x, y) for x, y in zip(a.data, b.data)])
    return Typed(a.kind, a.dims, [[_elem(op, x, y) for x, y in zip(ra, rb)] for ra, rb in zip(a.data, b.data)])

def fixed_sum(v):
    """FIXED_SUM over a declared-length vector: accumulator canonical +0, sequential ADD in ascending index order only."""
    if not isinstance(v, Typed) or v.kind != "FIXED_VECTOR_BINARY64": raise Refusal("operand", code="SHAPE_MISMATCH")
    _recheck(v); s = 0.0
    for x in v.data: s = _fin(s + x)
    return Typed("BINARY64_SCALAR", (), s)

def fixed_dot(a, b):
    """FIXED_DOT: each ascending-index product is rounded FIRST (a separate binary64 MULTIPLY, never fused), then added sequentially from +0."""
    _same(a, b)
    if a.kind != "FIXED_VECTOR_BINARY64": raise Refusal("operand", code="SHAPE_MISMATCH")
    s = 0.0
    for x, y in zip(a.data, b.data):
        p = _fin(x * y); s = _fin(s + p)
    return Typed("BINARY64_SCALAR", (), s)

NOT_ADMITTED = frozenset({"matmul", "transpose", "inverse", "solve", "decompose"})
def refuse_not_admitted(name):
    if name in NOT_ADMITTED: raise Refusal(name, code="OPCODE_NOT_ADMITTED_SQE_OPSET_V1_1")
