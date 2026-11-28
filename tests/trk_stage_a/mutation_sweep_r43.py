"""R43 mutants (historical_eligibility completeness/endpoint/epoch/trust, lifecycle_eligibility basis/time, ml consumer_path blockers, event_context_store, clause reconciliation). One at a time, file restored; NOT APPLICABLE or SURVIVED is reported and fails the run.
Run: python tests/trk_stage_a/mutation_sweep_r43.py (do not edit sources while it runs)."""
import subprocess, sys, pathlib, os
ROOT = pathlib.Path(__file__).resolve().parents[2]
HE="stage_a/tracker/historical_eligibility.py"; LE="stage_a/tracker/lifecycle_eligibility.py"; CP="stage_a/ml/consumer_path.py"; EC="stage_a/context/event_context_store.py"; RC="tools/r43_clause_reconciliation.py"
M = [
 (HE, 'return [e.seq for e in es if e.seq <= resolved_through_seq] == list(range(1, resolved_through_seq + 1))', 'return True'),
 (HE, 'return [e.seq for e in es if e.seq <= resolved_through_seq] == list(range(1, resolved_through_seq + 1))', 'return len(es) > 0 or resolved_through_seq == 0'),
 (HE, 'if slice_closed_at_seq != resolved_through_seq: why.append', 'if False: why.append'),
 (HE, 'if slice_closed_at_seq != resolved_through_seq: why.append', 'if slice_closed_at_seq > resolved_through_seq: why.append'),
 (HE, 'if slice_closed_through_time < event_time: why.append', 'if False: why.append'),
 (HE, 'if resolved_through_seq < required_through_seq: why.append("CURRENT_READ_FRESHNESS_FAIL")', 'pass'),
 (HE, 'if any(e.epoch is None for e in upto): why.append("EPOCH_NOT_RECORDED_HELD")', 'if False: why.append("EPOCH_NOT_RECORDED_HELD")'),
 (HE, 'elif any(e.epoch > epoch_bound for e in upto): why.append("EPOCH_AFTER_BASIS")', 'elif False: why.append("EPOCH_AFTER_BASIS")'),
 (HE, 'if e.event_time <= event_time: latest[e.generation_id] = e.state', 'latest[e.generation_id] = e.state'),
 (HE, 'if len(ok) != 1: return', 'if len(ok) == 0: return'),
 (HE, 'if not _complete_through(all_es, resolved_through_seq): return "UNKNOWN_STALE"', 'pass'),
 (HE, 'if not es: return "UNKNOWN_STALE"', 'pass'),
 (HE, 'return "REVOKED" if any(e.state in revoked_states for e in es) else "TRUSTED"', 'return "TRUSTED"'),
 (LE, 'if now[0] < basis[0]: raise Refusal(str(now), code="LIFECYCLE_ELIG_READ_BASIS_INCOHERENT")', 'pass'),
 (LE, 'if now[0] == basis[0] and now[1] != basis[1]: raise Refusal(str(now), code="LIFECYCLE_ELIG_READ_BASIS_INCOHERENT")', 'pass'),
 (LE, 'if not callable(time_of): raise Refusal("time_of", code="LIFECYCLE_ELIG_TIME_SOURCE_UNBOUND")', 'pass'),
 (LE, 'if type(t) is not int or t < 0: raise Refusal(str(r.seq), code="LIFECYCLE_ELIG_EVENT_TIME_NOT_SUPPLIED")', 'pass'),
 (LE, 'if not callable(index_basis): raise Refusal("index", code="LIFECYCLE_ELIG_INDEX_UNBOUND")', 'pass'),
 (LE, 'if type(closed) is not int or closed < 0: raise Refusal("closure", code="LIFECYCLE_ELIG_CLOSURE_INVALID")', 'pass'),
 (CP, 'blockers.append("DATASET_REVOKED")', 'pass'),
 (CP, 'if gate["verdict"] != "CLEAR": blockers.append("DATASET_ANCESTRY_" + gate["verdict"])', 'pass'),
 (CP, 'if corr["status"] != "VERIFIED_AGAINST_REGISTRY": blockers.append("GENERATION_" + corr["status"])', 'pass'),
 (CP, 'except Refusal as e: blockers.append("SNAPSHOT_" + e.code)', 'except Refusal as e: pass'),
 (CP, 'if bh is None: return MLConsumption(row, None, None, None, None, None, ("NO_DATASET_BINDING_LINK",), HELD)', 'pass'),
 (CP, 'if not row.included: return MLConsumption(', 'if False: return MLConsumption('),
 (CP, 'if s in (SJ.MISMATCH, SJ.MISSING)] + ["JOIN_"', 'if s in (SJ.MISMATCH,)] + ["JOIN_"'),
 (EC, 'if self._e(self._d(raw)) != raw: raise Refusal(ident, code="EVENT_CONTEXT_ENCODING_NOT_ROUND_TRIP")', 'pass'),
 (EC, 'if got is None or got[0] != raw: raise IntegrityFailure("event context identity already bound to different bytes")', 'pass'),
 (EC, 'if self._i(f) != ident or self._e(f) != got[0]: raise IntegrityFailure("stored event context does not match its identity key")', 'pass'),
 (EC, 'if key != _k(FACT, ident) or self._e(f) != raw: raise Refusal(key, code="E05_SOURCE_OBJECT_NOT_CONTENT_ADDRESSED")', 'pass'),
 (EC, 'if r.get("event_context_identity") != ident: raise Refusal(key, code="E05_SOURCE_COLUMNS_DISAGREE_WITH_IDENTITY")', 'pass'),
 (RC, '"TR-03", "S2 s27", "SD"', '"TR-03", "S2 s27", "XX"'),
]
T = [f"tests/trk_stage_a/{f}" for f in ("test_r41_historical_eligibility.py", "test_r42_lifecycle_eligibility.py", "test_r43_ml_integration.py", "test_r43_maintenance_recovery.py", "test_r43_event_context_store.py", "test_r42_e05_owning_sources.py", "test_r43_clause_reconciliation.py")]
def run():
    try: return subprocess.run([sys.executable, "-B", "-m", "pytest", "-q", "-x", "-p", "no:cacheprovider", *[str(ROOT / t) for t in T]], cwd=ROOT, capture_output=True, text=True, timeout=300, env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1")).returncode
    except subprocess.TimeoutExpired: return 99
def main():
    assert run() == 0; bad = []
    for rel, old, new in M:
        p = ROOT / rel; s = p.read_text()
        if s.count(old) != 1: print("NOT APPLICABLE", old[:70]); bad.append(old); continue
        try: p.write_text(s.replace(old, new)); k = run() != 0
        finally: p.write_text(s)
        print("killed  " if k else "SURVIVED", old[:70], flush=True); k or bad.append(old)
    print("mutants: %d, survived/unapplied: %d" % (len(M), len(bad))); assert run() == 0; return 1 if bad else 0
if __name__ == "__main__": sys.exit(main())
