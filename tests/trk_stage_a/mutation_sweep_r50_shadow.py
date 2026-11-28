"""R50 scoped mutation sweep: stage_a/ml/shadow_publication.py."""
import os, pathlib, subprocess, sys
ROOT = pathlib.Path(__file__).resolve().parents[2]; T = "tests/trk_stage_a/test_r50_shadow_publication.py"; F = "stage_a/ml/shadow_publication.py"
M = [("if cur is not None: return cur[1]", "if False: return cur[1]"), ('if type(v) is not bool: raise', 'if False: raise'),
     ('        if self._fenced(logical_key, trigger_id): self._l.record(logical_key, trigger_id, eid, "LIFECYCLE_FENCED"); return "LIFECYCLE_FENCED"\n        st, got = self._readback(eid)', '        st, got = self._readback(eid)'),
     ('        if self._fenced(logical_key, trigger_id): self._l.record(logical_key, trigger_id, eid, "LIFECYCLE_FENCED"); return "LIFECYCLE_FENCED"          # fence after', '        if False: pass          # fence after'),
     ('out = "LIFECYCLE_FENCED" if self._fenced(logical_key, trigger_id) else "MODEL_ABSTAINED"', 'out = "MODEL_ABSTAINED"'),
     ('try: self._sink.commit(eid, verdict[1])  ', 'try: pass  '), ('for k, t in items: self._l.expect(k, t)', 'pass'),
     ('if cur == "ABSENT": raise', 'if False: raise'), ('verdict[0] in ("PUBLISH", "ABSTAIN")', 'True'), ('if f is None: raise Refusal(n, code="SHADOW_%s_HELD" % n.upper())', 'pass'),
     # R51 additions
     ('        self._l.check_record(logical_key, trigger_id, eid, "PUBLISHED")                                    # R51', '        pass                                    # R51'),
     ('        if st == "UNREADABLE": raise Refusal(eid, code="SHADOW_PUBLICATION_OUTCOME_UNKNOWN")\n        if got is not None:', '        if False: pass\n        if got is not None:'),
     ('            if st == "UNREADABLE": raise Refusal(eid, code="SHADOW_PUBLICATION_OUTCOME_UNKNOWN")           # slot', '            if False: pass           # slot'),
     ('            if got is None: self._pending.pop(slot, None); raise ', '            if False: raise '),
     ('            if _h(got) != h: raise Refusal(eid, code="SHADOW_SINK_DIFFERENT_PAYLOAD")', '            if False: raise Refusal(eid, code="SHADOW_SINK_DIFFERENT_PAYLOAD")'),
     ('if pend is not None and pend[1] != _h(got): raise', 'if False: raise'),
     ('        if got is not None:\n            pend', '        if False:\n            pend'),
     ('callable(getattr(sink, "readback", None))', 'True')]
bad = 0; o = (ROOT / F).read_text()
for i, (a, b) in enumerate(M):
    if a not in o: print("MUTANT %d PATTERN NOT FOUND" % i); sys.exit(2)
    (ROOT / F).write_text(o.replace(a, b, 1))
    try: r = subprocess.run([sys.executable, "-m", "pytest", "-q", "-x", T], cwd=ROOT, capture_output=True, text=True, env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1"))
    finally: (ROOT / F).write_text(o)
    print("mutant %2d %s" % (i, "KILLED" if r.returncode else "SURVIVED")); bad += (r.returncode == 0)
sys.exit(1 if bad else 0)
