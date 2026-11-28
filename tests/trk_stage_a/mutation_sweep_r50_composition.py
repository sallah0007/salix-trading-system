"""R50 scoped mutation sweep: the emitter integration in stage_a/tracker/composition.py."""
import os, pathlib, subprocess, sys
ROOT = pathlib.Path(__file__).resolve().parents[2]; T = "tests/trk_stage_a/test_r50_composition_emitter.py"; F = "stage_a/tracker/composition.py"
M = [('getattr(status_emitter, "_path", None) is not self._path or ', ''), (' or status_token is not None', ''), (' or not isinstance(emit, dict):', ':'),
     ('r.status_event, r.audit = em["status_event"], em["audit"];', ''), ('em = status_emitter.emit(fk, supplied, sequence=sequence, **emit)', 'em = {"status_event": None, "audit": None, "replay": False}; self._path.commit(fk, supplied, "SIM_CUR", sequence=sequence)'),
     ('r.status = "HELD_STATUS_EMIT_" + e.code; return', 'r.status = "X"; pass; return'), ('else: self._path.commit(fk, supplied, status_token, sequence=sequence)', 'else: pass'),
     # R52/R53 maintenance connection (owning registration basis)
     ('if basis is None or basis[0] is not result:', 'if basis is None:'),
     ('stored_inputs.get("fetch") is fetch and ', 'True and '), ('and stored_inputs.get("series_hash") is sh): raise', 'and True): raise'), ('SV._require_same_class(self._core, j, self._st)\n        b = SV.StoredBinding(j, self._st, fk, fetch, sh)', 'b = SV.StoredBinding(j, self._st, fk, fetch, sh)'),
     ('self._sv[fk.key()] = b; return b', 'return b'), ('self._pub[key] = (r, r.status, ', 'self._pub[key + "x"] = (r, r.status, '),
     ('SV.run_stored_value_pass(self._core, dict(self._sv), sorted(self._sv) if subjects is None else list(subjects), events,', 'SV.run_stored_value_pass(self._core, {}, sorted(self._sv) if subjects is None else list(subjects), events,'),
     ('SV.run_stored_value_pass(self._core, dict(self._sv), sorted(self._sv) if subjects is None else list(subjects), events,', 'SV.run_stored_value_pass(self._core, dict(self._sv), [], (),'),
     # R54 owning-subject correlation and cold recovery
     ('if self._published.get(fk.key()) is not result: raise', 'if False: raise'), ('getattr(binding, "feature_id", None) != getattr(entry, "feature_id", object()) or ', ''), ('or getattr(binding, "feature_version", None) != fk.feature_version', ''), ('or getattr(entry, "feature_version", None) != fk.feature_version: raise', ': raise'),
     ('if not any(b.get("feature_key") == key for b in self._path.records()): raise', 'if False: raise'), ('if not self._path.source_current(): raise', 'if False: raise'), ('fs.recover()', 'pass'), ('r.published_rows = self._path.feed(gw);', 'r.published_rows = 1;'),
     ('r.log("recovered_committed_status_and_rows", "OK", "rows=%d" % r.published_rows); self._published[key] = r', 'r.log("recovered_committed_status_and_rows", "OK", "rows=%d" % r.published_rows)'),
     ('if v["segments"]:', 'if True:'),
     ('        try: read_accepted_manifest(j, self._st, feature_key)\n        except Refusal as e: raise Refusal(key, code="COMPOSITION_RECOVERY_NO_ACCEPTED_RECORD:" + e.code)', '        pass')]
o = (ROOT / F).read_text(); bad = 0
for i, (a, b) in enumerate(M):
    if a not in o: print("MUTANT %d PATTERN NOT FOUND" % i); sys.exit(2)
    (ROOT / F).write_text(o.replace(a, b, 1))
    try: r = subprocess.run([sys.executable, "-m", "pytest", "-q", "-x", T, "tests/trk_stage_a/test_r38_composition.py", "tests/trk_stage_a/test_r53_real_assembly_base.py"], cwd=ROOT, capture_output=True, text=True, env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1"))
    finally: (ROOT / F).write_text(o)
    print("mutant %d %s" % (i, "KILLED" if r.returncode else "SURVIVED")); bad += (r.returncode == 0)
sys.exit(1 if bad else 0)
