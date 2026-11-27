"""R25 mutants for the code changed in R25 B1-B5 only. Author-run; a surviving mutant is a finding. Older sweeps are not re-run."""
import subprocess, sys, pathlib, os
ROOT = pathlib.Path(__file__).resolve().parents[2]
TC = "stage_a/core/tracker_core.py"; RV = "stage_a/tracker/reverification.py"; TF = "stage_a/core/time_family.py"; VR = "stage_a/tracker/verification/verification_result.py"
SV = "stage_a/tracker/verification/stateful_verifier.py"; IH = "stage_a/tracker/verification/independent_hashing.py"; EN = "stage_a/health/envelope.py"
M = [
 (SV, '    chk("materialization_hash_recomputed", materialization_digest(record, enc_bytes) == record["materialization_hash"])', '    chk("materialization_hash_recomputed", True)'),
 (IH, 'if k != "materialization_hash"}', 'if k not in ("materialization_hash", "probe_batch")}'),
 (IH, '_D_MATERIALIZATION = "SALIX_MATERIALIZATION_V1"', '_D_MATERIALIZATION = "SALIX_MATERIALIZATION_V2"'),
 (RV, '    if got != want: raise Refusal', '    if False: raise Refusal'),
 (RV, 'want = SIMULATION if core.simulation else QUALIFIED', 'want = got'),
 (RV, 'evidence_class=COMPOSED_RECOMPUTATION, result=res)', 'evidence_class=COMPOSED_RECOMPUTATION, result=None)'),
 (TC, 'if result is None: raise Refusal("composed evidence needs the verifier result"', 'if False: raise Refusal("composed evidence needs the verifier result"'),
 (TC, 'if not result_is_self_consistent(result): raise', 'if False: raise'),
 (TC, 'result.scope != SCOPE_MATERIALIZATION or ', ''),
 (TC, 'verifier_id != COMPOSED_VERIFIER_ID or ', ''),
 (TC, ' or result_digest != result.result_hash', ''),
 (TC, 'dict(result.subject).get("expect_scope_key") != subject or ', ''),
 (TC, 'l2_requirement != "REQUIRED" or (l1, l2_status) != split_levels(result)', 'l2_requirement != "REQUIRED"'),
 (TC, 'elif result is not None: raise Refusal', 'elif False: raise Refusal'),
 (VR, 'return make_result(result.status, result.scope, dict(result.subject), result.checks, result.reasons).result_hash == result.result_hash', 'return True'),
 (TF, 'if pid in seen and seen[pid][0] != asof: raise', 'if False: raise'),
 (TF, 'if len(tied) > 1: return', 'if False: return'),
 (TF, 'if c is True and parent_visible_asof(a, query_asof)', 'if parent_visible_asof(a, query_asof)'),
 (TF, 'top = max(vis.values())', 'top = min(vis.values())'),
 (EN, 'key = (e["PRODUCER_ID"], subject, e.get("SUBJECT_VERSION_OR_HASH"))', 'key = (e["PRODUCER_ID"], si["AUTHORITY_STATE"], si["INSTRUMENT_ID"], e.get("SUBJECT_VERSION_OR_HASH"))'),
 (EN, 'json.dumps(si, sort_keys=True, allow_nan=False)', 'json.dumps(si, allow_nan=False)'),
 (EN, 'json.dumps(si, sort_keys=True, allow_nan=False)', 'json.dumps(si, sort_keys=True)'),
 (EN, 'e.get("SUBJECT_VERSION_OR_HASH"))\n', '0)\n'),
]
T = ["tests/trk_stage_a/test_r25_defects.py", "tests/trk_stage_a/test_r24_composed.py", "tests/trk_stage_a/test_verifier_independence.py", "tests/trk_stage_a/test_health_envelope.py"]
def run():
    try: return subprocess.run([sys.executable, "-B", "-m", "pytest", "-q", "-x", *[str(ROOT / t) for t in T]], cwd=ROOT, capture_output=True, text=True, timeout=90, env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1")).returncode
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
