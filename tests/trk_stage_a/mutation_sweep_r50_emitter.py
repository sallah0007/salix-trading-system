"""R50 scoped mutation sweep for stage_a/tracker/status_emitter.py (+ the origin/feature_journal additions in sim_publication_path.py)."""
import os, pathlib, subprocess, sys
ROOT = pathlib.Path(__file__).resolve().parents[2]; T = "tests/trk_stage_a/test_r50_status_emitter.py"
E, P = "stage_a/tracker/status_emitter.py", "stage_a/tracker/sim_publication_path.py"
M = [(E, 'if self._map is None: raise Refusal("kind_to_token", code="STATUS_MAPPING_HELD")', "pass"),
     (E, 'if token is None: raise Refusal(rec.kind, code="STATUS_KIND_UNMAPPED")', "pass"),
     (E, 'if mine and (type(sequence) is not int or sequence <= max(b[seqf] for b in mine)): raise', 'if False: raise'),
     (E, 'if b.get("origin", {}).get("record_hash") == rec.record_hash:', 'if False:'),
     (E, 'if b.get("origin", {}).get("token") != token or b[self._path._spec["status_field"]] != token: raise', 'if False: raise'),
     (E, 'origin={"record_seq": rec.seq, "record_hash": rec.record_hash, "kind": rec.kind, "token": token}, ', ''),
     (E, 'rec = recs[-1]', 'rec = recs[0]'),
     (P, 'body["origin"] = dict(origin)', 'pass'),
     (E, 'expected_source_head=src, expected_side_head=side)', 'expected_side_head=side)'), (E, 'expected_source_head=src, expected_side_head=side)', 'expected_source_head=src)'),
     (E, 'except HeadMismatch: continue', 'except HeadMismatch: raise'), (E, 'if e.code == "SIM_PUBLICATION_SOURCE_HEAD_ADVANCED": continue', 'if False: continue'),
     (P, 'if expected_source_head is not None and src != expected_source_head: raise', 'if False: raise'), (P, 'self._sj.head() if expected_side_head is None else expected_side_head', 'self._sj.head()'),
     (E, 'recs = [r for r in self._path.feature_journal.read_from(1) if r.seq <= head.seq and', 'recs = [r for r in self._path.feature_journal.read_from(1) if')]
bad = 0
for i, (f, a, b) in enumerate(M):
    p = ROOT / f; o = p.read_text()
    if a not in o: print("MUTANT %d PATTERN NOT FOUND" % i); sys.exit(2)
    p.write_text(o.replace(a, b, 1))
    try: r = subprocess.run([sys.executable, "-m", "pytest", "-q", "-x", T], cwd=ROOT, capture_output=True, text=True, env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1"))
    finally: p.write_text(o)
    print("mutant %d %s" % (i, "KILLED" if r.returncode else "SURVIVED")); bad += (r.returncode == 0)
sys.exit(1 if bad else 0)
