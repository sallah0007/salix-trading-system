"""INDEPENDENT structural traversal, operator extraction and reference evaluation. Re-declares the opcode table and
the numeric spec from the written definition; shares no code with the composer evaluator."""
import math, operator, struct
from functools import reduce

# arity, windowed, capability  (re-declared, not imported)
_OPS = {
    "input": (0, False, "INPUT_SERIES"), "const": (0, False, "CONST_BINARY64"),
    "add": (2, False, "ARITH_BINARY64"), "sub": (2, False, "ARITH_BINARY64"), "mul": (2, False, "ARITH_BINARY64"),
    "div": (2, False, "ARITH_BINARY64"), "min": (2, False, "ARITH_BINARY64"), "max": (2, False, "ARITH_BINARY64"),
    "neg": (1, False, "ARITH_BINARY64"), "abs": (1, False, "ARITH_BINARY64"),
    "sqrt": (1, False, "ELEMENTARY_BINARY64"),
    "lag": (1, True, "WINDOW_LAG"), "rolling_sum": (1, True, "WINDOW_ROLLING"), "rolling_mean": (1, True, "WINDOW_ROLLING"),
}

def structure_violations(p):
    """Returns a list of violation codes (empty = structurally sound). Kahn ordering + reverse reachability."""
    v = []
    nodes = p["nodes"]
    ids = [n["id"] for n in nodes]
    if len(set(ids)) != len(ids):
        v.append("DUPLICATE_NODE_ID")
    by = {n["id"]: n for n in nodes}
    indeg = {i: 0 for i in by}
    children = {i: [] for i in by}
    used_inputs = set()
    for n in nodes:
        if n["op"] not in _OPS:
            v.append("UNKNOWN_OPCODE:%s" % n["op"]); continue
        arity, win, _ = _OPS[n["op"]]
        args = n.get("args", [])
        if len(args) != arity:
            v.append("ARITY:%s" % n["id"])
        for a in args:
            if a not in by:
                v.append("DANGLING:%s" % n["id"]); continue
            indeg[n["id"]] += 1
            children[a].append(n["id"])
        if win and not (isinstance(n.get("n"), int) and n["n"] >= 1):
            v.append("WINDOW:%s" % n["id"])
        if n["op"] == "input":
            used_inputs.add(n.get("name"))
    if used_inputs != set(p["inputs"]):
        v.append("INPUTS_NOT_EQUAL_USED")
    queue = sorted(i for i, d in indeg.items() if d == 0)
    seen = 0
    while queue:
        cur = queue.pop(0)
        seen += 1
        for c in sorted(children[cur]):
            indeg[c] -= 1
            if indeg[c] == 0:
                queue.append(c)
    if seen != len(by):
        v.append("CYCLE")
    if p["output"] not in by:
        v.append("OUTPUT_MISSING")
    else:
        parents = {i: [a for a in by[i].get("args", []) if a in by] for i in by}
        reach, frontier = {p["output"]}, [p["output"]]
        while frontier:
            x = frontier.pop()
            for a in parents[x]:
                if a not in reach:
                    reach.add(a); frontier.append(a)
        if reach != set(by):
            v.append("UNREACHABLE_NODE")
    return v

def extracted_ops(p):
    return sorted(set(n["op"] for n in p["nodes"]))

def extracted_caps(p):
    return sorted(set(_OPS[o][2] for o in extracted_ops(p)))

def _kahn(p):
    by = {n["id"]: n for n in p["nodes"]}
    indeg = {i: len(by[i].get("args", [])) for i in by}
    kids = {i: [] for i in by}
    for i in by:
        for a in by[i].get("args", []):
            kids[a].append(i)
    q = sorted(i for i, d in indeg.items() if d == 0)
    out = []
    while q:
        c = q.pop(0); out.append(c)
        for k in sorted(kids[c]):
            indeg[k] -= 1
            if indeg[k] == 0:
                q.append(k)
    return out, by

class RefEvalError(Exception):
    pass

def _z(x):
    """Signed-zero canonicalisation by arithmetic (-0.0 + 0.0 == +0.0 under round-to-nearest); independent of the composer's comparison form."""
    return None if x is None else x + 0.0

def _fin(x):
    if x is not None and not math.isfinite(x):
        raise RefEvalError("NON_FINITE")
    return _z(x)

def reference_evaluate(p, series):
    """Column-wise reference evaluator. Returns list of float|None."""
    n_rows = len(next(iter(series.values())))
    order, by = _kahn(p)
    col = {}
    for nid in order:
        nd = by[nid]; op = nd["op"]
        if op == "input":
            col[nid] = [_z(x) for x in series[nd["name"]]]
        elif op == "const":
            c = struct.unpack(">d", bytes.fromhex(nd["value"]))[0]
            if not math.isfinite(c):
                raise RefEvalError("NON_FINITE_CONST")
            col[nid] = [_z(c)] * n_rows
        elif op in ("lag",):
            src, k = col[nd["args"][0]], nd["n"]
            col[nid] = [None] * min(k, n_rows) + src[:max(n_rows - k, 0)]
        elif op in ("rolling_sum", "rolling_mean"):
            src, k = col[nd["args"][0]], nd["n"]
            res = []
            for t in range(n_rows):
                w = src[t - k + 1:t + 1] if t - k + 1 >= 0 else None
                if w is None or any(x is None for x in w):
                    res.append(None); continue
                s = reduce(lambda acc, x: _fin(acc + _z(x)), w, 0.0)
                res.append(s if op == "rolling_sum" else _fin(s / float(k)))
            col[nid] = res
        else:
            cols = [col[a] for a in nd["args"]]
            res = []
            for row in zip(*cols):
                if any(x is None for x in row):
                    res.append(None); continue
                row = tuple(_z(x) for x in row)
                if op == "add": r = _fin(row[0] + row[1])
                elif op == "sub": r = _fin(row[0] - row[1])
                elif op == "mul": r = _fin(row[0] * row[1])
                elif op == "div":
                    if row[1] == 0.0: raise RefEvalError("DOMAIN_FAILURE")
                    r = _fin(row[0] / row[1])
                elif op == "min": r = _fin(min(row[0], row[1]) if row[0] != row[1] else row[0])
                elif op == "max": r = _fin(max(row[0], row[1]) if row[0] != row[1] else row[0])
                elif op == "neg": r = _fin(-row[0])
                elif op == "abs": r = _fin(math.fabs(row[0]))
                elif op == "sqrt":
                    if row[0] < 0.0: raise RefEvalError("DOMAIN_FAILURE")
                    r = _fin(math.sqrt(row[0]))
                else: raise RefEvalError("UNKNOWN_OPCODE")
                res.append(r)
            col[nid] = res
    return col[p["output"]]

def bits(x):
    """Bit-exact comparable form of a value."""
    return None if x is None else struct.pack(">d", x).hex()

def make_probe(inputs, length=48):
    """Verifier-authored deterministic probe series (edge cases included). Values are exact binary64 floats."""
    series = {}
    for idx, name in enumerate(sorted(inputs)):
        state = (0x9E3779B97F4A7C15 ^ (idx + 1) * 0x100000001B3) & 0xFFFFFFFFFFFFFFFF
        col = []
        for t in range(length):
            state = (state * 6364136223846793005 + 1442695040888963407) & 0xFFFFFFFFFFFFFFFF
            x = ((state >> 11) / float(1 << 53)) * 10.0 - 5.0
            if t % 11 == 3: x = 0.0
            if t % 13 == 5: x = -0.0
            if t % 17 == 7: x = None
            col.append(x)
        series[name] = col
    return series
