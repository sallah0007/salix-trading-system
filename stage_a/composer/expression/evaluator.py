"""Generic evaluator. No branch depends on feature id/version/model name (TR-01; enforced by a static test).
Causality: the value at index t reads inputs at indices <= t only.

ARITHMETIC SOURCE (R11; cited by ID/lines, not copied): Stateful Quantitative Feature Contract V1.2 (Drive 1i5P8zxQmvBDKz397BxIUKM8AnBY00-ItzLMOjNGOkRM),
readable lines 116-204, controlling overlay SQE_OPSET_V1_1; Typed Schema Annex V1.2 (Drive 13PE_pli3ZlFjjPdhHtWtLyyH2XdAv8XGA4FN0KGcIlA), lines 84-121.
Implemented here: binary64, round-to-nearest-even (Python float ops are single IEEE operations: no FMA, no reassociation, no FTZ/DAZ);
finite inputs and finite results or fail closed; signed zero canonicalised to +0 at operator input and output boundaries; subnormals preserved;
DIVIDE_GUARDED = zero denominator (after canonicalisation) is a DOMAIN FAILURE (refusal), SQRT_GUARDED = negative input is a DOMAIN FAILURE;
sequential ascending accumulation from +0 for rolling_sum (the FIXED_SUM rule). LOG/EXP/POW/transcendentals are NOT admitted (see opcodes.py).
UNDEFINED (None) is retained ONLY as missing-input / warm-up propagation (lag, short window, missing input). That propagation is this repository's
prototype semantics and is SOURCE-UNBOUND (SQE_OPSET_V1_1 does not define missing inputs); it must not be read as an arithmetic-domain result."""
import math, struct
from typing import Dict, List, Optional
from ...errors import Refusal
from .manifest import Manifest

def canon(x):
    """Signed-zero canonicalisation: -0.0 -> +0.0 (None passes through)."""
    return 0.0 if x is not None and x == 0.0 else x

def decode_const(hex16: str) -> float:
    v = struct.unpack(">d", bytes.fromhex(hex16))[0]
    if not math.isfinite(v):
        raise Refusal(hex16, code="NON_FINITE_CONST")
    return canon(v)

def encode_const(x: float) -> str:
    if type(x) is not float or not math.isfinite(x):
        raise Refusal(repr(x), code="NON_FINITE_CONST")
    return struct.pack(">d", x).hex()

def _fin(x):
    if x is not None and not math.isfinite(x):
        raise Refusal("overflow/non-finite result", code="NON_FINITE_RESULT")
    return canon(x)

def op_value(node, t, get):
    """Value of `node` at index t; get(node_id, idx) gives an already-computed value (None if undefined/out of range)."""
    op = node["op"]
    if op == "const":
        return decode_const(node["value"])
    a = [canon(get(x, t)) for x in node.get("args", [])]
    if op in ("add", "sub", "mul", "div", "min", "max", "neg", "abs", "sqrt"):
        if any(v is None for v in a):
            return None                                   # missing-input propagation (source-unbound)
        if op == "add": return _fin(a[0] + a[1])
        if op == "sub": return _fin(a[0] - a[1])
        if op == "mul": return _fin(a[0] * a[1])
        if op == "div":
            if a[1] == 0.0: raise Refusal("zero denominator", code="DOMAIN_DIV_ZERO")
            return _fin(a[0] / a[1])
        if op == "min": return _fin(a[0] if a[0] <= a[1] else a[1])
        if op == "max": return _fin(a[0] if a[0] >= a[1] else a[1])
        if op == "neg": return _fin(-a[0])
        if op == "abs": return _fin(abs(a[0]))
        if op == "sqrt":
            if a[0] < 0.0: raise Refusal("negative sqrt input", code="DOMAIN_SQRT_NEGATIVE")
            return _fin(math.sqrt(a[0]))
    src = node["args"][0]
    n = node["n"]
    if op == "lag":
        return get(src, t - n) if t - n >= 0 else None
    if op in ("rolling_sum", "rolling_mean"):
        if t - n + 1 < 0:
            return None
        s = 0.0
        for i in range(t - n + 1, t + 1):
            v = get(src, i)
            if v is None:
                return None
            s = _fin(s + canon(v))
        return s if op == "rolling_sum" else _fin(s / float(n))
    raise Refusal(op, code="UNKNOWN_OPCODE")   # unreachable for validated manifests

def check_series(m: Manifest, series: Dict[str, List[Optional[float]]]):
    if set(series) != set(m.data["inputs"]):
        raise Refusal("series=%s inputs=%s" % (sorted(series), m.data["inputs"]), code="INPUT_SET_MISMATCH")
    lens = {len(v) for v in series.values()}
    if len(lens) != 1:
        raise Refusal(str(lens), code="INPUT_LENGTH_MISMATCH")
    for k, v in series.items():
        for x in v:
            if x is not None and (type(x) is not float or not math.isfinite(x)):
                raise Refusal("%s: %r" % (k, x), code="INPUT_NOT_FINITE_BINARY64")
    return lens.pop()

def topo_order(m: Manifest):
    by_id = {n["id"]: n for n in m.data["nodes"]}
    order, seen, stack = [], set(), [(m.data["output"], False)]
    while stack:
        nid, done = stack.pop()
        if done:
            order.append(nid); continue
        if nid in seen:
            continue
        seen.add(nid)
        stack.append((nid, True))
        for a in by_id[nid].get("args", []):
            if a not in seen:
                stack.append((a, False))
    return order

def evaluate(m: Manifest, series) -> List[Optional[float]]:
    length = check_series(m, series)
    by_id = {n["id"]: n for n in m.data["nodes"]}
    vals: Dict[str, List[Optional[float]]] = {}
    for nid in topo_order(m):
        node = by_id[nid]
        if node["op"] == "input":
            vals[nid] = [canon(x) for x in series[node["name"]]]
            continue
        vals[nid] = [op_value(node, t, lambda k, i: vals[k][i]) for t in range(length)]
    return vals[m.data["output"]]
