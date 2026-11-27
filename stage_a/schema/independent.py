"""INDEPENDENT verifier-side Annex V1.2 hash composition.

Deliberately imports nothing from stage_a.schema.encoding/objects and uses no struct/dataclass machinery: integers are
written with int.to_bytes, objects are plain dicts, field order is its own table written from the Annex text.
Inputs are plain data: a Ref is (type_code:int, target_id:bytes, target_version:bytes, hash32|None); enums are
already-resolved UINT16 codes (code-table admission is D3 and is NOT decided here).
This is the same author as the producer side: independence is structural (no shared code), not a second human (Owner staffing)."""
import hashlib

def _n(v, width, lo, hi):
    if type(v) is not int or not lo <= v <= hi:
        raise ValueError("range")
    return v.to_bytes(width, "big", signed=lo < 0)
def _vid(s):
    b = s.encode("utf-8")
    if not 1 <= len(b) <= 128: raise ValueError("vid")
    return len(b).to_bytes(4, "big") + b
def _fix(b, n):
    if type(b) is not bytes or len(b) != n: raise ValueError("fixed")
    return b
def _ref(r):
    t, i, v, h = r
    out = _n(t, 2, 0, 65535) + len(i).to_bytes(4, "big") + i + len(v).to_bytes(4, "big") + v
    return out + (b"\x00" if h is None else b"\x01" + _fix(h, 32))
def _opt(x, f): return b"\x00" if x is None else b"\x01" + f(x)
def _lst(xs, f): return len(xs).to_bytes(4, "big") + b"".join(f(x) for x in xs)
def _u16(x): return _n(x, 2, 0, 65535)
def _u64(x): return _n(x, 8, 0, 2**64 - 1)
def _ts(x): return _n(x, 8, -2**63, 2**63 - 1)
def _bool(x):
    if x is not True and x is not False: raise ValueError("bool")
    return b"\x01" if x else b"\x00"
def _tagged(v):
    return b"\x01" + _u16(v[1]) if v[0] == "ENUM" else b"\x02" + _ref(v[1])
def _h(b): return hashlib.sha256(b).digest()

def row_hash(r):
    """r: dict with Annex §PENDING_ROW field names (lowercase)."""
    if (r["predecessor_row_hash"] is None) == (r["state_origin_ref"] is None): raise ValueError("origin")
    if (r["speculation_mode"] == 2) != (r["gate_dependency_hash"] is not None): raise ValueError("gate")
    if not r["input_refs_and_hashes"]: raise ValueError("inputs")
    b = (_fix(r["feature_id"], 16) + _vid(r["feature_version"]) + _fix(r["quant_manifest_hash"], 32) + _fix(r["instrument_id"], 16)
         + _fix(r["timeframe_id"], 16) + _vid(r["materialization_version"]) + _u64(r["step_index"]) + _ts(r["event_time"])
         + _vid(r["state_schema_version"]) + _vid(r["logical_encoding_version"]) + _vid(r["arithmetic_contract_version"])
         + len(r["state_tuple"]).to_bytes(4, "big") + r["state_tuple"] + _vid(r["published_projection_name"])
         + _fix(r["published_projection_bits"], 8) + _lst(r["input_refs_and_hashes"], lambda p: _ref(p[0]) + _fix(p[1], 32))
         + _opt(r["fit_generation_ref"], _ref) + _ref(r["step_class_ref"]) + _opt(r["predecessor_row_hash"], lambda x: _fix(x, 32))
         + _opt(r["state_origin_ref"], _ref) + _u16(r["speculation_mode"]) + _opt(r["gate_dependency_hash"], lambda x: _fix(x, 32))
         + _fix(r["materializer_implementation_id"], 16))
    return _h(b)

def transition_hash(c):
    if c["available_asof"] != c["canonical_accepted_at"]: raise ValueError("asof")
    return _h(_fix(c["row_content_hash"], 32) + _ref(c["verification_evidence_ref"]) + _u64(c["sifp_fencing_epoch"])
              + _fix(c["canonical_commit_point_id"], 16) + _ts(c["canonical_accepted_at"]) + _ts(c["available_asof"])
              + _opt(c["gate_dependency_transition_ref"], _ref) + _u16(c["currentness_state_at_acceptance"]) + _u16(c["status_event"]))

def status_event_hash(s):
    e = s["effective_from"]
    if e[0] == "STEP": eff = b"\x01" + _u64(e[1])
    elif e[0] == "INTERVAL" and e[2] > e[1]: eff = b"\x02" + _u64(e[1]) + _u64(e[2])
    else: raise ValueError("effective")
    return _h(_fix(s["status_event_id"], 16) + _vid(s["feature_version"]) + _fix(s["instrument_id"], 16) + _fix(s["timeframe_id"], 16)
              + _vid(s["materialization_version"]) + _u64(s["mv_status_sequence"]) + _u16(s["status_event_type"]) + eff
              + _tagged(s["reason_code"]) + _opt(s["predecessor_or_successor_mv_ref"], _ref) + _ts(s["available_asof"])
              + _ref(s["evidence_ref"]) + _u64(s["sifp_fencing_epoch"]) + _bool(s["correction_marked"]))

