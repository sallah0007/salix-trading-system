"""NOTE (R20): the blast_radius entries below reference the removed `upstream_incomplete` and are SUPERSEDED by mutation_sweep_r20.py; do not rerun them as current evidence.
R18 mutants (Health consumer-specific incompleteness, graph-key binding). Run: python3 -B tests/trk_stage_a/mutation_sweep_r18.py (60 s per mutant)"""
import subprocess, sys, pathlib, os
ROOT = pathlib.Path(__file__).resolve().parents[2]
BR = "stage_a/health/blast_radius.py"; LN = "stage_a/fw/lanes.py"; QI = "stage_a/tracker/quant_intake_adapter.py"; PL = "stage_a/tracker/pipeline.py"; ML = "stage_a/ml/receiver.py"; VR = "stage_a/tracker/version_relationship.py"
M = [(BR, "            incomplete = features_incomplete\n            if closure_features is not None:", "            incomplete = features_incomplete\n            if False:"),                 # global incomplete flag always used: the reproduced over-blocking
     (BR, "incomplete = upstream_incomplete(closure_features(m, consumers), failed, feature_deps, unread_features)", "incomplete = features_incomplete"),
     (BR, "        if n in unread or n not in feature_deps:", "        if n in unread:"),
     (BR, "        if n in unread or n not in feature_deps:", "        if n not in feature_deps:"),
     (BR, "        if n in seen or n == failed:", "        if n in seen:"),
     (BR, "        stack.extend(feature_deps[n])", "        pass"),
     (BR, '        if getattr(m, "manifest_id", cid) != cid:', "        if False:"),
     (BR, "                except Refusal as e:\n                    out[cid] = CarriedUpstreamImpact(cid, UNDETERMINED, failed, (), e.code); continue", "                except Refusal as e:\n                    incomplete = False"),
     (LN, "        if nxt.manifest_id != cur.derived_from:\n            raise Refusal(cur.derived_from, code=\"GRAPH_KEY_MISMATCH\")            # a misbound", "        if False:\n            raise Refusal(cur.derived_from, code=\"GRAPH_KEY_MISMATCH\")            # a misbound"),
     (LN, "        if nxt.manifest_id != cur.derived_from:\n            raise Refusal(cur.derived_from, code=\"GRAPH_KEY_MISMATCH\")\n        cur = nxt\n    return out", "        if False:\n            raise Refusal(cur.derived_from, code=\"GRAPH_KEY_MISMATCH\")\n        cur = nxt\n    return out"),
     (LN, "        out.update(cur.dependency_feature_ids); out.update(cur.artifact_closure_features)", "        out.update(cur.dependency_feature_ids)"),
     (LN, "        out.update(cur.dependency_feature_ids); out.update(cur.artifact_closure_features)", "        out.update(cur.artifact_closure_features)"),
     (PL, "        if held:                                              # Parent", "        if False:                                              # Parent"),
     (PL, "        held = unresolved_mandatory(adm, duty_ev)", "        held = []"),
     (PL, "duty_ev = None if self._duty_source is None else self._duty_source(pkg, adm)", "duty_ev = SIM"),
     (PL, "if u[0] not in done)", "if True)"),
     (PL, "accepted=accepted, authority_ref=ref, duty_evidence=duty_ev)", "accepted=accepted, authority_ref=ref)"),
     (QI, "    verified = evidence.duties if isinstance(evidence, DutyEvidence) else frozenset()", "    verified = evidence.duties if evidence is not None else frozenset()"),
     (QI, "if d in MANDATORY_UNVERIFIED_DUTIES and d not in verified]", "if d in MANDATORY_UNVERIFIED_DUTIES]"),
     (QI, "if d in MANDATORY_UNVERIFIED_DUTIES and d not in verified]", "if d not in verified]"),
     (QI, "    if evidence is not None and not isinstance(evidence, DutyEvidence):\n        out.append", "    if False:\n        out.append"),
     (QI, "not isinstance(self.duties, frozenset) or not self.duties or", "not self.duties or"),
     (QI, "or not self.evidence_ref.strip():\n            raise Refusal(\"evidence_ref\", code=\"DUTY_EVIDENCE_WITHOUT_REF\")", "or False:\n            raise Refusal(\"evidence_ref\", code=\"DUTY_EVIDENCE_WITHOUT_REF\")"),
     (QI, '        a.unverified.append(("OUTCOME_ACCESS_DECLARATION_GOVERNED_BEFORE_BUILD", "NOT_VERIFIED_SUPPLIED_RECORD_STRUCTURAL_EQUALITY"))', "        pass"),
     (QI, '"CAPABILITY_CLASS_STRUCTURE", "OUTCOME_ACCESS_DECLARATION_GOVERNED_BEFORE_BUILD")\n\n@dataclass(frozen=True)\nclass DutyEvidence', '"CAPABILITY_CLASS_STRUCTURE",)\n\n@dataclass(frozen=True)\nclass DutyEvidence'),
     (ML, '"research_exposure_ref", "support_ref"):\n            v = getattr', '"research_exposure_ref"):\n            v = getattr'),
     (VR, '    if not admitted:\n', '    if False:\n'),
     (VR, "        if f in OUTSIDE_VERSION_CONTENT_DIFF:", "        if False:"),
     (VR, "        if d not in DIMENSIONS:", "        if False:"),
     (VR, "        if f in seen:", "        if False:"),
     (VR, "    if set(seen) - aset:", "    if False:"),
     (VR, "    if aset - set(seen):", "    if False:"),
     (VR, "        if f in seen and seen[f] != d:", "        if False:"),
     (VR, '"data_vintage": "PROVENANCE_SOURCE"', '"data_vintage": "CAUSAL_TIME"'),
     (VR, '"blocks_supersession_claim": True, "blocks_gateway_delivery_of_existing_eligible_version": False', '"blocks_supersession_claim": False, "blocks_gateway_delivery_of_existing_eligible_version": False'),
     (VR, '"blocks_supersession_claim": True, "blocks_gateway_delivery_of_existing_eligible_version": False', '"blocks_supersession_claim": True, "blocks_gateway_delivery_of_existing_eligible_version": True'),
     (VR, '"may_yield_correction": False, "routes_to"', '"may_yield_correction": True, "routes_to"'),
     (VR, '"routes_to": "MATERIAL_ALTERNATIVE"', '"routes_to": "CORRECTION"'),
     (LN, "        if cur.manifest_id in seen:\n            raise Refusal(cur.manifest_id, code=\"DERIVATION_CYCLE\")\n        seen.add(cur.manifest_id)\n        out.update", "        seen.add(cur.manifest_id)\n        out.update")]
T = ["tests/trk_stage_a/test_r12_blast_radius.py", "tests/trk_stage_a/test_r16_ml_ancestry.py", "tests/trk_stage_a/test_r18_mandatory_hold.py", "tests/trk_stage_a/test_r16_conformance_wiring.py", "tests/trk_stage_a/test_r12_ml_augmented.py", "tests/trk_stage_a/test_r18_version_relationship.py"]
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
