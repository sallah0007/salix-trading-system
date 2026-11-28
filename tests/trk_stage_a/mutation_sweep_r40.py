"""R40 mutants for code added in R40 (l2_scope, e05_index, separated_handlers, expectation, composition resolver). One at a time, file restored; NOT APPLICABLE or SURVIVED fails the run. Registry-integrity and composition lineage mutants: see EXCLUDED note in the closeout (not swept in R40 -> stated, not claimed)."""
import subprocess, sys, pathlib, os
ROOT = pathlib.Path(__file__).resolve().parents[2]
L2="stage_a/tracker/l2_scope.py"; EI="stage_a/storage/e05_index.py"; SH="stage_a/ops/separated_handlers.py"; EX="stage_a/health/expectation.py"; CO="stage_a/tracker/composition.py"
M = [
 (L2, 'if resolver is None: return "UNAVAILABLE", "L2_SCOPE_RESOLVER_UNBOUND_HELD"', 'if False: pass'),
 (L2, 'if not isinstance(s, ResolvedL2Scope): return', 'if False: return'),
 (L2, '!= (scope_ref, contract_ref, feature_key, feature_version): return', '!= (s.scope_ref, s.contract_ref, s.feature_key, s.feature_version): return'),
 (L2, 'if s.revoked is not False: return', 'if False: return'),
 (L2, 'if s.current is not True: return', 'if False: return'),
 (L2, 'if s.admitted is not True: return', 'if False: return'),
 (L2, 'if type(s.required) is not bool: return', 'if False: return'),
 (EX, 'or a.subject != subject or', 'or'),
 (EX, 'not (a.valid_from <= at < a.valid_until)', 'False'),
 (EX, 'resolver is not None and resolver(a.admitted_ref) is True', 'True'),
 (EX, 'if len({a.state for a in usable}) > 1:', 'if False:'),
 (EX, 'if type(at) is not int or', 'if False or'),
 (EI, 'or any(c not in row for c in cols): raise', ': raise'),
 (EI, 'and _HASH.match(row["ref_hash"])', ''),
 (EI, 'if not (isinstance(row.get("data_vintage_mode"), str) and row["data_vintage_mode"]): raise', 'if False: raise'),
 (EI, 'if after != before: raise _Moved()', 'pass'),
 (EI, 'if row is None or tuple(row) != tuple(head): raise', 'if row is None: raise'),
 (EI, 'if got != row["ref_hash"]: raise', 'if False: raise'),
 (EI, 'if s in sup: raise Refusal(s, code="E05_SUPERSESSION_FORK")', 'pass'),
 (EI, 'if cur in seen: raise Refusal(start, code="E05_SUPERSESSION_CYCLE")', 'if cur in seen: break'),
 (EI, 'if int(a) <= asof)', 'if True)'),
 (EI, 'authoritative = False', 'authoritative = True'),
 (SH, 'if manifest_digest(raw) != mh: raise', 'if False: raise'),
 (SH, 'if cert.status != "CERTIFIED": raise', 'if False: raise'),
 (SH, 'if ver.status != "PASS": raise', 'if False: raise'),
 (SH, 'if fk.key() != rec["feature_key"]: raise', 'if False: raise'),
 (SH, 'if len(v) != 1 or ', 'if '),
]
# NAMED EQUIVALENT (not run): e05_index.lookup `if got is None: raise IntegrityFailure` -> removed: a None resolver result then fails `got != row["ref_hash"]` and raises the same IntegrityFailure (DRIFT); only the message differs.
T = [f"tests/trk_stage_a/{f}" for f in ("test_r38_composition.py", "test_r40_e05_index.py", "test_r40_separated_handlers.py", "test_r40_health_expectation.py")]
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
