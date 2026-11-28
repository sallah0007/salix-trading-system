"""R42 mutants (registry-gate report scope, expectation payload correlation, lifecycle_eligibility, final-resolution/sequence E05 sources, partial-observation boundary, composition consumers). One at a time, file restored; NOT APPLICABLE or SURVIVED fails the run. NOT swept: ops/separated_*, the A07 tool, the clause-status generator (guarded by its own completeness test)."""
import subprocess, sys, pathlib, os
ROOT = pathlib.Path(__file__).resolve().parents[2]
CO="stage_a/tracker/composition.py"; EX="stage_a/health/expectation.py"; LE="stage_a/tracker/lifecycle_eligibility.py"; ES="stage_a/storage/e05_sources.py"; RI="stage_a/tracker/registry_integrity.py"
M = [
 (CO, 'if not isinstance(rep, IntegrityReport): return "MALFORMED"', 'pass'),
 (CO, 'if rep.subject != key: return "SUBJECT_DIFFERS_FROM_ACCEPTED_FEATURE"', 'pass'),
 (CO, 'if rep.creation_request_id != getattr(pkg, "request_id", None): return "CREATION_REQUEST_DIFFERS_FROM_PACKAGE"', 'pass'),
 (CO, 'type(rep.checked_at) is not int or type(now) is not int or type(max_age) is not int or rep.checked_at > now or now - rep.checked_at > max_age', 'False'),
 (CO, 'rep.checked_at > now or now - rep.checked_at > max_age', 'now - rep.checked_at > max_age'),
 (CO, 'rep.checked_at > now or now - rep.checked_at > max_age', 'rep.checked_at > now'),
 (CO, 'if why is not None: r.status = "HELD_REGISTRY_REPORT_SCOPE_" + why; return', 'if False: r.status = "HELD_REGISTRY_REPORT_SCOPE_" + why; return'),
 (EX, 'isinstance(r, ResolvedExpectation) and ', ''),
 (EX, '(r.admitted_ref, r.subject, r.state, r.valid_from, r.valid_until) == (a.admitted_ref, a.subject, a.state, a.valid_from, a.valid_until)', 'r.admitted_ref == a.admitted_ref'),
 (EX, '(r.admitted_ref, r.subject, r.state, r.valid_from, r.valid_until) == (a.admitted_ref, a.subject, a.state, a.valid_from, a.valid_until)', '(r.admitted_ref, r.subject, r.valid_from, r.valid_until) == (a.admitted_ref, a.subject, a.valid_from, a.valid_until)'),
 (EX, '(r.admitted_ref, r.subject, r.state, r.valid_from, r.valid_until) == (a.admitted_ref, a.subject, a.state, a.valid_from, a.valid_until)', '(r.admitted_ref, r.subject, r.state) == (a.admitted_ref, a.subject, a.state)'),
 (EX, 'and r.admitted is True and r.current is True and r.revoked is False)', 'and r.current is True and r.revoked is False)'),
 (EX, 'and r.admitted is True and r.current is True and r.revoked is False)', 'and r.admitted is True and r.revoked is False)'),
 (EX, 'and r.admitted is True and r.current is True and r.revoked is False)', 'and r.admitted is True and r.current is True)'),
 (EX, 'if len({a.state for a in usable}) > 1:', 'if False:'),
 (LE, 'if type(t) is not int or t < 0: raise', 'if False: raise'),
 (LE, 'later = any(e.event_time > event_time for e in es)', 'later = True'),
 (LE, 'later = any(e.event_time > event_time for e in es)', 'later = any(e.event_time >= event_time for e in es)'),
 (LE, 'required_through_seq=head_seq, resolved_through_seq=index_resolved_through(), revoked_states', 'required_through_seq=0, resolved_through_seq=index_resolved_through(), revoked_states'),
 (LE, 'if not callable(index_resolved_through): raise', 'if False: raise'),
 (ES, 'if D._ident_key(ident) != k: raise Refusal(k, code="E05_SOURCE_OBJECT_NOT_CONTENT_ADDRESSED")', 'pass'),
 (ES, 'else: raise Refusal(k, code="E05_SOURCE_OUTCOME_TYPE_UNMAPPED")', 'else: continue'),
 (ES, 'if fn is None: raise Refusal(table, code="E05_SOURCE_MAPPER_NOT_SUPPLIED")', 'if fn is None: continue'),
 (ES, 'if g is None: raise Refusal(k, code="E05_SOURCE_LISTED_OBJECT_UNREADABLE")', 'if g is None: continue'),
 (ES, 'if i in seen: raise Refusal(i, code="E05_SOURCE_DUPLICATE_IDENT")', 'pass'),
 (ES, 'if not (isinstance(i, str) and i): raise Refusal(table, code="E05_SOURCE_IDENT_INVALID")', 'pass'),
 (ES, '"%s:%s" % (i, v[i][1]) for i in sorted(v)', '"%s" % i for i in sorted(v)'),
 (ES, 'if ident_of(o) == want: return hash_of(o)', 'if ident_of(o) == want: return "x"'),
 (ES, 'raise Refusal("stagea_event_context_index", code="E05_SOURCE_EVENT_CONTEXT_HELD_NO_ENCODING_INTERFACE")', 'return iter(())'),
 (RI, 'IntegrityReport(subj, tuple(out), overall, False, entry.creation_request_id, now)', 'IntegrityReport(subj, tuple(out), overall, False, "", now)'),
]
T = [f"tests/trk_stage_a/{f}" for f in ("test_r40_registry_integrity.py", "test_r40_health_expectation.py", "test_r42_lifecycle_eligibility.py", "test_r42_e05_owning_sources.py", "test_r42_partial_observation.py", "test_r42_consumer_path.py")]
def run():
    try: return subprocess.run([sys.executable, "-B", "-m", "pytest", "-q", "-x", "-p", "no:cacheprovider", *[str(ROOT / t) for t in T]], cwd=ROOT, capture_output=True, text=True, timeout=240, env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1")).returncode
    except subprocess.TimeoutExpired: return 99
def main():
    assert run() == 0; bad = []
    for rel, old, new in M:
        p = ROOT / rel; s = p.read_text()
        if s.count(old) != 1: print("NOT APPLICABLE", old[:70]); bad.append(old); continue
        try: p.write_text(s.replace(old, new)); k = run() != 0
        finally: p.write_text(s)
        print("killed  " if k else "SURVIVED", old[:70]); k or bad.append(old)
    print("mutants: %d, survived/unapplied: %d" % (len(M), len(bad))); assert run() == 0; return 1 if bad else 0
if __name__ == "__main__": sys.exit(main())
