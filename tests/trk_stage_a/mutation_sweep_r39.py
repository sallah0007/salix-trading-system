"""R39 mutants for code added/changed in R39 (findings 1-6). One at a time, file restored; NOT APPLICABLE or SURVIVED fails the run. Named equivalents listed below. (The R38 sweep is historical: its RS/SB/PS/RL lines target pre-R39 text.) AUTHOR-RUN evidence, not CI."""
import subprocess, sys, pathlib, os
ROOT = pathlib.Path(__file__).resolve().parents[2]
SV="stage_a/tracker/stored_values.py"; RS="stage_a/tracker/relationship_store.py"; CO="stage_a/tracker/composition.py"; PS="stage_a/ops/process_supervisor.py"; SB="stage_a/tracker/snapshot_binding.py"; RL="stage_a/tracker/research_lineage.py"; TC="stage_a/core/tracker_core.py"; RE="stage_a/tracker/registry_entry.py"; LF="stage_a/coordination/lifecycle_framework.py"
M = [
 (SV, 'if k != stored_values_key(mh, segment_id(b)) or', 'if False or'),
 (RS, 'if want != rel: raise', 'if False: raise'),
 (RS, 'if self._schema is None or rel.schema_version != self._schema.version: raise', 'if False: raise'),
 (RS, 'if not (isinstance(cp, dict) and isinstance(cs, dict)): raise', 'if False: raise'),
 (RS, 'if self._schema is None or self._content is None: raise', 'if False: raise'),
 (RS, 'elif self._recompute(predecessor, successor, r.evidence_refs, self._attr.get(k, ())) != r: why', 'elif False: why'),
 (RS, 'if self._schema is None or self._schema.version != current_schema_version: why = "CURRENT_SCHEMA_NOT_BOUND_HELD"', 'if False: why = "CURRENT_SCHEMA_NOT_BOUND_HELD"'),
 (RS, 'if why is not None: return RelationshipReference(', 'if False: return RelationshipReference('),
 (RS, 'defect_verifier=self._verifier, defect_evidence_refs=tuple(evidence_refs), attributable_fields=tuple(attributable))', 'defect_verifier=None, defect_evidence_refs=tuple(evidence_refs), attributable_fields=tuple(attributable))'),
 (CO, 'else: absent("STORED_VALUES_REQUIRED_BUT_NOT_SUPPLIED" if l2_applicability is not None else "L2_APPLICABILITY_UNBOUND_HELD")', 'else: pass'),
 (CO, 'elif l2_applicability is not None and not l2_applicability.required:', 'elif l2_applicability is not None:'),
 (CO, 'self._core.record_verification(key, fk.feature_version, "REQUIRED", "UNAVAILABLE",', 'self._core.record_verification(key, fk.feature_version, "REQUIRED", "PASS",'),
 (CO, 'if l2_ok[0] else "PUBLISHED_SIMULATION_L2_NOT_PASS"', 'if True else "PUBLISHED_SIMULATION_L2_NOT_PASS"'),
 (CO, 'type(self.required) is bool', 'True'),
 (PS, 'if left <= 0: p.kill(); p.wait(); return "LOST", "CHILD_REPLY_TIMEOUT"', 'if left <= 0: left = 1e9'),
 (PS, 'if len(buf) > MAX_FRAME_BYTES and b"\\n" not in buf[:MAX_FRAME_BYTES]: p.kill(); p.wait(); return "LOST", "CHILD_REPLY_OVERSIZED"', 'pass'),
 (PS, 'if rest or len(line) > MAX_FRAME_BYTES: p.kill(); p.wait(); return "LOST", "CHILD_REPLY_MALFORMED"', 'pass'),
 (PS, 'math.isfinite(reply_timeout) and ', ''),
 (PS, 'type(reply_timeout) in (int, float)', 'isinstance(reply_timeout, (int, float))'),
 (PS, 'old.wait(); self._close_streams(old)', 'old.wait()'),
 (PS, '            self._close_streams(p)\n    def __enter__', '    def __enter__'),
 (SB, 'or body.get("state") != TF.RESOLVED', ''),
 (SB, 'e.get("selection_state") != TF.SELECTED', 'False'),
 (SB, 'if manifest.timeframe_or_event_class not in', 'if False and manifest.timeframe_or_event_class not in'),
 (RL, 'if b["attempt_id"] in atts and atts[b["attempt_id"]] != b: raise', 'if False: raise'),
 (RL, 'try: return self._j.append(st[3], d[0], d[1])', 'try: return self._j.append(self._j.head(), d[0], d[1])'),
 (RL, 'except HeadMismatch: continue', 'except HeadMismatch: raise'),
 (RL, 'truth = self._facts(st, family, battery)["attempts"]', 'truth = declared_n if type(declared_n) is int else -1'),
 (RL, 'if d is None: return None\n', 'if d is None: return 1\n'),

 (CO, 'if (research_lineage is None) != (attempt_id is None):', 'if False:'),
 (CO, 'if research_lineage is not None and not research_lineage.resolves(attempt_id):', 'if False:'),
 (CO, 'if lifecycle is None or lifecycle_transition is None: r.log("lifecycle", "HELD"', 'if False: r.log("lifecycle", "HELD"'),
 (CO, 'try: rec = lifecycle.apply(key, *lifecycle_transition)', 'try: rec = None'),
 (RE, 'origin in RSM.ORIGINS and', 'True and'),
 (RE, 'len(set(test_evidence_refs)) == len(test_evidence_refs)', 'True'),
 (RE, 'if lifecycle is None or not hasattr(lifecycle, "history"): raise', 'if False: raise'),
 (RE, 'chain = RSM.resolve_survivor_chain(ptr, subject)', 'chain = (subject,)'),
 (RE, 'lifecycle.history(subject)', '()'),
 (LF, 'if b["subject"] == subject)', 'if True)'),
]
EQUIVALENT = [   # NAMED EQUIVALENTS (outcome-identical; recorded, not hidden)
 (SV, 'or rec.get("segment_id") != segment_id(b)', '', "verify_stored_values (stored_values.py line 56) repeats the identical segment_id check on the same body: same FAIL/NOT_HEALTHY; only the reason text differs"),
 (SV, 'or rec.get("materialization_hash") != mh', '', "same: line 56 repeats the materialization_hash check"),
 (SV, 'or rec.get("feature_key") != feature_key.key():', ':', "same: line 56 repeats the feature_key check"),
 (CO, 'if e.code == "STORED_VALUES_CLASS_MISMATCH": raise', 'pass', "absent() starts with SV._require_same_class, which re-raises the identical STORED_VALUES_CLASS_MISMATCH Refusal: the explicit re-raise is a duplicate guard"),
]
T = [f"tests/trk_stage_a/{f}" for f in ("test_r38_stored_values_scope.py", "test_r38_relationship_snapshot.py", "test_r38_composition.py", "test_r38_process_supervisor.py", "test_r38_research_lineage.py", "test_r37_stored_values.py", "test_r38_stored_values_class.py")]
def run():
    try: return subprocess.run([sys.executable, "-B", "-m", "pytest", "-q", "-x", *[str(ROOT / t) for t in T]], cwd=ROOT, capture_output=True, text=True, timeout=240, env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1")).returncode
    except subprocess.TimeoutExpired: return 99
def main():
    assert run() == 0; bad = []
    for rel, old, new in M:
        p = ROOT / rel; s = p.read_text()
        if s.count(old) != 1: print("NOT APPLICABLE", old[:70].replace("\n", " ")); bad.append(old); continue
        try: p.write_text(s.replace(old, new)); k = run() != 0
        finally: p.write_text(s)
        print("killed  " if k else "SURVIVED", old[:70].replace("\n", " ")); k or bad.append(old)
    print("mutants: %d, survived/unapplied: %d" % (len(M), len(bad))); assert run() == 0; return 1 if bad else 0
if __name__ == "__main__": sys.exit(main())
