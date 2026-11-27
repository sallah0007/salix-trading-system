"""Protection-disabled mutants for R09 modules; each must make test_r09_boundaries.py (and r08) FAIL. Run: python3 -B tests/trk_stage_a/mutation_sweep_r09.py"""
import subprocess, sys, pathlib, os
ROOT = pathlib.Path(__file__).resolve().parents[2]
M = [
 ("stage_a/binding/producer_binding.py", "if not isinstance(rec, dict):", "if False:"),
 ("stage_a/binding/producer_binding.py", "    if extra:", "    if False:"),
 ("stage_a/binding/producer_binding.py", "    if missing:", "    if False:"),
 ("stage_a/binding/producer_binding.py", "if type(v) is not str or not v.strip():", "if type(v) is not str:"),
 ("stage_a/binding/producer_binding.py", "if not _HEX64.match(rec[\"content_hash\"]):", "if False:"),
 ("stage_a/binding/producer_binding.py", 'r"[0-9a-f]{64}\\Z"', 'r"[0-9a-f]{64}"'),
 ("stage_a/fw/descriptor_crosswalk.py", "return check_shape(b)", "return b"),
 ("stage_a/security/principals.py", "if not isinstance(rec, dict):", "if False:"),
 ("stage_a/security/principals.py", "if type(v) is not str or not v.strip():", "if v is None:"),
 ("stage_a/security/principals.py", "if set(rec) - set(GRANT_EVIDENCE_FIELDS):", "if False:"),
 ("stage_a/security/principals.py", 'if scope == "E06": capabilities(rec["role"])', 'if scope == "E06": pass'),
 ("stage_a/health/envelope.py", 'if "ML_LOCAL_STATE" in e:', "if False:"),
 ("stage_a/health/envelope.py", "    if independent_local_evidence:\n        causes.append", "    if independent_local_evidence and not upstream_unhealthy:\n        causes.append"),
 ("stage_a/coordination/provider_contract.py", 'if not isinstance(evidence, dict) or not evidence.get("provider_id"):', "if False:"),
 ("stage_a/coordination/provider_contract.py", 'if results.get(c) != "PASS":', 'if results.get(c) is None:'),
 ("stage_a/coordination/provider_contract.py", "    return got is not None and got[0] == data", "    return got is not None"),
 ("stage_a/coordination/provider_contract.py", '"read_after_write_probe": None}', '"read_after_write_probe": "get", "x": None}'),
]
TESTS = ["tests/trk_stage_a/test_r09_boundaries.py", "tests/trk_stage_a/test_r08_completion.py"]
def run():
    return subprocess.run([sys.executable, "-B", "-m", "pytest", "-q", "-x", *[str(ROOT / t) for t in TESTS]], cwd=ROOT, capture_output=True, text=True,
                          env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1")).returncode
def main():
    assert run() == 0, "baseline must pass"
    bad = []
    for rel, old, new in M:
        p = ROOT / rel; src = p.read_text()
        if src.count(old) != 1:
            print("NOT APPLICABLE (count=%d): %s :: %s" % (src.count(old), rel, old.strip()[:60])); bad.append(rel); continue
        try:
            p.write_text(src.replace(old, new)); killed = run() != 0
        finally:
            p.write_text(src)
        print(("killed  " if killed else "SURVIVED"), rel, "::", old.strip()[:70])
        if not killed: bad.append((rel, old))
    print("mutants: %d, survived/unapplied: %d" % (len(M), len(bad)))
    assert run() == 0
    return 1 if bad else 0
if __name__ == "__main__": sys.exit(main())
