"""R16 mutants (ML ancestry/augmented rebind, conformance wiring). Run: python3 -B tests/trk_stage_a/mutation_sweep_r16.py (60 s per-mutant timeout; hang = killed)"""
import subprocess, sys, pathlib, os
ROOT = pathlib.Path(__file__).resolve().parents[2]
ML = "stage_a/ml/receiver.py"; BO = "stage_a/tracker/build_output_check.py"; QI = "stage_a/tracker/quant_intake_adapter.py"; PL = "stage_a/tracker/pipeline.py"
M = [(ML, '    for anc in ancestry(m, graph):\n        if anc.kind == "FW":', '    for anc in ancestry(m, graph)[:1]:\n        if anc.kind == "FW":'),
     (ML, '        if anc.kind == "FW":', "        if False:"), (ML, '        if anc.kind != "ML":', "        if False:"),
     (ML, "        if nxt is None:\n            raise Refusal(cur.derived_from, code=\"DERIVED_FROM_UNRESOLVED\")\n        if nxt.manifest_id", "        if nxt is None:\n            pass\n        if nxt.manifest_id"),
     (ML, "        if nxt.manifest_id in seen:", "        if False:"), (ML, "        if nxt.manifest_id != cur.derived_from:", "        if False:"),
     (ML, '    if kind != "ML_STANDALONE":', "    if False:"), (ML, '    if m.kind != "ML":\n        raise Refusal(m.kind, code="STANDALONE_REQUIRES_ML_MANIFEST")', "    if False:\n        raise Refusal(m.kind, code=\"STANDALONE_REQUIRES_ML_MANIFEST\")"),
     (ML, "    if lane != BASELINE:", "    if False:"), (ML, "    ancestry(m, graph)                                             # unresolved", "    pass                                             # unresolved"),
     (ML, "    if gateway.outcome(aug.gateway_rebind.request_id) is not aug.gateway_rebind:", "    if False:"),
     (ML, '        return AugmentedCheck(lane, False, "UNVERIFIED_SHAPE_ONLY")', '        return AugmentedCheck(lane, True, "UNVERIFIED_SHAPE_ONLY")'),
     (ML, "    if not isinstance(chk, AugmentedCheck) or not chk.rebind_verified:", "    if False:"),
     (ML, '            if v is None:\n                raise Refusal(n, code="AUGMENTED_FIELD_MISSING")', '            if False:\n                raise Refusal(n, code="AUGMENTED_FIELD_MISSING")'),
     (ML, "            if not isinstance(v, Ref):", "            if False:"), (ML, "        if not isinstance(self.gateway_rebind, Binding) or", "        if False or"),
     (ML, '    if not isinstance(aug, AugmentedInput):\n        raise Refusal("rebind"', '    if False:\n        raise Refusal("rebind"'),
     (BO, '    check_outcome_access(bo.get("OUTCOME_INFORMATION_ACCESS"), None if evidence is None else evidence.outcome_access_consulted)', "    pass"),
     (BO, "        if consulted_by_verification is None:", "        if False:"), (BO, "        if consulted_by_verification is True:", "        if False:"),
     (BO, "    if evidence is not None and not isinstance(evidence, ConformanceEvidence):", "    if False:"),
     (BO, "        if not _present(self.evidence_ref):", "        if False:"), (BO, "        if self.outcome_access_consulted is not None and not isinstance(self.outcome_access_consulted, bool):", "        if False:"),
     (QI, "        check_conformance(pkg.build_output, conformance)", "        pass"), (QI, '        fail("BUILD_CONFORMANCE", e.code)', "        pass"),
     (PL, "conformance=None if self._conformance_source is None else self._conformance_source(pkg))", "conformance=None)")]
T = ["tests/trk_stage_a/test_r16_ml_ancestry.py", "tests/trk_stage_a/test_r12_ml_augmented.py", "tests/trk_stage_a/test_r16_conformance_wiring.py", "tests/trk_stage_a/test_boundaries.py", "tests/trk_stage_a/test_r13_build_output.py"]
def run():
    try: return subprocess.run([sys.executable, "-B", "-m", "pytest", "-q", "-x", *[str(ROOT / t) for t in T]], cwd=ROOT, capture_output=True, text=True, timeout=60, env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1")).returncode
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
