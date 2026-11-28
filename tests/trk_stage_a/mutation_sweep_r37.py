"""R37 mutants for code added/changed in R37 (dataset lineage namespaces, ML required non-delivery reason, generation payload freeze, FW CBID correlation, SIM publication path, stored-value L2, pipeline telemetry isolation, runner, version diff, registry semantics). Author-run. NAMED EQUIVALENT (not run): fw/outcome_desk.request `or rec.manifest_or_dataset_binding_id != identity.manifest_or_dataset_binding_id` - `register_consumer_binding` already refuses a record whose manifest binding id differs from the issued identity and request() has already proven `identity` is the issued one, so the second comparison is a defensive duplicate kept on purpose."""
import subprocess, sys, pathlib, os
ROOT = pathlib.Path(__file__).resolve().parents[2]
DA="stage_a/ml/dataset_authority.py"; RC="stage_a/ml/receiver.py"; GL="stage_a/ml/generation_lifecycle.py"; OD="stage_a/fw/outcome_desk.py"; SP="stage_a/tracker/sim_publication_path.py"; SV="stage_a/tracker/stored_values.py"; PL="stage_a/tracker/pipeline.py"; RN="stage_a/ops/runner.py"; VD="stage_a/tracker/version_diff.py"; RS="stage_a/tracker/registry_semantics.py"; GW="stage_a/gateway/contracts.py"; SPJ="stage_a/tracker/status_projection.py"
M = [
 (DA, 'if self._d.manifest(g) is not None or g in self._union: raise', "if False: raise"),
 (DA, 'if self._g is None or self._g.manifest_of(g) is None: raise Refusal(g, code="GENERATION_LINEAGE_KEY_UNKNOWN_GENERATION")', "pass"),
 (DA, "if amb: return", "if False: return"),
 (DA, 'if self._ambiguous(m): raise Refusal(m, code="UNION_NODE_ID_AMBIGUOUS")', "pass"),
 (RC, "if not _tagged_reason(why): raise", "if False: raise"),
 (RC, 'return all(isinstance(x, str) and x for x in v[1:])', "return True"),
 (RC, 'if not callable(exclusion_reason_for_missing): raise', "if False: raise"),
 (GL, "result = _freeze(result)", "pass"),
 (GL, "return MappingProxyType({k: _freeze(v, _depth + 1) for k, v in x.items()})", "return {k: _freeze(v, _depth + 1) for k, v in x.items()}"),
 (GL, "if type(x) in (list, tuple): return tuple(_freeze(i, _depth + 1) for i in x)", "if type(x) in (list, tuple): return x"),
 (OD, "if rec is None: raise", "if False: raise"),
 (OD, "if other is not None and other != rec.consumer_binding_id: raise", "if False: raise"),
 (OD, "or identity.manifest_or_dataset_binding_id != rec.manifest_or_dataset_binding_id: raise", ": raise"),
 (GW, 'if getattr(self.status, "simulation", False) and not self.allow_simulation_status:', "if False:"),
 (SPJ, 'if authority_class_of(journal) != SIMULATION: raise', "if False: raise"),
 (SP, "st.accepted_hash != b[\"accepted_hash\"] or ", ""),
 (SP, "or st.accepted_body[\"manifest_hash\"] != b[\"row\"][\"quant_manifest_hash\"]", ""),
 (SP, "if not isinstance(supplied, SuppliedRowInputs) or status_token not in self._spec[\"status_map\"] or", "if not isinstance(supplied, SuppliedRowInputs) or"),
 (SP, 'row = {"feature_version": feature_key.feature_version, "quant_manifest_hash": rb.manifest_hash}', 'row = {"feature_version": feature_key.feature_version, "quant_manifest_hash": "0" * 64}'),
 (SV, 'if rec.get("bindings") != {n: dict(bindings[n]) for n in sorted(bindings)}: return', "if False: return"),
 (SV, "same = rec[\"values\"] == v[\"recomputed\"]", "same = True"),
 (SV, 'if got is None: return dict(base, overall="UNAVAILABLE", reason="STORED_VALUES_ABSENT", l1="PASS", l2="UNAVAILABLE"', 'if got is None: return dict(base, overall="UNAVAILABLE", reason="STORED_VALUES_ABSENT", l1="PASS", l2="PASS"'),
 (SV, "rec.get(\"materialization_hash\") == body[\"materialization_hash\"] and ", ""),
 (SV, "if series_hash(list(v)) != bindings[n][\"hash\"]: raise", "if False: raise"),
 (PL, "        except Exception: self.sink_failures += 1", "        except Exception: raise"),
 (RN, "                if self._tries[k] >= self._max: self.dead[k]", "                if False: self.dead[k]"),
 (RN, "self._q.complete(k); self._emit(\"JOB_DONE\"", "self._emit(\"JOB_DONE\""),
 (RN, 'set(d) == set(_JOB_FIELDS) and', ''),
 (VD, "if dims == {\"PROVENANCE_SOURCE\"}: return", "if \"PROVENANCE_SOURCE\" in dims: return"),
 (VD, "defect_verifier(tuple(defect_evidence_refs)) is True", "defect_verifier(tuple(defect_evidence_refs))"),
 (VD, "semantic <= set(attributable_fields)", "True"),
 (VD, "if old != rel: raise", "if False: raise"),
 (VD, "k not in VR.OUTSIDE_VERSION_CONTENT_DIFF", "True"),
 (VD, "if any(v == UNVERIFIABLE for v in", "if False and any(v == UNVERIFIABLE for v in"),
 (RS, "return available_asof < snapshot_fence_ts", "return available_asof <= snapshot_fence_ts"),
 (RS, "if declared_policy_allows_mixed is not True: raise", "if False: raise"),
 (RS, "if any(p[1] > self.snapshot_fence_ts for p in w): raise", "if False: raise"),
 (RS, "if a[\"origin\"] == b[\"origin\"]: raise", "if False: raise"),
 (RS, "if nxt in chain: raise", "if False: raise"),
]
T = [f"tests/trk_stage_a/{f}" for f in ("test_r37_dataset_lineage.py", "test_r37_ml_required_nondelivery.py", "test_r37_generation_payload_frozen.py", "test_r36_outcome_desk.py", "test_r37_sim_publication_path.py", "test_r37_stored_values.py", "test_r37_json_sink_pipeline.py", "test_r37_runner.py", "test_r37_version_diff.py", "test_r37_registry_semantics.py", "test_r36_dataset_authority.py")]
def run():
    try: return subprocess.run([sys.executable, "-B", "-m", "pytest", "-q", "-x", *[str(ROOT / t) for t in T]], cwd=ROOT, capture_output=True, text=True, timeout=120, env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1")).returncode
    except subprocess.TimeoutExpired: return 99
def main():
    assert run() == 0; bad = []
    for rel, old, new in M:
        p = ROOT / rel; s = p.read_text()
        if s.count(old) != 1: print("NOT APPLICABLE", old[:70].replace("\n", " ")); bad.append(old); continue
        try: p.write_text(s.replace(old, new)); k = run() != 0
        finally: p.write_text(s)
        print("killed  " if k else "SURVIVED", old[:70].replace("\n", " ")); k or bad.append(old)
    print("mutants: %d, survived/unapplied: %d" % (len(M), len(bad))); assert run() == 0; return 1 if bad else 0
if __name__ == "__main__": sys.exit(main())
