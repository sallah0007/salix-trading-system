"""Independent verification of a materialization record against the bytes actually stored.
Imports only stdlib and this verifier's own independent modules. A static test asserts that."""
from .independent_encoding import enc_bytes, parse
from .independent_hashing import manifest_digest, graph_digest, program_digest, materialization_digest
from .independent_traversal import (structure_violations, extracted_ops, extracted_caps, reference_evaluate,
                                    RefEvalError, bits, make_probe)
from .verification_result import issue_result, PASS, FAIL, INSUFFICIENT_EVIDENCE, SCOPE_MATERIALIZATION

_REC_KEYS = {"feature_key", "feature_version", "instrument", "timeframe", "object_key", "manifest_hash",
             "graph_hash", "program_hash", "byte_length", "probe_batch", "probe_incremental", "materialization_hash"}

def probe_for(manifest_bytes: bytes):
    """The probe the materializer must run. Authored here, derived only from the stored manifest bytes."""
    p = parse(manifest_bytes)
    return make_probe(p["inputs"])

def verify_materialization(*, store_get, record: dict, declared: dict, expect_scope_key: str):
    """store_get(key)->bytes|None.  declared = hashes the producer (Composer) declared for the same attempt.
    expect_scope_key = 'INSTRUMENT/TIMEFRAME/FEATURE_ID/VERSION' the verifier was asked about."""
    checks, reasons = [], []
    def chk(name, ok, why=""):
        checks.append((name, bool(ok)))
        if not ok:
            reasons.append("%s%s" % (name, (":" + why) if why else ""))
        return ok
    subject = {"expect_scope_key": expect_scope_key, "record_manifest_hash": str(record.get("manifest_hash"))}

    if not chk("record_field_set", isinstance(record, dict) and set(record) == _REC_KEYS):
        return issue_result(FAIL, SCOPE_MATERIALIZATION, subject, checks, reasons)
    chk("materialization_hash_recomputed", materialization_digest(record, enc_bytes) == record["materialization_hash"])      # a free-form hash label is never verified identity
    raw = store_get(record["object_key"])
    if not chk("artifact_present", raw is not None):
        return issue_result(INSUFFICIENT_EVIDENCE, SCOPE_MATERIALIZATION, subject, checks, reasons)
    chk("object_key_is_content_address", record["object_key"] == "artifact/" + record["manifest_hash"])
    chk("byte_length", len(raw) == record["byte_length"])
    try:
        p = parse(raw)
    except Exception as e:
        chk("artifact_parses", False, str(e))
        return issue_result(FAIL, SCOPE_MATERIALIZATION, subject, checks, reasons)
    top = {"schema", "feature_id", "feature_version", "instrument", "timeframe", "inputs", "nodes", "output",
           "fit_refs", "declared_opcodes", "declared_capabilities"}
    if not chk("manifest_field_set", isinstance(p, dict) and set(p) == top):
        return issue_result(FAIL, SCOPE_MATERIALIZATION, subject, checks, reasons)
    chk("artifact_is_canonical_bytes", enc_bytes(p) == raw)
    chk("manifest_hash_recomputed", manifest_digest(raw) == record["manifest_hash"])
    chk("graph_hash_recomputed", graph_digest(p, enc_bytes) == record["graph_hash"])
    chk("program_hash_recomputed", program_digest(p, enc_bytes) == record["program_hash"])
    chk("declared_manifest_hash", declared.get("manifest_hash") == manifest_digest(raw))
    chk("declared_graph_hash", declared.get("graph_hash") == graph_digest(p, enc_bytes))
    chk("declared_program_hash", declared.get("program_hash") == program_digest(p, enc_bytes))
    key = "%s/%s/%s/%s" % (p["instrument"], p["timeframe"], p["feature_id"], p["feature_version"])
    chk("identity_binding_artifact_vs_request", key == expect_scope_key, key)
    chk("identity_binding_record_vs_request",
        "%s/%s/%s/%s" % (record["instrument"], record["timeframe"], record["feature_key"].split("/")[-2], record["feature_version"]) == expect_scope_key
        and record["feature_key"] == expect_scope_key)
    sv = structure_violations(p)
    chk("structure_sound", not sv, ",".join(sv))
    if sv:
        return issue_result(FAIL, SCOPE_MATERIALIZATION, subject, checks, reasons)
    chk("opcode_declaration_equals_extracted", p["declared_opcodes"] == extracted_ops(p))
    chk("capability_declaration_equals_extracted", p["declared_capabilities"] == extracted_caps(p))
    # numeric equivalence on the verifier's own probe, bit-exact, for both materializer paths
    probe = probe_for(raw)
    try:
        ref = [bits(x) for x in reference_evaluate(p, probe)]
    except RefEvalError as e:
        ref = {"error": str(e)}
    for name in ("probe_batch", "probe_incremental"):
        got = record[name]
        if isinstance(ref, dict):
            chk("equivalence_" + name, got == ref, "reference refused; materializer=%r" % (got,))
        else:
            chk("equivalence_" + name, isinstance(got, list) and got == ref)
    status = PASS if all(ok for _, ok in checks) else FAIL
    subject["graph_hash"] = record["graph_hash"]
    subject["program_hash"] = record["program_hash"]
    subject["materialization_hash"] = record["materialization_hash"]
    return issue_result(status, SCOPE_MATERIALIZATION, subject, checks, reasons)
