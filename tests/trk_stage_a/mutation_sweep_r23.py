"""R23 mutants for the paths changed in R23 only (asserted admission, candidate-preserving resolution, epoch supersession/basis, reconstruction, typed health, unknown-commit resolution, plane identity, terminal subject validity). Supersedes the TrackerCore/terminal entries of mutation_sweep_r22.py whose anchors changed. Run: python3 -B tests/trk_stage_a/mutation_sweep_r23.py"""
import subprocess, sys, pathlib, os
ROOT = pathlib.Path(__file__).resolve().parents[2]
TC = "stage_a/core/tracker_core.py"; AC = "stage_a/storage/authority_class.py"; ML = "stage_a/ml/receiver.py"; TI = "stage_a/tracker/terminal_identity.py"; CB = "stage_a/tracker/construction_binding.py"
M = [
     (CB, '        if self.status() != SIMULATION_EVIDENCE: return False', '        if self.status() == HELD_ADMISSION: return False'),
     (TI, 'if mode not in SUBJECT_MODES: return "SUBJECT_MODE_INVALID"', 'pass'),
     (TI, 'if ls not in LOOKUP_ERA_SCOPES: return "LOOKUP_ERA_SCOPE_INVALID"', 'pass'),
     (TI, 'if errs: return "NORMALIZER_NOT_GOVERNED"', 'pass'),
     (TI, '        if cerrs: return "CANDIDATE_CONTENT_INVALID"', '        pass'),
     (TI, '        return "CANDIDATE_CONTENT_REQUIRED"', '        return ""'),
     (TI, 'if any(k in subject for k in ("content_key", "content_identity_key", "content_key_composite")): return "SUPPLIED_CONTENT_KEY_NOT_ACCEPTED"', 'pass'),
     (TC, '                if landed and landed[0].record_hash == want: return out', '                if False: return out'),
     (TC, '            except HeadMismatch:\n                continue', '            except HeadMismatch:\n                return out'),
     (TC, 'if not self._payload_reconstructs(st["cands"][key][chosen_cid]): raise Refusal(key, code="CANDIDATE_INTEGRITY_FAILED")', 'pass'),
     (TC, 'st["obs"][b["key"]] = st["cands"][b["key"]][b["cid"]]', 'st["obs"][b["key"]] = st["obs"][b["key"]]'),
     (TC, 'return CONFLICT, (None if cid in known else ("OBS_AMBIGUOUS", {"key": key, "candidate": cand}))     # complete', 'return CONFLICT, ("OBS_AMBIGUOUS", {"key": key, "candidate": cand})     # complete'),
     (TC, 'canonical_bytes({"digest": digest, "available_asof": available_asof, "vintage": vintage})', 'canonical_bytes({"digest": digest})'),
     (TC, ' and TrackerCore._cid(o["digest"], o["available_asof"], o["vintage"]) == o["cid"]', ''),
     (TC, '        return bool(ups) and all(self._reconstructable(st, u, _seen | {up}) for u in ups)', '        return True'),
     (TC, 'if up in _seen or self._blocked(st, up): return False', 'if up in _seen: return False'),
     (TC, 'return HealthReading(local if self.simulation else HELD,', 'return HealthReading(local,'),
     (TC, '        if not self.simulation: raise Refusal("source approval/evidence binding unbound", code="SOURCE_APPROVAL_BINDING_UNBOUND_HELD")\n        if not certifier', '        if not certifier'),
     (TC, '        if not self.simulation: raise Refusal("source approval/evidence binding unbound", code="SOURCE_APPROVAL_BINDING_UNBOUND_HELD")\n        if not creator', '        if not creator'),
     (TC, 'if self.plane is not None and b.get("plane") != self.plane: raise IntegrityFailure', 'if False: raise IntegrityFailure'),
     (TC, '; st["reverify"][b["subject"]] = r.seq        # eligibility', '        # eligibility'),
     (TC, 'if o is not None: return up not in st["amb"] and self._payload_reconstructs(o)', 'if o is not None: return up not in st["amb"]')]
T = ["tests/trk_stage_a/test_r23_core.py", "tests/trk_stage_a/test_r22_construction_binding.py", "tests/trk_stage_a/test_r20_terminal_scope.py", "tests/trk_stage_a/test_r22_boundaries.py"]
def run():
    try: return subprocess.run([sys.executable, "-B", "-m", "pytest", "-q", "-x", *[str(ROOT / t) for t in T]], cwd=ROOT, capture_output=True, text=True, timeout=90, env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1")).returncode
    except subprocess.TimeoutExpired: return 99
def apply_multi(entries):
    saved = {}
    try:
        for rel, old, new in entries:
            p = ROOT / rel; saved.setdefault(rel, p.read_text()); cur = p.read_text()
            if cur.count(old) != 1: return None
            p.write_text(cur.replace(old, new))
        return run() != 0
    finally:
        for rel, txt in saved.items(): (ROOT / rel).write_text(txt)
MULTI = [("epoch witness: latest-invalidation marker AND basis (mutually redundant defences; removing both must fail)",
          [(TC, 'seen.add(d); st["inval"][d] = (b["key"], r.seq);', 'seen.add(d); st["inval"].setdefault(d, (b["key"], r.seq));'), (TC, ' or h["basis"] != self._basis(st, key): raise Refusal(key, code="NO_FRESH_WITNESS")', ': raise Refusal(key, code="NO_FRESH_WITNESS")')]),
         ("health: epoch basis AND reverify marker (mutually redundant for epoch changes; removing both must fail)",
          [(TC, '        if h["basis"] != self._basis(st, subject): return "UNKNOWN"', '        pass'), (TC, '        if st["reverify"].get(subject, 0) >= h["seq"]: return "UNKNOWN"', '        pass')])]
def main():
    assert run() == 0; bad = []
    for rel, old, new in M:
        p = ROOT / rel; s = p.read_text()
        if s.count(old) != 1: print("NOT APPLICABLE", old[:60].replace("\n", " ")); bad.append(old); continue
        try: p.write_text(s.replace(old, new)); k = run() != 0
        finally: p.write_text(s)
        print("killed  " if k else "SURVIVED", old[:70].replace("\n", " ")); k or bad.append(old)
    for name, ents in MULTI:
        k = apply_multi(ents); print("killed  " if k else "SURVIVED", name); k or bad.append(name)
    print("mutants: %d (+%d combined), survived/unapplied: %d" % (len(M), len(MULTI), len(bad))); assert run() == 0; return 1 if bad else 0
if __name__ == "__main__": sys.exit(main())
