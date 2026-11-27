"""Manifest schema SALIX_EXPR_MANIFEST_V1 (implementation-defined; source admission OPEN). Strict: exact field
sets, no unknown keys, no duplicates, acyclic, every node reachable from the output, declared inputs == used inputs."""
import re
from ...errors import Refusal
from ...identifiers import check_token
from .opcodes import OPCODES, EMULATED, NOT_ADMITTED_PROFILE_ONLY

SCHEMA_ID = "SALIX_EXPR_MANIFEST_V1"
TOP_KEYS = {"schema", "feature_id", "feature_version", "instrument", "timeframe", "inputs", "nodes", "output",
            "fit_refs", "declared_opcodes", "declared_capabilities"}
_HEX16 = re.compile(r"^[0-9a-f]{16}$")
_HEX64 = re.compile(r"^[0-9a-f]{64}$")
MAX_NODES = 512
MAX_WINDOW = 10000

def _req(cond, code, detail=""):
    if not cond:
        raise Refusal(detail, code=code)

def validate_manifest(m) -> dict:
    """Returns a normalised deep copy (sorted where order is semantically irrelevant). Raises Refusal."""
    _req(isinstance(m, dict), "MANIFEST_NOT_OBJECT")
    _req(set(m) == TOP_KEYS, "MANIFEST_FIELD_SET", "missing=%s extra=%s" % (sorted(TOP_KEYS - set(m)), sorted(set(m) - TOP_KEYS)))
    _req(m["schema"] == SCHEMA_ID, "MANIFEST_SCHEMA_ID", str(m["schema"]))
    for k in ("feature_id", "feature_version", "instrument", "timeframe"):
        check_token(m[k], k)
    inputs = m["inputs"]
    _req(isinstance(inputs, list) and inputs, "INPUTS_REQUIRED")
    for i in inputs:
        check_token(i, "input")
    _req(len(set(inputs)) == len(inputs), "DUPLICATE_INPUT")
    nodes = m["nodes"]
    _req(isinstance(nodes, list) and 0 < len(nodes) <= MAX_NODES, "NODE_COUNT")
    by_id = {}
    used_inputs = set()
    for n in nodes:
        _req(isinstance(n, dict) and "id" in n and "op" in n, "NODE_SHAPE")
        nid, op = check_token(n["id"], "node id"), n["op"]
        _req(nid not in by_id, "DUPLICATE_NODE_ID", nid)
        _req(op not in EMULATED, "EMULATED_OPCODE_REFUSED", op)
        _req(op not in NOT_ADMITTED_PROFILE_ONLY, "OPCODE_NOT_ADMITTED_SQE_OPSET_V1_1", str(op))
        _req(isinstance(op, str) and op in OPCODES, "UNKNOWN_OPCODE", str(op))
        spec = OPCODES[op]
        allowed = {"id", "op"}
        if spec.arity:
            allowed.add("args")
        if op == "const":
            allowed.add("value")
        if op == "input":
            allowed.add("name")
        if spec.windowed:
            allowed.add("n")
        _req(set(n) == allowed, "NODE_FIELD_SET", "%s %s" % (nid, sorted(set(n) ^ allowed)))
        if spec.arity:
            _req(isinstance(n["args"], list) and len(n["args"]) == spec.arity, "ARITY", nid)
            for a in n["args"]:
                check_token(a, "arg")
        if op == "const":
            _req(isinstance(n["value"], str) and _HEX16.match(n["value"]), "CONST_NOT_BINARY64_HEX", nid)
        if op == "input":
            _req(n["name"] in inputs, "UNDECLARED_INPUT", "%s uses %s" % (nid, n["name"]))
            used_inputs.add(n["name"])
        if spec.windowed:
            w = n["n"]
            _req(isinstance(w, int) and not isinstance(w, bool) and 1 <= w <= MAX_WINDOW, "WINDOW_PARAM", nid)
        by_id[nid] = n
    _req(used_inputs == set(inputs), "DECLARED_INPUTS_NOT_EQUAL_USED")
    for n in nodes:
        for a in n.get("args", []):
            _req(a in by_id, "DANGLING_ARG", "%s -> %s" % (n["id"], a))
    _req(m["output"] in by_id, "OUTPUT_NOT_A_NODE")
    # acyclic + reachability (iterative DFS)
    state, reach, stack = {}, set(), [(m["output"], False)]
    while stack:
        nid, done = stack.pop()
        if done:
            state[nid] = 2
            continue
        if state.get(nid) == 2:
            continue
        _req(state.get(nid) != 1, "CYCLE", nid)
        state[nid] = 1
        reach.add(nid)
        stack.append((nid, True))
        for a in by_id[nid].get("args", []):
            if state.get(a) == 1:
                raise Refusal(a, code="CYCLE")
            if state.get(a) != 2:
                stack.append((a, False))
    _req(reach == set(by_id), "UNREACHABLE_NODE", str(sorted(set(by_id) - reach)))
    fr = m["fit_refs"]
    _req(isinstance(fr, list), "FIT_REFS_SHAPE")
    gens = set()
    for f in fr:
        _req(isinstance(f, dict) and set(f) == {"generation", "ref_hash"}, "FIT_REF_FIELD_SET")
        _req(isinstance(f["generation"], int) and not isinstance(f["generation"], bool) and f["generation"] >= 1, "FIT_REF_GENERATION")
        _req(isinstance(f["ref_hash"], str) and _HEX64.match(f["ref_hash"]), "FIT_REF_HASH")
        _req(f["generation"] not in gens, "DUPLICATE_FIT_GENERATION")
        gens.add(f["generation"])
    for k in ("declared_opcodes", "declared_capabilities"):
        _req(isinstance(m[k], list) and all(isinstance(x, str) for x in m[k]), "DECLARATION_SHAPE", k)
        _req(len(set(m[k])) == len(m[k]), "DUPLICATE_DECLARATION", k)
    return {
        "schema": m["schema"], "feature_id": m["feature_id"], "feature_version": m["feature_version"],
        "instrument": m["instrument"], "timeframe": m["timeframe"],
        "inputs": sorted(inputs),
        "nodes": sorted(({k: (list(v) if isinstance(v, list) else v) for k, v in n.items()} for n in nodes),
                        key=lambda x: x["id"]),
        "output": m["output"],
        "fit_refs": sorted(({"generation": f["generation"], "ref_hash": f["ref_hash"]} for f in fr),
                           key=lambda x: x["generation"]),
        "declared_opcodes": sorted(m["declared_opcodes"]),
        "declared_capabilities": sorted(m["declared_capabilities"]),
    }
