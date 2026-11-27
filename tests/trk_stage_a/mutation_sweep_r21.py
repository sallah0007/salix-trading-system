"""R21 mutants for the paths changed in R21 (structural authority class, subject-bound terminal identities, absence/non-delivery binding, D14 strict fence, B09 classifier, TrackerCore ports).
Supersedes the AC/TI entries of mutation_sweep_r20.py that anchored removed lines. Unchanged earlier sweeps are not rerun. Run: python3 -B tests/trk_stage_a/mutation_sweep_r21.py"""
import subprocess, sys, pathlib, os
ROOT = pathlib.Path(__file__).resolve().parents[2]
AC = "stage_a/storage/authority_class.py"; TI = "stage_a/tracker/terminal_identity.py"; OB = "stage_a/gateway/outcome_binding.py"; FW = "stage_a/fw/receiver.py"; ML = "stage_a/ml/receiver.py"
NH = "stage_a/context/news_hub_v2.py"; VR = "stage_a/tracker/version_relationship.py"; TC = "stage_a/core/tracker_core.py"
M = [(AC, '    if t is SimulationStore:\n        return SIMULATION', '    if False:\n        return SIMULATION'),
     (AC, '    if t is ObjectStoreJournal:\n        return _root_class(obj._s, depth + 1)', '    if t is ObjectStoreJournal:\n        return QUALIFIED'),
     (AC, '    raise Refusal(t.__name__, code="UNKNOWN_CARRIER")', '    return QUALIFIED'),
     (AC, 'return self._i.put_if_absent(_PREFIX + key, data)', 'return self._i.put_if_absent(key, data)'),
     (TI, 'if by_content or by_canonical:', 'if True:'),
     (TI, '        if r.is_current:\n            continue', '        if False:\n            continue'),
     (TI, 'by_content = key is not None and r.has_content_key', 'by_content = r.has_content_key'),
     (OB, 'if o.feature_id != e.feature_id or o.feature_version != e.feature_version:', 'if False:'),
     (OB, 'o.absence_handling_applied_ref != e.absence_rule_ref:', 'False:'),
     (OB, 'if gateway is not None and gateway.outcome(o.request_id) is not o:', 'if False:'),
     (FW, 'check_dependency_outcome(binding, expected, gateway)                  #', 'pass                  #'),
     (ML, '            check_dependency_outcome(o, e, gateway)                                  # exact', '            pass                                  # exact'),
     (NH, 'if asof >= decision_cutoff:', 'if asof > decision_cutoff:'),
     (NH, 'return bar_or_decision_time > issued_at', 'return bar_or_decision_time >= issued_at'),
     (NH, 'if ev["AVAILABLE_ASOF"] >= cutoff:', 'if ev["AVAILABLE_ASOF"] > cutoff:'),
     (VR, '    if reason in (WORK_NOT_DONE, SOFTWARE_FAILURE):\n        return UNCOMPUTED', '    if reason in (WORK_NOT_DONE, SOFTWARE_FAILURE):\n        return UNCOMPUTABLE'),
     (TC, 'if st["obs"][key] == dg: return REPEAT', 'if True: return REPEAT'),
     (TC, 'if m["available_asof"] < fence: inc.append(m)', 'if m["available_asof"] <= fence: inc.append(m)'),
     (TC, 'if mixed_policy_id is None or mixed_policy_id not in st["policies"]:', 'if False:'),
     (TC, '        if len(hits) != 1:', '        if len(hits) == 0:'),
     (TC, 'now - wm > c["max_staleness"]', 'False'),
     (TC, 'if h["req"] == "REQUIRED": return "HEALTHY" if h["l2"] == "PASS" else "UNKNOWN"', 'if h["req"] == "REQUIRED": return "HEALTHY"'),
     (TC, 'if h is None or now - h["at"] > h["max_age"]: return "UNKNOWN"', 'if h is None: return "UNKNOWN"'),
     (TC, 'if q is None or q["reasons"]: raise Refusal(subject, code="REASONS_STILL_OPEN")', 'if q is None: raise Refusal(subject, code="REASONS_STILL_OPEN")'),
     (TC, 'if bad: raise Refusal(",".join(bad), code="NOT_RECONSTRUCTABLE")', 'if False: raise Refusal(",".join(bad), code="NOT_RECONSTRUCTABLE")'),
     (TC, 'elif k == "Q_REOPEN": st["q"][b["subject"]]["status"] = "REOPENED"', 'elif k == "Q_REOPEN": st["q"][b["subject"]]["status"] = "ACTIVE"'),
     (TC, 'while stack:\n                    d = stack.pop()\n                    if d not in st["inval"]: st["inval"][d] = b["key"]; stack += st["deps"].get(d, [])', 'for d in list(st["deps"].get(b["key"], [])):\n                    st["inval"][d] = b["key"]'),
     (TC, 'if self.simulation: return {"eligible": False', 'if False: return {"eligible": False'),
     (TC, '        if not certifier or certifier == creator:', '        if not certifier:'),
     (TC, 'if (cls == QUALIFIED) == self.simulation:', 'if False:'),
     (TC, 'if set(finding) != set(self.FINDING_FIELDS)', 'if False and set(finding) != set(self.FINDING_FIELDS)')]
T = ["tests/trk_stage_a/test_r20_simulation_boundary.py", "tests/trk_stage_a/test_r20_terminal_scope.py", "tests/trk_stage_a/test_r19_terminal_identity.py", "tests/trk_stage_a/test_r21_absence_binding.py",
     "tests/trk_stage_a/test_r21_core.py", "tests/trk_stage_a/test_r21_version_relationship_reason.py", "tests/trk_stage_a/test_context_contracts.py", "tests/trk_stage_a/test_r14_event_causality.py", "tests/trk_stage_a/test_r13_context_resolver.py"]
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
