"""Mutants for R13 new code only. Run: python3 -B tests/trk_stage_a/mutation_sweep_r13.py  (60 s per-mutant timeout; a hang counts as killed)"""
import subprocess, sys, pathlib, os
ROOT = pathlib.Path(__file__).resolve().parents[2]
BO = "stage_a/tracker/build_output_check.py"; LS = "stage_a/tracker/lifecycle_status_event.py"; NH = "stage_a/context/news_hub_v2.py"
BR = "stage_a/health/blast_radius.py"; FR = "stage_a/fw/return_lineage.py"; QI = "stage_a/tracker/quant_intake_adapter.py"; ML = "stage_a/ml/receiver.py"
M = [(BO, "    bad = sorted(set(bo) & FORBIDDEN_FIELDS)\n    if bad:", "    bad = []\n    if bad:"), (BO, 'if bo.get("ORDER_ID") != order_id or not _present(bo.get("ORDER_ID")):', "if False:"),
     (BO, 'if bo.get("CREATION_REQUEST_ID") != creation_request_id or not _present(bo.get("CREATION_REQUEST_ID")):', "if False:"),
     (BO, "    if learned_derived:\n        missing", "    if False:\n        missing"), (BO, "    elif any(bo.get(k) is not None", "    elif False and any(bo.get(k) is not None"),
     (BO, 'if k in KNOWN_TOKEN_FIELDS and not _present(v) and k != "CLAIM_ID":', "if False:"),
     (BO, "        if consulted_by_verification is True:", "        if False:"), (BO, "        if consulted_by_verification is None:", "        if False:"),
     (BO, "    if dangling:", "    if False:"), (BO, "        if not _present(not_possible_governed_reason_ref):", "        if False:"),
     (BO, "    if declared_hash != recomputed_hash:", "    if False:"), (BO, "    if not isinstance(bo, dict):\n        raise Refusal(type(bo).__name__", "    if False:\n        raise Refusal(type(bo).__name__"),
     (QI, 'learned_derived=bool(m.data["fit_refs"]))', "learned_derived=False)"), (QI, 'fail("BUILD_OUTPUT_CONTRACT", e.code)', "pass"),
     (LS, "    if rec.kind not in KINDS:", "    if False:"), (LS, "check_status_event(ev, context_known)", "pass"),
     (LS, 'if boundary_evidence and k in boundary_evidence and k != "PRIOR_STATE" and boundary_evidence[k] != ev[k]:', "if False:"),
     (LS, 'if prior_kind is not None and boundary_evidence and boundary_evidence.get("PRIOR_STATE") not in (None, prior_kind):', "if False:"),
     (LS, '"PRIOR_STATE": prior_kind if prior_kind is not None else (boundary_evidence or {}).get("PRIOR_STATE")}', '"PRIOR_STATE": prior_kind}'),
     (NH, 'if rec["KNOWABILITY_MODE"] not in KNOWABILITY:', "if False:"), (NH, "        if need:", "        if False:"),
     (NH, 'if rec["ACTUAL_AVAILABLE_ASOF"] != max(rec["ACTUAL_PUBLICLY_AVAILABLE_AT"], rec["ACTUAL_SALIX_RECEIVED_AT"]):', "if False:"),
     (NH, 'if rec.get("IMPACT_RATING") is not None and rec.get("IMPACT_RATING_VINTAGE") is None:', "if False:"),
     (NH, '    if "NO_EVENT_RECORDED" in rec:', "    if False:"), (NH, "    if missing:\n        raise Refusal(\",\".join(missing), code=\"DAILY_RECORD_FIELD_MISSING\")", "    if False:\n        raise Refusal(\",\".join(missing), code=\"DAILY_RECORD_FIELD_MISSING\")"),
     (NH, "    if ev[\"REVISION_AVAILABLE_AT\"] > cutoff:", "    if False:"), (NH, 'ev["ACTUAL_AVAILABLE_ASOF"] > cutoff', "False"),
     (NH, "top = max(e.get(\"REVISION_SEQ\", 0) for e in avail)", "top = min(e.get(\"REVISION_SEQ\", 0) for e in avail)"),
     (NH, 'if len({e["FACTUAL_PAYLOAD_HASH"] for e in cands}) > 1:', "if False:"), (NH, '"exhaustive": daily_record["COVERAGE_STATE"] == "COMPLETE"', '"exhaustive": True'),
     (NH, "    for eid in sorted(by_id, key=str):", "    for eid in list(by_id):"),
     (BR, "    return \"REFUSE_UNPROVEN_INDEPENDENCE\" if required else", "    return \"ALLOW_PROVEN_INDEPENDENT\" if required else"),
     (BR, "    if impact.verdict == UNAFFECTED:\n        return \"ALLOW", "    if False:\n        return \"ALLOW"),
     (FR, "    if not classes:", "    if False:"), (FR, "    if bad:", "    if False:"), (FR, "if fw_derived_predictive and augmented is None:", "if False:"),
     (ML, '"fw_generation_identity_ref", "research_exposure_ref", "support_ref"):', '):')]
T = ["tests/trk_stage_a/test_r13_build_output.py", "tests/trk_stage_a/test_r13_status_event.py", "tests/trk_stage_a/test_r13_context_resolver.py", "tests/trk_stage_a/test_r14_event_causality.py",
     "tests/trk_stage_a/test_r13_fw_return.py", "tests/trk_stage_a/test_r12_blast_radius.py", "tests/trk_stage_a/test_r12_ml_augmented.py"]
def run():
    try: return subprocess.run([sys.executable, "-B", "-m", "pytest", "-q", "-x", *[str(ROOT / t) for t in T]], cwd=ROOT, capture_output=True, text=True, timeout=60, env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1")).returncode
    except subprocess.TimeoutExpired: return 99
def main():
    assert run() == 0; bad = []
    for rel, old, new in M:
        p = ROOT / rel; s = p.read_text()
        if s.count(old) != 1: print("NOT APPLICABLE", old[:60].replace("\n", " ")); bad.append(old); continue
        try: p.write_text(s.replace(old, new)); k = run() != 0
        finally: p.write_text(s)
        print("killed  " if k else "SURVIVED", old[:70].replace("\n", " ")); k or bad.append(old)
    print("mutants: %d, survived/unapplied: %d" % (len(M), len(bad))); assert run() == 0; return 1 if bad else 0
if __name__ == "__main__": sys.exit(main())
