"""R50 scoped mutation sweep: the emitter integration in stage_a/tracker/composition.py."""
import os, pathlib, subprocess, sys
ROOT = pathlib.Path(__file__).resolve().parents[2]; T = "tests/trk_stage_a/test_r50_composition_emitter.py"; F = "stage_a/tracker/composition.py"
M = [('getattr(status_emitter, "_path", None) is not self._path or ', ''), (' or status_token is not None', ''), (' or not isinstance(emit, dict):', ':'),
     ('r.status_event, r.audit = em["status_event"], em["audit"];', ''), ('em = status_emitter.emit(fk, supplied, sequence=sequence, **emit)', 'em = {"status_event": None, "audit": None, "replay": False}; self._path.commit(fk, supplied, "SIM_CUR", sequence=sequence)'),
     ('r.status = "HELD_STATUS_EMIT_" + e.code; return', 'r.status = "X"; pass; return'), ('else: self._path.commit(fk, supplied, status_token, sequence=sequence)', 'else: pass')]
o = (ROOT / F).read_text(); bad = 0
for i, (a, b) in enumerate(M):
    if a not in o: print("MUTANT %d PATTERN NOT FOUND" % i); sys.exit(2)
    (ROOT / F).write_text(o.replace(a, b, 1))
    try: r = subprocess.run([sys.executable, "-m", "pytest", "-q", "-x", T, "tests/trk_stage_a/test_r38_composition.py"], cwd=ROOT, capture_output=True, text=True, env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1"))
    finally: (ROOT / F).write_text(o)
    print("mutant %d %s" % (i, "KILLED" if r.returncode else "SURVIVED")); bad += (r.returncode == 0)
sys.exit(1 if bad else 0)
