"""R50 scoped mutation sweep: stage_a/ml/shadow_publication.py."""
import os, pathlib, subprocess, sys
ROOT = pathlib.Path(__file__).resolve().parents[2]; T = "tests/trk_stage_a/test_r50_shadow_publication.py"; F = "stage_a/ml/shadow_publication.py"
M = [("if cur is not None: return cur[1]", "if False: return cur[1]"), ('if type(v) is not bool: raise', 'if False: raise'),
     ('        if self._fenced(logical_key, trigger_id): self._l.record(logical_key, trigger_id, eid, "LIFECYCLE_FENCED"); return "LIFECYCLE_FENCED"\n        verdict', '        verdict'),
     ('        if self._fenced(logical_key, trigger_id): self._l.record(logical_key, trigger_id, eid, "LIFECYCLE_FENCED"); return "LIFECYCLE_FENCED"          # fence after', '        if False: pass          # fence after'),
     ('out = "LIFECYCLE_FENCED" if self._fenced(logical_key, trigger_id) else "MODEL_ABSTAINED"', 'out = "MODEL_ABSTAINED"'),
     ('self._sink(eid, verdict[1])  ', 'pass  '), ('for k, t in items: self._l.expect(k, t)', 'pass'),
     ('if cur == "ABSENT": raise', 'if False: raise'), ('verdict[0] in ("PUBLISH", "ABSTAIN")', 'True'), ('if f is None: raise Refusal(n, code="SHADOW_%s_HELD" % n.upper())', 'pass')]
bad = 0; o = (ROOT / F).read_text()
for i, (a, b) in enumerate(M):
    if a not in o: print("MUTANT %d PATTERN NOT FOUND" % i); sys.exit(2)
    (ROOT / F).write_text(o.replace(a, b, 1))
    try: r = subprocess.run([sys.executable, "-m", "pytest", "-q", "-x", T], cwd=ROOT, capture_output=True, text=True, env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1"))
    finally: (ROOT / F).write_text(o)
    print("mutant %2d %s" % (i, "KILLED" if r.returncode else "SURVIVED")); bad += (r.returncode == 0)
sys.exit(1 if bad else 0)
