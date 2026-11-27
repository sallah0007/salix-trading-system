"""R22 mutants for the paths changed in R22 only (Core held-unless-bound eligibility, stored-fact snapshot members, atomic admission, reconstructability, health validity, exact-type adapter whitelist, ML gateway
requirement, terminal era/scope bounds, construction binding). Supersedes the TrackerCore entries of mutation_sweep_r21.py. Equivalent mutant deliberately not listed: replaying beyond the validated head still fails the head-conditioned append and re-reads. Run: python3 -B tests/trk_stage_a/mutation_sweep_r22.py"""
import subprocess, sys, pathlib, os
ROOT = pathlib.Path(__file__).resolve().parents[2]
TC = "stage_a/core/tracker_core.py"; AC = "stage_a/storage/authority_class.py"; ML = "stage_a/ml/receiver.py"; TI = "stage_a/tracker/terminal_identity.py"; CB = "stage_a/tracker/construction_binding.py"
M = [(TC, '        return {"state": HELD, "eligible": False', '        return {"state": SIM_ELIGIBLE, "eligible": True'),
     (TC, 'ok = self.simulation and not self._blocked', 'ok = not self._blocked'),
     (TC, 'if f is None or f.status != "CURRENT": reasons.append', 'if False: reasons.append'),
     (TC, '            except (HeadMismatch, UnknownCommit):\n                continue', '            except (HeadMismatch, UnknownCommit):\n                return NEW'),
     (TC, 'if o["digest"] == dg and o["available_asof"] == available_asof and o["vintage"] == vintage: return REPEAT, None', 'if o["digest"] == dg: return REPEAT, None'),
     (TC, 'if c is not None and any(c.get(n) != m[n] for n in c):', 'if False:'),
     (TC, 'if f["instrument"] != instrument: raise Refusal(k, code="CROSS_INSTRUMENT_MEMBER")', 'pass'),
     (TC, 'if self._blocked(st, m["key"]): raise Refusal(m["key"], code="MEMBER_BLOCKED")', 'pass'),
     (TC, 'if not self.simulation: res["r"] = ("MIXED_DECLARED_POLICY_UNBOUND_HELD", None); return None, None', 'pass'),
     (TC, 'if p is None or p.get("revoked") or query_asof >= p["expires_at"]:', 'if p is None:'),
     (TC, 'kind = "SIMULATION_MIXED_VIEW"', 'kind = "SEALED"'),
     (TC, '        if not self.simulation: raise Refusal("fresh permitted witness/materialization binding unbound", code="VERIFIER_BINDING_UNBOUND_HELD")', '        pass'),
     (TC, 'if any(u in st["inval"] or self._blocked(st, u) for u in st["ups"].get(key, [])): raise Refusal(key, code="UPSTREAM_STILL_INVALID")', 'pass'),
     (TC, 'if h is None or h["seq"] <= st["inval"][key][1]: raise Refusal(key, code="NO_FRESH_WITNESS")', 'pass'),
     (TC, '        if not self.simulation: raise Refusal("reconstruction proof binding unbound", code="RECONSTRUCTION_PROOF_BINDING_UNBOUND_HELD")', '        pass'),
     (TC, 'bad = [u for u in self._closure(st, subject) if not self._reconstructable(st, u)]', 'bad = []'),
     (TC, 'return up not in st["amb"] and self._payload_reconstructs(o)', 'return up not in st["amb"]'),
     (TC, 'if self._reaches(st, upstream, dependent): raise Refusal(dependent, code="DEPENDENCY_CYCLE")', 'pass'),
     (TC, '        for u in self._closure(st, key):                                     # reverse', '        for u in []:                                     # reverse'),
     (TC, 'if h["at"] > now or now - h["at"] > h["max_age"]: return "UNKNOWN"                # future', 'if now - h["at"] > h["max_age"]: return "UNKNOWN"                # future'),
     (TC, 'if st["reverify"].get(subject, 0) >= h["seq"]: return "UNKNOWN"', 'pass'),
     (TC, 'if h is None or h["version"] != version: return "UNKNOWN"', 'if h is None: return "UNKNOWN"'),
     (TC, 'if l2_requirement == "NOT_APPLICABLE_BY_GOVERNED_DEFINITION" and not definition_ref:', 'if False:'),
     (TC, 'if not _int(at) or at < 0 or not _int(max_age) or max_age <= 0:', 'if False:'),
     (TC, 'if asof_seq is not None: raise Refusal("historical Health', 'if False: raise Refusal("historical Health'),
     (AC, 'if t in _qualified_store_types():', 'if any(t is q or issubclass(t, q) for q in _qualified_store_types()):'),
     (ML, '    if gateway is None:\n        raise Refusal("ML row building needs the issuing Gateway"', '    if False:\n        raise Refusal("ML row building needs the issuing Gateway"'),
     (ML, 'if expected_request_ids is not None and getattr(o, "request_id", None) != expected_request_ids.get(k):', 'if False:'),
     (TI, '        recs = [r for r in recs if r.era_id == active_era_id]', '        pass'),
     (TI, '        if active_era_id != "ERA_1":\n            return ()', '        if False:\n            return ()'),
     (TI, 'if searched_scopes is not None:', 'if False:'),
     (CB, 'if self.status() == HELD_ADMISSION: return False', 'pass'),
     (CB, '    installed = False', '    installed = True')]
T = ["tests/trk_stage_a/test_r24_core.py", "tests/trk_stage_a/test_r22_boundaries.py", "tests/trk_stage_a/test_r22_construction_binding.py", "tests/trk_stage_a/test_r20_terminal_scope.py", "tests/trk_stage_a/test_r20_simulation_boundary.py"]
def run():
    try: return subprocess.run([sys.executable, "-B", "-m", "pytest", "-q", "-x", *[str(ROOT / t) for t in T]], cwd=ROOT, capture_output=True, text=True, timeout=90, env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1")).returncode
    except subprocess.TimeoutExpired: return 99
def main():
    assert run() == 0; bad = []
    for rel, old, new in M:
        p = ROOT / rel; s = p.read_text()
        if s.count(old) != 1: print("NOT APPLICABLE", old[:60].replace("\n", " ")); bad.append(old); continue
        try: p.write_text(s.replace(old, new)); k = run() != 0
        finally: p.write_text(s)
        print("killed  " if k else "SURVIVED", old[:70].replace("\n", " ")); k or bad.append(old)
    print("mutants: %d, survived/unapplied: %d" % (len(M), len(bad))); assert run() == 0; return 1 if bad else 0
if __name__ == "__main__": sys.exit(main())
