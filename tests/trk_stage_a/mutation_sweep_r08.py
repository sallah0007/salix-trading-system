"""Protection-disabled mutants for R08 modules. Each must make test_r08_completion.py FAIL. Run: python3 -B tests/trk_stage_a/mutation_sweep_r08.py"""
import subprocess, sys, pathlib, os
ROOT = pathlib.Path(__file__).resolve().parents[2]
M = [
 ("stage_a/security/principals.py", "if principal in R7_REPLICA_ONLY:", "if False:"),
 ("stage_a/security/principals.py", "if principal not in E06:", "if False:"),
 ("stage_a/security/principals.py", "if capability not in capabilities(principal):", "if False:"),
 ("stage_a/security/principals.py", "    for a, b in PROHIBITED_MERGES:\n        if a in held and b in held:", "    for a, b in PROHIBITED_MERGES:\n        if False:"),
 ("stage_a/security/principals.py", "    for p in held: capabilities(p)", "    pass"),
 ("stage_a/composer/request_classification.py", "if classification == A.FAILED_REQUESTED_BUILD:", "if False:"),
 ("stage_a/health/envelope.py", "if any(c and s != \"HEALTHY\" for s, c in members):", "if False:"),
 ("stage_a/health/envelope.py", "    if not members:\n        return \"UNKNOWN\"", "    if not members:\n        return \"AGGREGATE_HEALTHY\""),
 ("stage_a/health/envelope.py", "    if independent_local_evidence:\n        causes.append", "    if False:\n        causes.append"),
 ("stage_a/health/envelope.py", "if all(s == \"HEALTHY\" for s, _ in members):", "if all(str(s).upper() == \"HEALTHY\" for s, _ in members):"),
 ("stage_a/fw/descriptor_crosswalk.py", "if b is None:", "if False:"),
 ("stage_a/fw/descriptor_crosswalk.py", "if st in (MISSING_EXACT_SOURCE_MAPPING, INTERNAL_DERIVATION_UNBOUND):", "if False:"),
 ("stage_a/fw/descriptor_crosswalk.py", "if field not in SOURCE_STATUS:", "if False:"),
 ("stage_a/fw/descriptor_crosswalk.py", '"SEGMENT_REF": MISSING_EXACT_SOURCE_MAPPING', '"SEGMENT_REF": DIRECT_SCHEMA_FIELD_NOT_INSTANCE'),
]
def run():
    return subprocess.run([sys.executable, "-B", "-m", "pytest", "-q", "-x", str(ROOT / "tests/trk_stage_a/test_r08_completion.py")], cwd=ROOT,
                          capture_output=True, text=True, env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1")).returncode
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