def delivered_hash(d):
    return _h(_fix(d["feature_id"], 16) + _vid(d["feature_version"]) + _fix(d["quant_manifest_hash"], 32) + _fix(d["instrument_id"], 16)
              + _fix(d["timeframe_id"], 16) + _vid(d["materialization_version"]) + _u64(d["step_index"]) + _ts(d["event_time"])
              + _vid(d["logical_encoding_version"]) + _vid(d["published_projection_name"]) + _fix(d["published_projection_bits"], 8)
              + _fix(d["published_projection_hash"], 32) + _opt(d["fit_generation_ref"], _ref) + _u16(d["data_vintage_mode"])
              + _ts(d["available_asof"]) + _u16(d["chain_status_at_bind"]) + _ref(d["source_or_causal_policy_ref"])
              + _ref(d["bound_health_resolution_ref"]) + _ts(d["bound_health_resolved_at"]) + _ref(d["canonical_transition_ref"])
              + _lst(d["omissions_exclusions_reason_codes"], _tagged))

def manifest_hash(m):
    """Independent MANIFEST_HASH. `m` is a plain dict; refs are (type, id, version, hash|None); keyed lists are lists of
    (name, ref) in ANY order (declaration order is non-authoritative); capabilities are dicts with program_ref,
    capability_class (resolved UINT16), opcode_set_used (ascending, unique, non-empty) and resource_ceiling_ref."""
    if m["shared_evaluator_operator_set_version"] != "SQE_OPSET_V1_1":
        raise ValueError("opset")
    sched = m["refit_mode_is_scheduled"]
    if sched != (m["refit_rule_ref"] is not None) or sched != (m["parameter_generation_source_ref"] is not None):
        raise ValueError("refit presence")
    def keyed(pairs):
        if not pairs: raise ValueError("empty")
        enc = sorted(((_vid(k), _vid(k) + _ref(r)) for k, r in pairs), key=lambda p: p[0])
        if len({k for k, _ in enc}) != len(enc): raise ValueError("dup")
        return _lst([e for _, e in enc], lambda b: b)
    if not m["program_capability_declarations"]: raise ValueError("empty")
    caps = []
    for c in m["program_capability_declarations"]:
        ops = list(c["opcode_set_used"])
        if not ops or ops != sorted(set(ops)): raise ValueError("opcodes")
        caps.append((_ref(c["program_ref"]), _ref(c["program_ref"]) + _u16(c["capability_class"])
                     + _lst(ops, _u16) + _ref(c["resource_ceiling_ref"])))
    caps.sort(key=lambda p: p[0])
    if len({k for k, _ in caps}) != len(caps): raise ValueError("dup")
    parts = [_vid(m["quant_manifest_schema_version"]), _fix(m["feature_id"], 16), _vid(m["feature_version"]),
             _vid(m["model_profile_id"]), _vid(m["model_profile_version"]), _vid(m["state_schema_version"]),
             _vid(m["parameter_schema_version"]), _vid(m["arithmetic_contract_version"]), _vid(m["logical_encoding_version"]),
             _vid(m["shared_evaluator_operator_set_version"]), _u16(m["refit_mode"]),
             _opt(m["refit_rule_ref"], _ref), _opt(m["parameter_generation_source_ref"], _ref),
             _ref(m["initialization_rule_set_ref"]), _ref(m["step_class_set_ref"]), _ref(m["step_classifier_ref"]),
             keyed(m["input_dependencies"]), keyed(m["transition_program_refs"]), keyed(m["projection_program_refs"]),
             keyed(m["invariant_program_refs"]),
             _ref(m["published_projection_set_ref"]), _ref(m["verification_rule_set_ref"]), _ref(m["golden_vector_set_ref"]),
             _ref(m["health_profile_ref"]), _lst_health(m["health_metric_program_refs"]),
             _lst([e for _, e in caps], lambda b: b), _ref(m["resource_ceiling_ref"]), _ref(m["data_vintage_policy_ref"])]
    return _h(b"".join(parts))

def _lst_health(pairs):
    # HEALTH_METRIC_PROGRAM_REFS may be empty in a manifest whose health profile declares no metrics; the producer allows it.
    enc = sorted(((_vid(k), _vid(k) + _ref(r)) for k, r in pairs), key=lambda p: p[0])
    if len({k for k, _ in enc}) != len(enc): raise ValueError("dup")
    return _lst([e for _, e in enc], lambda b: b)
