"""R54 scoped mutation sweep: stage_a/tracker/observation_snapshot.py (+ Core.observations_for)."""
import os, pathlib, subprocess, sys
ROOT = pathlib.Path(__file__).resolve().parents[2]; T = "tests/trk_stage_a/test_r54_observation_snapshot.py"
O, C = "stage_a/tracker/observation_snapshot.py", "stage_a/core/tracker_core.py"
M = [(O, "if self._pc is None: raise Refusal", "if False: raise Refusal"), (O, "if type(c) is not bool: raise", "if False: raise"), (O, "if avail >= fence: continue", "pass"), (O, "if not rows: return", "if False: return"),
     (O, "member_keys=[r[0] for r in rows]", "member_keys=[r[0] for r in rows[:1]]"), (O, "watermark_source=self._wm", "watermark_source=(lambda tf: 0)"),
     (C, 'and o["facts"].get("instrument") == instrument]', "]"), (C, "if k not in st[\"amb\"] and o[\"facts\"]", "if o[\"facts\"]")]
bad = 0
for i, (f, a, b) in enumerate(M):
    p = ROOT / f; o = p.read_text()
    if a not in o: print("MUTANT %d PATTERN NOT FOUND" % i); sys.exit(2)
    p.write_text(o.replace(a, b, 1))
    try: r = subprocess.run([sys.executable, "-m", "pytest", "-q", "-x", T], cwd=ROOT, capture_output=True, text=True, env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1"))
    finally: p.write_text(o)
    print("mutant %2d %s" % (i, "KILLED" if r.returncode else "SURVIVED")); bad += (r.returncode == 0)
sys.exit(1 if bad else 0)
