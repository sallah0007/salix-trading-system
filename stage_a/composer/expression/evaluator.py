"""Generic evaluator. No branch depends on feature id/version/model name (TR-01; enforced by a static test).
Causality: the value at index t reads inputs at indices <= t only."""
import math, struct
from typing import Dict, List, Optional
from ...errors import Refusal
from .manifest import Manifest

def decode_const(hex16: str) -> float:
    v = struct.unpack(">d", bytes.fromhex(hex16))[0]
    if not math.isfinite(v):
        raise Refusal(hex16, code="NON_FINITE_CONST")
    return v

def encode_const(x: float) -> str:
    if type(x) is not float or not math.isfinite(x):
        raise Refusal(repr(x), code="NON_FINITE_CONST")
    return struct.pack(">d", x).hex()

def _fin(x):
    if x is not None and not math.isfinite(x):
        raise Refusal("overflow/non-finite result", code="NON_FINITE_RESULT")
    return x

def op_value(node, t, get):
    """Value of `node` at index t; get(node_id, idx) gives an already-computed value (None if undefined/out of range)."""
    op = node["op"]
    if op == "const":
        return decode_const(node["value"])
    a = [get(x, t) for x in node.get("args", [])]
    if op in ("add", "sub", "mul", "div", "min", "max", "neg", "abs", "sqrt", "log"):
        if any(v is None for v in a):
            return None
        if op == "add": return _fin(a[0] + a[1])
        if op == "sub": return _fin(a[0] - a[1])
        if op == "mul": return _fin(a[0] * a[1])
        if op == "div": return None if a[1] == 0.0 else _fin(a[0] / a[1])
        if op == "min": return a[0] if a[0] <= a[1] else a[1]
        if op == "max": return a[0] if a[0] >= a[1] else a[1]
        if op == "neg": return -a[0]
        if op == "abs": return abs(a[0])
        if op == "sqrt": return None if a[0] < 0.0 else math.sqrt(a[0])
        if op == "log": return None if a[0] <= 0.0 else math.log(a[0])
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
            s = _fin(s + v)
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
            vals[nid] = list(series[node["name"]])
            continue
        vals[nid] = [op_value(node, t, lambda k, i: vals[k][i]) for t in range(length)]
    return vals[m.data["output"]]
