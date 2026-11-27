"""R24 mutants for the paths changed in R24 only (plane identity both directions, read-only identity/mode, rejected-known-candidate result, contract freshness/input validation, positive-witness requirement for
reresolve, fail-closed safety integration + restoration prohibition). Author-run; a surviving mutant is a finding. Earlier sweeps are not re-run."""
import subprocess, sys, pathlib, os
ROOT = pathlib.Path(__file__).resolve().parents[2]
TC = "stage_a/core/tracker_core.py"; RV = "stage_a/tracker/reverification.py"; TF = "stage_a/core/time_family.py"; AM = "stage_a/tracker/accepted_manifest.py"
M = [
     (TC, 'if b.get("plane") != self._plane: raise IntegrityFailure', 'if self._plane is not None and b.get("plane") != self._plane: raise IntegrityFailure'),
     (TC, '        self._replay()          # R24: the established', '        pass          # R24: the established'),
     (TC, '    @property\n    def plane(self): return self._plane', '    plane = None'),
     (TC, '    @property\n    def simulation(self) -> bool: return self._simulation', '    simulation = True'),
     (TC, 'if not isinstance(simulation, bool): raise Refusal("simulation must be a bool", code="SIMULATION_FLAG_INVALID")', 'pass'),
     (TC, '                if cid in known: return REJECTED_KNOWN, None ', '                if False: return REJECTED_KNOWN, None '),
     (TC, '                return CONFLICT, (None if cid in known else ("OBS_AMBIGUOUS", {"key": key, "candidate": cand}))\n            if key in st["obs"]:', '                return CONFLICT, ("OBS_AMBIGUOUS", {"key": key, "candidate": cand})\n            if key in st["obs"]:'),
     (TC, '            if wm > now: out["r"] = ("HELD", "FUTURE_WATERMARK"); return None, None', '            pass'),
     (TC, 'if not _int(wm) or wm < 0: out["r"]', 'if not _int(wm): out["r"]'),
     (TC, 'if now - wm > c["max_staleness"]: out["r"] = ("HELD", "STALE_WATERMARK")', 'if False: out["r"] = ("HELD", "STALE_WATERMARK")'),
     (TC, ' or not _int(max_staleness) or max_staleness < 0 or not isinstance(battery_passed, bool):', ' or not _int(max_staleness) or max_staleness < 0:'),
     (TC, ' or not _int(max_staleness) or max_staleness < 0 or not isinstance(battery_passed, bool):', ' or not isinstance(battery_passed, bool):'),
     (TC, 'if not isinstance(envelope, dict) or not isinstance(raw, bytes) or not _int(now) or now < 0: raise', 'if False: raise'),
     (TC, '            if self._health(st, key, version, now) != "HEALTHY": raise Refusal(key, code="WITNESS_NOT_POSITIVE")', '            pass'),
     (TC, '        if reason == self.REASON_CONTEXT_DOMAIN_METADATA_MISSING: raise Refusal(reason, code="RESTORATION_PROHIBITED_UNTIL_GOVERNED_CONTEXT")', '        pass'),
     (TC, '        decision = fail_closed_transition(subject_kind, True, False) ', '        if not self.simulation: raise Refusal("held", code="X")\n        decision = fail_closed_transition(subject_kind, True, False) '),
     (TC, '"CHAIN_STILL_CURRENT" if (f is not None and f.status == "CURRENT")', '"CHAIN_NOT_CURRENT" if (f is not None and f.status == "CURRENT")'),
     (TC, '"NOT_APPLIED_SUBJECT_TO_MV_AND_STATUS_KIND_MAPPING_UNBOUND"', '"APPLIED"'),
     (TC, '; st["reviews"].setdefault(b["subject"], []).append(b["review"])\n            elif k == "Q_CLEAR"', '\n            elif k == "Q_CLEAR"'),
     (TC, 'if subject_kind not in SUBJECT_DOMAIN: raise Refusal(subject_kind, code="UNKNOWN_SUBJECT_KIND")', 'pass'),
     (TC, 'if evidence_class not in EVIDENCE_CLASSES: raise Refusal(str(evidence_class), code="HEALTH_EVIDENCE_CLASS_UNKNOWN")', 'pass'),
     (TC, '("SIMULATION_COMPOSED_RECOMPUTATION" if composed else "SIMULATION_CALLER_ASSERTED")', '"SIMULATION_CALLER_ASSERTED"'),
     (RV, 'if result.status == INSUFFICIENT_EVIDENCE: return "FAIL", "UNAVAILABLE"', 'pass'),
     (RV, 'if not all(n in names for n in _L2_CHECKS): return l1, "UNAVAILABLE"', 'pass'),
     (RV, 'res.result_hash, evidence_class=COMPOSED_RECOMPUTATION)', 'res.result_hash)'),
     (RV, 'if not isinstance(declared, dict) or set(declared)', 'if False or set(declared)'),
     (RV, 'declared=declared, expect_scope_key=fk.key())', 'declared=declared2(declared, raw), expect_scope_key=fk.key())'),
     (TF, 'return parent_available_asof < query_asof', 'return parent_available_asof <= query_asof'),
     (TF, 'if p[2] is True and parent_visible_asof', 'if parent_visible_asof'),
     (TF, '    if len(set(got)) != len(got): raise Refusal(parent_id, code="DUPLICATE_CHILD_OBSERVATION")', '    pass'),
     (TF, '    if extra: raise Refusal(', '    if False: raise Refusal('),
     (TF, 'if not isinstance(segmentation, dict) or parent_id not in segmentation: return UNDETERMINED', 'if not isinstance(segmentation, dict): return UNDETERMINED'),
     (TF, '        if tf not in self._e: raise Refusal(str(tf), code="UNKNOWN_TIMEFRAME")', '        pass'),
     (AM, 'if manifest_digest(raw) != body["manifest_hash"] or graph_digest', 'if False or graph_digest'),
     (AM, ' or graph_digest(p, enc_bytes) != body["graph_hash"] or program_digest(p, enc_bytes) != body["program_hash"]:', ' or program_digest(p, enc_bytes) != body["program_hash"]:'),
     (AM, ' or program_digest(p, enc_bytes) != body["program_hash"]:', ':'),
     (AM, 'if not isinstance(p, dict) or enc_bytes(p) != raw: raise', 'if not isinstance(p, dict): raise'),
     (AM, 'if (p.get("instrument"), p.get("timeframe")', 'if False and (p.get("instrument"), p.get("timeframe")'),
     (AM, 'if got is None: raise Refusal(body["manifest_hash"], code="ACCEPTED_ARTIFACT_ABSENT")', 'pass'),
     (AM, 'if st is None: raise Refusal(feature_key.key(), code="NO_ACCEPTED_RECORD")', 'pass'),
     (TC, '        if self._timeframes is not None: self._timeframes.require(facts["timeframe"])', '        pass')]
T = ["tests/trk_stage_a/test_r24_core.py", "tests/trk_stage_a/test_r24_composed.py", "tests/trk_stage_a/test_r24_accepted_readback.py"]
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
