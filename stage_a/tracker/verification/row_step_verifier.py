"""R53 independent verification of ONE PendingRow step: is the proposed full state tuple the DECLARED legal successor of the exact predecessor tuple under the exact inputs?
Producer/independent byte-hash equality alone does not show that; this re-derives the successor through SUPPLIED independent ports and compares bytes.
Imports only stdlib and this verifier's own modules. It shares NO code with tracker/materialization/state_rows (own shape/finite checks, own projection rule).
SUPPLIED (held when unbound; nothing defaulted or invented): `reference_step(prior_values|None, inputs)` = the independent reference implementation of the profile's declared program
(profile math is source-owned, so tests use UNADMITTED SIM instances); `decode`/`encode` = the STATE_TUPLE codec (D13 bytes unadmitted); `resolve_inputs(declared)` re-reads the actual
inputs as {"declared": [(ref, hash, value), ...]} (None => INSUFFICIENT_EVIDENCE, never PASS) and `input_symbols` = the SUPPLIED symbol -> declared-input-index mapping from which the evaluation values are derived (None = held = INSUFFICIENT_EVIDENCE; never guessed); `recompute_row_hash(row)` = the independent row hash. LIMIT: this layer cannot recompute an input VALUE's hash (the input-hash rule is
not defined here), so it binds inputs by the declared (ref, hash) pairs the resolver echoes, and states that limit in the result subject."""
import hashlib, math, struct
from .verification_result import _issue_result, PASS, FAIL, INSUFFICIENT_EVIDENCE

SCOPE_ROW_STEP = "COMPONENT_ROW_STEP_V1"
ROW_STEP_PROFILE = frozenset(("schema_well_formed", "row_hash_recomputed", "predecessor_linkage", "predecessor_state_canonical", "inputs_reread_and_bound",
                              "successor_state_equals_reference", "projection_equals_reference", "schema_identity_registry_bound", "invariants_evaluated"))
HELD_CHECKS = frozenset(("schema_identity_registry_bound", "invariants_evaluated"))      # a False here means the evidence is UNAVAILABLE (INSUFFICIENT_EVIDENCE), not that a rule failed
INPUT_VALUE_HASH_LIMIT = "INPUT_VALUE_HASH_RULE_NOT_DEFINED_BINDING_BY_DECLARED_REF_HASH_ONLY"
def _snap(x):
    """Own deep snapshot of plain data (dict/list/tuple/str/int/float/bool/bytes/None); anything else is carried by reference (rows are frozen; refs are frozen)."""
    if isinstance(x, dict): return {k: _snap(v) for k, v in x.items()}
    if isinstance(x, list): return [_snap(v) for v in x]
    if isinstance(x, tuple): return tuple(_snap(v) for v in x)
    return x
_REQ = {"COMPONENT_NAME", "COMPONENT_TYPE", "SHAPE_RANK", "SHAPE_DIMENSIONS", "PUBLISHED"}
_DIMS = {"BINARY64_SCALAR": 0, "FIXED_VECTOR_BINARY64": 1, "FIXED_MATRIX_BINARY64": 2}

def _f(x):
    if type(x) is not float or not math.isfinite(x): raise ValueError("non-finite or non-float element")
    return 0.0 if x == 0.0 else x
def _shape(c, v):
    t, d = c["COMPONENT_TYPE"], list(c["SHAPE_DIMENSIONS"])
    if t == "BINARY64_SCALAR": return _f(v)
    if t == "FIXED_VECTOR_BINARY64":
        if not isinstance(v, (list, tuple)) or len(v) != d[0]: raise ValueError("vector shape")
        return tuple(_f(x) for x in v)
    if not isinstance(v, (list, tuple)) or len(v) != d[0] or any(not isinstance(r, (list, tuple)) or len(r) != d[1] for r in v): raise ValueError("matrix shape")
    return tuple(tuple(_f(x) for x in r) for r in v)
def _schema_ok(schema):
    if not isinstance(schema, (list, tuple)) or not schema: return False
    names = set()
    for c in schema:
        try:
            if not isinstance(c, dict) or not _REQ <= set(c) or not set(c) <= _REQ | {"INVARIANT_REF"}: return False          # SHAPE_RANK is MANDATORY (Annex STATE_COMPONENTS); unknown fields refused
            n, t, d, rk = c["COMPONENT_NAME"], c["COMPONENT_TYPE"], c["SHAPE_DIMENSIONS"], c["SHAPE_RANK"]
            if type(rk) is not int or not 0 <= rk <= 255 or t not in _DIMS or rk != _DIMS[t]: return False                  # rank: integer (not bool), coherent with the component type
            if not (isinstance(n, str) and n) or n in names or t not in _DIMS or not isinstance(c["PUBLISHED"], bool): return False
            if not isinstance(d, (list, tuple)) or len(d) != rk or any(type(x) is not int or x < 1 or x >= 2 ** 32 for x in d): return False
            names.add(n)
        except Exception: return False
    return True
