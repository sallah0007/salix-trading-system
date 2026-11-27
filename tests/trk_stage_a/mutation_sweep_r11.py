"""Mutants for the R11 arithmetic alignment. Run: python3 -B tests/trk_stage_a/mutation_sweep_r11.py
Known EQUIVALENT (not mutated; defensive duplicates of canonicalisation at input load and at every operator output): the argument canon(...) in evaluator.op_value, canon(v) in the rolling accumulation, and `row = tuple(_z(x) ...)` in the independent reference."""
import subprocess, sys, pathlib, os
ROOT = pathlib.Path(__file__).resolve().parents[2]
EV, OC, SC, IT, MZ, QC = ("stage_a/composer/expression/evaluator.py", "stage_a/composer/expression/opcodes.py", "stage_a/composer/expression/schema.py",
    "stage_a/tracker/verification/independent_traversal.py", "stage_a/tracker/materialization/stateful_materializer.py", "stage_a/tracker/quant_certification.py")
M = [
 (EV, '    return 0.0 if x is not None and x == 0.0 else x', '    return x'),
 (EV, '    return canon(v)', '    return v'),
 (EV, '        raise Refusal("overflow/non-finite result", code="NON_FINITE_RESULT")\n    return canon(x)', '        raise Refusal("overflow/non-finite result", code="NON_FINITE_RESULT")\n    return x'),
 (EV, 'if a[1] == 0.0: raise Refusal("zero denominator", code="DOMAIN_DIV_ZERO")', 'if False: pass'),
 (EV, 'if a[0] < 0.0: raise Refusal("negative sqrt input", code="DOMAIN_SQRT_NEGATIVE")', 'if False: pass'),
 (EV, '[canon(x) for x in series[node["name"]]]', 'list(series[node["name"]])'),
 (OC, 'NOT_ADMITTED_PROFILE_ONLY = frozenset({"log"})', 'NOT_ADMITTED_PROFILE_ONLY = frozenset()'),
 (SC, '_req(op not in NOT_ADMITTED_PROFILE_ONLY, "OPCODE_NOT_ADMITTED_SQE_OPSET_V1_1", str(op))', 'pass'),
 (IT, '    return None if x is None else x + 0.0', '    return x'),
 (IT, 'if row[1] == 0.0: raise RefEvalError("DOMAIN_FAILURE")', 'if False: pass'),
 (IT, 'if row[0] < 0.0: raise RefEvalError("DOMAIN_FAILURE")', 'if False: pass'),
 (IT, 'col[nid] = [_z(x) for x in series[nd["name"]]]', 'col[nid] = list(series[nd["name"]])'),
 (MZ, '"DOMAIN_DIV_ZERO": "DOMAIN_FAILURE"', '"DOMAIN_DIV_ZERO": "OTHER"'),
 (MZ, 'v = canon(row[node["name"]])', 'v = row[node["name"]]'),
 (QC, '        if r is None:', '        if False:'),
 (QC, '        return bool(r)', '        return r is not False'),
]
T = ["tests/trk_stage_a/test_r11_arithmetic.py", "tests/trk_stage_a/test_expression.py", "tests/trk_stage_a/test_verifier_independence.py"]
def run(): return subprocess.run([sys.executable, "-B", "-m", "pytest", "-q", "-x", *[str(ROOT / t) for t in T]], cwd=ROOT, capture_output=True, text=True, env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1")).returncode
def main():
    assert run() == 0; bad = []
    for rel, old, new in M:
        p = ROOT / rel; s = p.read_text()
        if s.count(old) != 1: print("NOT APPLICABLE", rel, old[:60]); bad.append(old); continue
        try: p.write_text(s.replace(old, new)); k = run() != 0
        finally: p.write_text(s)
        print("killed  " if k else "SURVIVED", rel.split("/")[-1], "::", old.strip()[:70]); k or bad.append(old)
    print("mutants: %d, survived/unapplied: %d" % (len(M), len(bad))); assert run() == 0; return 1 if bad else 0
if __name__ == "__main__": sys.exit(main())
