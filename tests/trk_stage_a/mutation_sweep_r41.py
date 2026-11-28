"""R41 mutants (supervisor EOF deadline, acceptor binding checks, historical_eligibility, atomic_publication, e05 sources, separated caller). One at a time, file restored; NOT APPLICABLE or SURVIVED fails the run. NOT swept in R41: registry_integrity, composition lineage/registry_gate (see closeout section 20)."""
import subprocess, sys, pathlib, os
ROOT = pathlib.Path(__file__).resolve().parents[2]
PS="stage_a/ops/process_supervisor.py"; SH="stage_a/ops/separated_handlers.py"; HE="stage_a/tracker/historical_eligibility.py"; AP="stage_a/tracker/atomic_publication.py"; ES="stage_a/storage/e05_sources.py"; SC="stage_a/ops/separated_caller.py"
M = [
 (PS, 'except subprocess.TimeoutExpired: p.kill(); p.wait(); return "LOST", "CHILD_REPLY_TIMEOUT"', 'except subprocess.TimeoutExpired: pass'),
 (PS, 'p.wait(timeout=max(deadline - time.monotonic(), 0.0))', 'p.wait()'),
 (SH, 'if not isinstance(rec, dict) or materialization_digest(rec, enc_bytes) != matH or', 'if not isinstance(rec, dict) or'),
 (SH, 'if rec.get("manifest_hash") != mh or rec.get("object_key") != "artifact/" + mh: raise why("SEP_ACCEPT_REFS_DO_NOT_BIND")', 'pass'),
 (SH, 'if art is None or manifest_digest(art[0]) != mh: raise', 'if art is None: raise'),
 (SH, 'and ver["result_hash"] == rh and ver["materialization_hash"] == matH)', ')'),
 (SH, 'if res.result_hash != rh: raise', 'if False: raise'),
 (SH, 'if res.status != PASS or res.scope != SCOPE_MATERIALIZATION or split_levels(res) != ("PASS", "PASS") or not all(ok for _, ok in res.checks): raise', 'if False: raise'),
 (SH, 'if sub.get("materialization_hash") != matH or', 'if False or'),
 (SH, 'if link is None or link[0].decode() != rh: raise', 'if False: raise'),
 (HE, 'if resolved_through_seq < required_through_seq: why.append("CURRENT_READ_FRESHNESS_FAIL")', 'pass'),
 (HE, 'if slice_closed_through_time < event_time: why.append', 'if False: why.append'),
 (HE, 'if [e.seq for e in upto] != list(range(1, len(upto) + 1)) and upto: why.append', 'if False: why.append'),
 (HE, 'if e.event_time <= event_time: latest[e.generation_id] = e.state', 'latest[e.generation_id] = e.state'),
 (HE, 'if len(ok) != 1: return', 'if len(ok) == 0: return'),
 (HE, 'if resolved_through_seq < required_through_seq: return "UNKNOWN_STALE"', 'pass'),
 (HE, 'if not es: return "UNKNOWN_STALE"', 'pass'),
 (HE, 'a.epoch > b.epoch or a.event_time > b.event_time', 'False'),
 (AP, 'if _after_body is not None: _after_body()', 'pass'),
 (AP, 'if cur is None or cur[0].decode() != h: raise IntegrityFailure', 'if False: raise IntegrityFailure'),
 (AP, 'if domain_hash(DOMAIN, b[0]) != h: raise', 'if False: raise'),
 (AP, 'if b is None: raise IntegrityFailure("pointer names a missing body")', 'if b is None: return None'),
 (AP, 'all(rec[f] not in (None, "") for f in self._req)', 'True'),
 (ES, 'if manifest_digest(raw) != mh: raise', 'if False: raise'),
 (ES, 'if not (isinstance(c, str) and c): raise', 'if False: raise'),
 (ES, 'if g is not None: out.append((k, g[1], g[0]))', 'pass'),
 (ES, '"%s:%d" % (k, e) for k, e, _ in l', '"%s" % k for k, e, _ in l'),
 (SC, 'if not (len(done) == 3 and all(r[1] == "DONE" for r in done)):', 'if False:'),
 (SC, 'if self._re is not None: self._re()', 'pass'),
 (SC, 'if not adm.admissible: return', 'if False: return'),
]
T = [f"tests/trk_stage_a/{f}" for f in ("test_r38_process_supervisor.py", "test_r40_separated_handlers.py", "test_r41_historical_eligibility.py", "test_r41_atomic_publication.py", "test_r41_e05_sources.py", "test_r41_separated_caller.py")]
def run():
    try: return subprocess.run([sys.executable, "-B", "-m", "pytest", "-q", "-x", *[str(ROOT / t) for t in T]], cwd=ROOT, capture_output=True, text=True, timeout=240, env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1")).returncode
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
