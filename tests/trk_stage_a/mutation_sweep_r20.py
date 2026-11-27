"""R20 mutants for the paths changed in R19/R20 only (Health mandatory probes + cyclic lineage, mandatory duties, no-quant hold/lineage, authority class, terminal identity, ML union closure).
Supersedes the Health entries of mutation_sweep_r18.py that referenced the removed `upstream_incomplete`. Unchanged earlier sweeps are not rerun. Run: python3 -B tests/trk_stage_a/mutation_sweep_r20.py (60 s per mutant)"""
import subprocess, sys, pathlib, os
ROOT = pathlib.Path(__file__).resolve().parents[2]
BR = "stage_a/health/blast_radius.py"; QI = "stage_a/tracker/quant_intake_adapter.py"; PL = "stage_a/tracker/pipeline.py"; ML = "stage_a/ml/receiver.py"; TI = "stage_a/tracker/terminal_identity.py"
AC = "stage_a/storage/authority_class.py"; PB = "stage_a/tracker/publication.py"; RM = "stage_a/storage/postgres_read_model.py"; SP = "stage_a/tracker/status_projection.py"; CL = "tracker_component/claims.py"
M = [(BR, 'if not callable(closure_contains_target) or not callable(closure_features):', 'if False:'),
     (BR, 'if not callable(closure_contains_target) or not callable(closure_features):', 'if not callable(closure_contains_target):'),
     (BR, '            if state.get(c) == 1:\n                return "FEATURE_LINEAGE_CYCLIC"', '            if False:\n                return "FEATURE_LINEAGE_CYCLIC"'),
     (BR, '        if root in unread or root not in feature_deps:', '        if root in unread:'),
     (BR, '            if c in unread or c not in feature_deps:', '            if c in unread:'),
     (BR, '        if root == failed or state.get(root) == 2:', '        if state.get(root) == 2:'),
     (BR, 'out[cid] = CarriedUpstreamImpact(cid, UNDETERMINED, failed, (), defect) if defect else', 'out[cid] = CarriedUpstreamImpact(cid, UNDETERMINED, failed, (), defect) if False else'),
     (QI, 'verified = evidence.duties if (simulation and isinstance(evidence, DutyEvidence)) else frozenset()', 'verified = evidence.duties if isinstance(evidence, DutyEvidence) else frozenset()'),
     (QI, 'if not simulation and not baseline_connected:', 'if False:'),
     (QI, 'if not simulation and not baseline_connected:', 'if not baseline_connected:'),
     (PL, 'duty_evidence=duty_ev, simulation=self._simulation)', 'duty_evidence=duty_ev)'),
     (PL, '            if lineage:                                       # a caller flag', '            if False:                                       # a caller flag'),
     (PL, '            if not self._simulation:\n                # QUALIFIED', '            if False:\n                # QUALIFIED'),
     (PL, '            if authority_class_of(obj) != want:', '            if False:'),
     (PL, 'scope=("ERA_1", adm.definition.instrument, adm.definition.timeframe)', 'scope=None'),
     (CL, '        if order_id in self._p.orders:', '        if False:'),
     (CL, '        if request_id and request_id in self._p.request_claim:', '        if False:'),
     (AC, 'return self._i.get(_PREFIX + key)', 'return self._i.get(key)'),
     (AC, '        if authority_class_of(inner) != QUALIFIED or isinstance(inner, SimulationStore):', '        if False:'),
     (AC, '    if c not in (QUALIFIED, SIMULATION):', '    if False:'),
     (PB, 'require_qualified(journal, "publication")', 'pass'),
     (RM, 'require_qualified(journal, "read-model rebuild")', 'pass'),
     (RM, 'require_qualified(journal, "read-model status")', 'pass'),
     (RM, 'require_qualified(journal, "read-model verify")', 'pass'),
     (SP, 'require_qualified(journal, "chain-status projection")', 'pass'),
     (TI, 'if identity_scope(r) == sc}', 'if True}'),
     (TI, 'if len(cands) > 1:', 'if False:'),
     (TI, 'CROSS_SCOPE if same_id else ORPHAN', 'ORPHAN'),
     (TI, 'for r in sorted(recs, key=full_facts):', 'for r in recs:'),
     (TI, 'if (sid, sc) in seen:', 'if sid in seen and False:'),
     (TI, 'if not any(str(e).startswith("UNRESOLVED_CANONICAL_SURVIVOR:")', 'if False and not any(str(e).startswith("UNRESOLVED_CANONICAL_SURVIVOR:")'),
     (TI, 'if (r.canonical_survivor, identity_scope(r)) in cur:', 'if False:'),
     (ML, '            if cls != CONTENT_CARRYING:', '            if False:'),
     (ML, '            if cls == ADMINISTRATIVE_ONLY:', '            if False:'),
     (ML, '            if parent in taint:', '            if False:'),
     (ML, '            if parent not in seen:', '            if True:'),
     (ML, '        if not (isinstance(e, tuple) and len(e) == 3):', '        if False:'),
     (ML, '    raise Refusal(getattr(chk, "union_closure", type(chk).__name__), code="UNION_CLOSURE_COMPLETENESS_UNPROVEN")', '    return "QUALIFIED"')]
T = ["tests/trk_stage_a/test_r12_blast_radius.py", "tests/trk_stage_a/test_r18_mandatory_hold.py", "tests/trk_stage_a/test_r19_qualified_acceptance.py", "tests/trk_stage_a/test_r19_terminal_identity.py",
     "tests/trk_stage_a/test_r19_union_closure.py", "tests/trk_stage_a/test_r20_simulation_boundary.py", "tests/trk_stage_a/test_r20_terminal_scope.py", "tests/trk_stage_a/test_pipeline.py"]
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
