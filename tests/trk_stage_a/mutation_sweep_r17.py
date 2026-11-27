"""R17 mutants (ORDER_READY outcome-access declaration, order binding, unverified labels, feature lineage). Run: python3 -B tests/trk_stage_a/mutation_sweep_r17.py (60 s per-mutant timeout)"""
import subprocess, sys, pathlib, os
ROOT = pathlib.Path(__file__).resolve().parents[2]
RR = "stage_a/composer/request_record.py"; BO = "stage_a/tracker/build_output_check.py"; QI = "stage_a/tracker/quant_intake_adapter.py"; PL = "stage_a/tracker/pipeline.py"; FL = "stage_a/tracker/feature_lineage.py"
M = [(RR, 'if rec.get("OUTCOME_INFORMATION_ACCESS") is None: raise', 'if False: raise'),
     (RR, 'if rec["OUTCOME_INFORMATION_ACCESS"] not in OUTCOME_ACCESS_VALUES: raise', 'if False: raise'),
     (RR, '"PERMITTED_UNDER_DECLARED_FITTING_CONTRACT")\n\ndef _text', '"PERMITTED_UNDER_DECLARED_FITTING_CONTRACT", "OTHER")\n\ndef _text'),
     (RR, '        _text(rec, "PURPOSE_STATEMENT", "REQUEST_PURPOSE_STATEMENT_MISSING")\n        if rec.get("OUT', '        _text(rec, "PURPOSE_STATEMENT", "REQUEST_PURPOSE_STATEMENT_MISSING")\n        if stage == "X" and rec.get("OUT'),
     (BO, '    if order_declaration not in ("FORBIDDEN", "PERMITTED_UNDER_DECLARED_FITTING_CONTRACT"):', '    if False:'),
     (BO, '    if d is None:\n        raise Refusal("OUTCOME_INFORMATION_ACCESS", code="BUILD_OUTPUT', '    if False:\n        raise Refusal("OUTCOME_INFORMATION_ACCESS", code="BUILD_OUTPUT'),
     (BO, '    if d != order_declaration:', '    if False:'),
     (BO, '    if order_declaration != "FORBIDDEN":\n        raise', '    if False:\n        raise'),
     (BO, '    if evidence is not None and not isinstance(evidence, ConformanceEvidence):', '    if False:'),
     (BO, 'check_outcome_access("FORBIDDEN", None if evidence is None else evidence.outcome_access_consulted)', 'pass'),
     (QI, '(pkg.request_record or {}).get("OUTCOME_INFORMATION_ACCESS"))', '(pkg.build_output or {}).get("OUTCOME_INFORMATION_ACCESS"))'),
     (QI, '        a.unverified.append(("CAPABILITY_CLASS_STRUCTURE", "NOT_VERIFIED_NO_SOURCE_COMPATIBILITY_RULE"))', '        pass'),
     (QI, '"NOT_VERIFIED_NO_SOURCE_COMPATIBILITY_RULE"', '"VERIFIED"'),
     (PL, '+ (("S28_FULL_CONFORMANCE", "NOT_ASSESSED_BOUNDARY"),)', '+ ()'),
     (PL, 'tuple(u for u in getattr(self.admission, "unverified", ()) if u[0] not in done)', '()'),
     (FL, '    if not ft:\n', '    if False:\n'),
     (FL, '        if not isinstance(m, QuantManifest):', '        if False:'),
     (FL, '                if ref.target_id == m.feature_id:', '                if False:'),
     (FL, '            if ref.ref_type in ft:', '            if True:'),
     (FL, 'own = deps.setdefault(m.feature_id, set())', 'own = set()'),
     (FL, 'tuple(sorted(d))', 'tuple(d)')]
T = ["tests/trk_stage_a/test_r16_conformance_wiring.py", "tests/trk_stage_a/test_r17_feature_lineage.py", "tests/trk_stage_a/test_r10_replica_roles.py", "tests/trk_stage_a/test_r11_intake_request.py", "tests/trk_stage_a/test_r13_build_output.py", "tests/trk_stage_a/test_pipeline.py"]
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
