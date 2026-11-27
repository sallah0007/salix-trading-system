"""Mutants for R10 replica role lookup. Run: python3 -B tests/trk_stage_a/mutation_sweep_r10.py"""
import subprocess, sys, pathlib, os
R = "stage_a/composer/request_record.py"
ROOT = pathlib.Path(__file__).resolve().parents[2]; P = "stage_a/security/principals.py"
M = [(P, '"replica-commit-service": frozenset({WRITE_HEAD_TRANSITION})}', '"replica-commit-service": frozenset({WRITE_HEAD_TRANSITION}), "acceptance-origin": frozenset({WRITE_HEAD_TRANSITION})}'),
     (P, '"acceptance-origin": frozenset({WRITE_ACCEPTANCE_EVIDENCE}),', '"acceptance-origin": E06["tracker-acceptor"],'),
     (P, 'if principal == "tracker-acceptor":', "if False:"),
     (P, "_REPLICA_CARRIED = frozenset(E06) - {\"tracker-acceptor\"}", "_REPLICA_CARRIED = frozenset(E06)"),
     (P, '    ("acceptance-origin", "replica-commit-service"),', "    ('x','y'),"),
     (P, 'for r in ("acceptance-origin", "replica-commit-service")', 'for r in ("acceptance-origin",)'),
     (P, "    for p in held: replica_capabilities(p)", "    pass"),
     (P, 'elif scope == "REPLICA": replica_capabilities(rec["role"])', 'elif scope == "REPLICA": pass'),
     (P, "if principal in R7_REPLICA_ONLY:", "if False:")]
M += [(R, 'if stage not in STAGES:', "if False:"), (R, 'if not isinstance(rec, dict):', "if False:"),
      (R, 'if rec.get(k) not in allowed:', "if False:"), (R, 'and rec.get("REQUEST_ORIGIN") != "FORWARD_WALK":', "and False:"),
      (R, 'if rec["REQUEST_CONTEXT"] == "OTHER" or rec["REQUESTER_TYPE"] == "OTHER_GOVERNED_PROCESS":', 'if rec["REQUEST_CONTEXT"] == "OTHER":'),
      (R, 'if rec["REQUEST_CONTEXT"] == "CORRECTION":', "if False:"), (R, 'if stage == "ORDER":', "if False:"),
      (R, 'if rec["TARGET_CONSUMER"] == "UNKNOWN": return "REVIEW_REQUIRED"', "pass"),
      (R, '_text(rec, "REQUESTER_ID", "REQUEST_FIELD_MISSING")', "pass"),
      (R, 'if type(v) is not str or not v.strip():', "if v is None:")]
T = ["tests/trk_stage_a/test_r10_replica_roles.py", "tests/trk_stage_a/test_r09_boundaries.py", "tests/trk_stage_a/test_r08_completion.py"]
def run(): return subprocess.run([sys.executable, "-B", "-m", "pytest", "-q", "-x", *[str(ROOT / t) for t in T]], cwd=ROOT, capture_output=True, text=True, env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1")).returncode
def main():
    assert run() == 0; bad = []
    for rel, old, new in M:
        p = ROOT / rel; s = p.read_text()
        if s.count(old) != 1: print("NOT APPLICABLE", old[:60]); bad.append(old); continue
        try: p.write_text(s.replace(old, new)); k = run() != 0
        finally: p.write_text(s)
        print("killed  " if k else "SURVIVED", old[:70]); k or bad.append(old)
    print("mutants: %d, survived/unapplied: %d" % (len(M), len(bad))); assert run() == 0; return 1 if bad else 0
if __name__ == "__main__": sys.exit(main())