def _state(schema, values):
    if not isinstance(values, dict) or set(values) != {c["COMPONENT_NAME"] for c in schema}: raise ValueError("state name set")
    return {c["COMPONENT_NAME"]: _shape(c, values[c["COMPONENT_NAME"]]) for c in schema}
def _ordered(schema, st): return {c["COMPONENT_NAME"]: st[c["COMPONENT_NAME"]] for c in schema}

def _norm(x):
    if isinstance(x, dict): return {k: _norm(v) for k, v in x.items()}
    if isinstance(x, (list, tuple)): return [_norm(v) for v in x]
    return x
_IDENT = ("feature_id", "feature_version", "quant_manifest_hash", "instrument_id", "timeframe_id", "materialization_version", "state_schema_version",
          "logical_encoding_version", "arithmetic_contract_version")

def verify_row_step(*, row, predecessor, schema, reference_step, decode, encode, resolve_inputs, input_symbols, recompute_row_hash, expect_row_hash, schema_registry=None, invariant_resolver=None):
    schema = _snap(schema); input_symbols = _snap(input_symbols)      # R53: snapshot what is validated; a supplied port can never change it afterwards
    checks, reasons = [], []
    subject = {"row_content_hash": str(expect_row_hash), "state_tuple_sha256": hashlib.sha256(getattr(row, "state_tuple", b"") if isinstance(getattr(row, "state_tuple", b""), bytes) else b"").hexdigest(),
               "predecessor_row_hash": "" if getattr(row, "predecessor_row_hash", None) is None else row.predecessor_row_hash.hex(), "input_binding_limit": INPUT_VALUE_HASH_LIMIT}
    def chk(name, ok, why=""):
        checks.append((name, bool(ok)))
        if not ok: reasons.append("%s%s" % (name, (":" + why) if why else ""))
        return bool(ok)
    held = set()
    def done(status):
        if status == PASS and held: status = INSUFFICIENT_EVIDENCE            # an unavailable binding/stage is never an automatic satisfaction
        return _issue_result(status, SCOPE_ROW_STEP, subject, checks, reasons)
    def pad(): [checks.append((n, False)) for n in sorted(ROW_STEP_PROFILE) if n not in dict(checks)]
    if not chk("schema_well_formed", _schema_ok(schema)): pad(); return done(FAIL)
    # the declared schema must be the one the governed registry reads back for THIS row's state_schema_version (not a caller's version string)
    reg_ok = False
    if schema_registry is None: subject["schema_identity"] = "UNBOUND_HELD"; held.add("schema_identity_registry_bound")
    else:
        try: got = schema_registry(row.state_schema_version)
        except Exception as e: got = False; reasons.append("schema_registry:%s" % type(e).__name__)
        if got is None: subject["schema_identity"] = "NOT_REGISTERED_HELD"; held.add("schema_identity_registry_bound")        # nothing to compare against: unavailable, not a failed rule
        elif got is False: subject["schema_identity"] = "REGISTRY_READBACK_FAILED"
        else: reg_ok = _norm(got) == _norm(schema); subject["schema_identity"] = "REGISTRY_BOUND" if reg_ok else "REGISTRY_MISMATCH"
    chk("schema_identity_registry_bound", reg_ok)
    try: rh = recompute_row_hash(row)
    except Exception as e: rh = None; reasons.append("row_hash_port:%s" % type(e).__name__)
    if not chk("row_hash_recomputed", rh == expect_row_hash): pad(); return done(FAIL)
    ok = (predecessor is None) == (row.predecessor_row_hash is None) and (predecessor is None) != (row.state_origin_ref is None)
    prior = None
    if ok and predecessor is not None:
        try: ok = recompute_row_hash(predecessor) == row.predecessor_row_hash.hex() and row.step_index == predecessor.step_index + 1 and all(getattr(row, k) == getattr(predecessor, k) for k in _IDENT)
        except Exception: ok = False
    chk("predecessor_linkage", ok)
    pc = True
    if predecessor is not None and ok:
        try:
            prior = _state(schema, decode(predecessor.state_tuple)); pc = encode(_ordered(schema, prior)) == predecessor.state_tuple
        except Exception as e: pc = False; reasons.append("predecessor_decode:%s" % type(e).__name__)
    chk("predecessor_state_canonical", pc and ok)
    try: res = resolve_inputs(tuple(row.input_refs_and_hashes))
    except Exception as e: res = None; reasons.append("input_port:%s" % type(e).__name__)
    if res is None:
        chk("inputs_reread_and_bound", False, "inputs could not be re-read"); pad(); return done(INSUFFICIENT_EVIDENCE)
    vals = None
    try:
        decl = _snap(list(res["declared"]))
        bound = tuple((r, h) for r, h, _ in decl) == tuple(row.input_refs_and_hashes)
        if input_symbols is None: bound = False; reasons.append("input_symbol_mapping_not_supplied_held")
        elif bound:                                              # evaluation values are DERIVED from the bound re-read payloads through the SUPPLIED symbol -> declared-input mapping; no second value carrier exists
            if not isinstance(input_symbols, dict) or not input_symbols or any(not isinstance(k, str) or type(i) is not int or not 0 <= i < len(decl) for k, i in input_symbols.items()): bound = False; reasons.append("input_symbol_mapping_invalid")
            else: vals = {k: decl[i][2] for k, i in input_symbols.items()}
    except Exception: bound = False
    if input_symbols is None and res is not None:
        chk("inputs_reread_and_bound", False, "symbol mapping held"); pad(); return done(INSUFFICIENT_EVIDENCE)
    chk("inputs_reread_and_bound", bound and vals is not None)
    exp, ok_state, ok_proj = None, False, False
    if bound and vals is not None and pc and ok:
        try:
            exp = _state(schema, reference_step(None if prior is None else _snap(prior), _snap(vals)))
            ok_state = encode(_ordered(schema, exp)) == row.state_tuple
            pub = [c for c in schema if c["PUBLISHED"]]
            ok_proj = len(pub) == 1 and pub[0]["COMPONENT_TYPE"] == "BINARY64_SCALAR" and row.published_projection_name == pub[0]["COMPONENT_NAME"] and row.published_projection_bits == struct.pack(">d", exp[pub[0]["COMPONENT_NAME"]])
        except Exception as e: reasons.append("reference_step:%s" % type(e).__name__)
    chk("successor_state_equals_reference", ok_state); chk("projection_equals_reference", ok_proj)
    # declared INVARIANT checks (Parent generic runtime: after independent verification, before canonical acceptance). An applicable declared rule that cannot be resolved is HELD, never satisfied.
    refs = []
    for c in schema:
        r = c.get("INVARIANT_REF")
        if r is not None and r not in refs: refs.append(r)
    inv_ok = True
    if not refs: subject["invariants"] = "NONE_DECLARED"
    elif exp is None: inv_ok = False; subject["invariants"] = "NOT_EVALUATED_NO_VERIFIED_STATE"
    else:
        hashes = []
        for r in refs:
            try: got = None if invariant_resolver is None else invariant_resolver(r)
            except Exception as e: got = None; reasons.append("invariant_resolver:%s" % type(e).__name__)
            if got is None: inv_ok = False; held.add("invariants_evaluated"); subject["invariants"] = "UNRESOLVED_HELD"; break
            ph, prog = got
            if getattr(r, "target_hash", None) not in (None, ph): inv_ok = False; subject["invariants"] = "PROGRAM_HASH_MISMATCH"; reasons.append("invariant_program_hash_mismatch"); break
            try: v = prog(_snap(exp), None if prior is None else _snap(prior), _snap(vals))
            except Exception as e: v = None; reasons.append("invariant_program:%s" % type(e).__name__)
            if v is not True: inv_ok = False; subject["invariants"] = "RULE_FAILED" if v is False else "RULE_NOT_BOOLEAN"; break
            hashes.append(ph.hex() if isinstance(ph, bytes) else str(ph))
        else: subject["invariants"] = "EVALUATED_PASS"; subject["invariant_program_hashes"] = ",".join(hashes)
    chk("invariants_evaluated", inv_ok)
    if held: pad_fail = [n for n, v in checks if not v and n not in held]; return done(FAIL if pad_fail else INSUFFICIENT_EVIDENCE)
    return done(PASS if all(v for _, v in checks) and ROW_STEP_PROFILE <= set(dict(checks)) else FAIL)
