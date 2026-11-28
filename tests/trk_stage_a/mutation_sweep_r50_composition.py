"""R50 scoped mutation sweep: the emitter integration in stage_a/tracker/composition.py."""
import os, pathlib, subprocess, sys
ROOT = pathlib.Path(__file__).resolve().parents[2]; T = "tests/trk_stage_a/test_r50_composition_emitter.py"; F = "stage_a/tracker/composition.py"
M = [('getattr(status_emitter, "_path", None) is not self._path or ', ''), (' or status_token is not None', ''), (' or not isinstance(emit, dict):', ':'),
     ('r.status_event, r.audit = em["status_event"], em["audit"];', ''), ('em = status_emitter.emit(fk, supplied, sequence=sequence, **emit)', 'em = {"status_event": None, "audit": None, "replay": False}; self._path.commit(fk, supplied, "SIM_CUR", sequence=sequence)'),
     ('r.status = "HELD_STATUS_EMIT_" + e.code; return', 'r.status = "X"; pass; return'), ('else: self._path.commit(fk, supplied, status_token, sequence=sequence)', 'else: pass'),
     # R52 maintenance connection
     ('str(result.status).startswith("PUBLISHED_")', 'True'), ('callable(stored_inputs.get("fetch")) and callable(stored_inputs.get("series_hash"))', 'True'), ('SV._require_same_class(self._core, j, self._st)\n        b = SV.StoredBinding', 'b = SV.StoredBinding'),
     ('if old is not None and (old.fetch, old.series_hash) != (b.fetch, b.series_hash): raise', 'if False: raise'), ('self._sv[fk.key()] = b; return b', 'return b'),
     ('SV.run_stored_value_pass(self._core, dict(self._sv), sorted(self._sv) if subjects is None else list(subjects), events,', 'SV.run_stored_value_pass(self._core, {}, sorted(self._sv) if subjects is None else list(subjects), events,'),
     ('SV.run_stored_value_pass(self._core, dict(self._sv), sorted(self._sv) if subjects is None else list(subjects), events,', 'SV.run_stored_value_pass(self._core, dict(self._sv), [], (),')]
o = (ROOT / F).read_text(); bad = 0
for i, (a, b) in enumerate(M):
    if a not in o: print("MUTANT %d PATTERN NOT FOUND" % i); sys.exit(2)
    (ROOT / F).write_text(o.replace(a, b, 1))
    try: r = subprocess.run([sys.executable, "-m", "pytest", "-q", "-x", T, "tests/trk_stage_a/test_r38_composition.py"], cwd=ROOT, capture_output=True, text=True, env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1"))
    finally: (ROOT / F).write_text(o)
    print("mutant %d %s" % (i, "KILLED" if r.returncode else "SURVIVED")); bad += (r.returncode == 0)
sys.exit(1 if bad else 0)
