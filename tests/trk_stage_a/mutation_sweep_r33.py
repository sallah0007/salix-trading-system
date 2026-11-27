"""R33 mutants for code changed in R32/R33 (order-read detach, resolved manifest, six joins incl. correlation/reverse J1/family map, FW10 descriptor reader, triggered pass slots). Author-run; a survivor is a finding. Not run by CI. Named behavioural equivalents (kept, not killable): the J3 competing-field early refusal (the following exact-shape check yields the same MISMATCH status; only the detail text differs) and `Descriptor(..., not held)`; R34: the `feature_key` equality in the accepted-record binding and the accepted-record identity pre-check in `reverify_accepted` duplicate the verifier's `expect_scope_key` check and the journal replay's namespace/version lookup (three slots are always held, so `complete` is False either way)."""
import subprocess, sys, pathlib, os
ROOT = pathlib.Path(__file__).resolve().parents[2]
CL = "tracker_component/claims.py"; SJ = "stage_a/ml/six_joins.py"; DB = "stage_a/fw/descriptor_binding.py"; RS = "stage_a/tracker/reverify_scheduler.py"; RV = "stage_a/tracker/reverification.py"; PL = "stage_a/tracker/pipeline.py"; TC = "stage_a/core/tracker_core.py"
M = [
 (CL, "order = ConstructionOrder.from_body(copy.deepcopy(raw))", "order = ConstructionOrder.from_body(raw)"),
 (CL, "return None if o is None else copy.deepcopy(o)", "return None if o is None else o"),
 (CL, "return [copy.deepcopy(x) for x in self._p.order_prov.get(order_id, [])]", "return list(self._p.order_prov.get(order_id, []))"),
 (TC, '"registry_basis": [list(x) for x in self._timeframes.basis()], "state": r.state, "entries": ents,', '"registry_basis": [list(x) for x in self._timeframes.basis()], "state": r.state,'),
 (TC, '"supplied_unadmitted": ["watermarks", "parent_completeness", "segmentation"]}', '"supplied_unadmitted": []}'),
 (SJ, 'same = (j4.get("manifest_id"), j4.get("manifest_hash")) == (j5.get("manifest_id"), j5.get("manifest_hash"))', "same = True"),
 (SJ, 'elif consumer_binding_id is not None and consumer_binding_id != j["binding_id"]:', "elif False:"),
 (SJ, 'dataset_manifests.get(j["dataset_manifest_id"]) != j["dataset_manifest_hash"]:', 'dataset_manifests.get(j["dataset_manifest_id"]) == j["dataset_manifest_hash"]:'),
 (SJ, 'elif consumer_binding_id is not None and binding_to_manifest is not None and dataset_manifests is not None: add(JOINS[0], VERIFIED_AGAINST_REGISTRY', 'elif True: add(JOINS[0], VERIFIED_AGAINST_REGISTRY'),
 (SJ, 'len(binding_to_manifest.get(consumer_binding_id, [])) != 1 or', ''),
 (SJ, 'binding_to_manifest[consumer_binding_id][0] != j["dataset_manifest_id"]', 'False'),
 (SJ, 'elif binding_to_manifest is not None and (consumer_binding_id is None or', 'elif False and (consumer_binding_id is None or'),
 (RV, 'r.get("materialization_hash") == body["materialization_hash"] and r.get("feature_key") == feature_key.key() and r.get("feature_version") == feature_key.feature_version', 'True'),
 (RV, 'r.get("materialization_hash") == body["materialization_hash"] and', ''),
 (RV, 'and r.get("feature_key") == feature_key.key() and', 'and'),
 (RV, 'declared = {"manifest_hash": body["manifest_hash"], "graph_hash": body["graph_hash"], "program_hash": body["program_hash"]}', 'declared = {"manifest_hash": "0" * 64, "graph_hash": body["graph_hash"], "program_hash": body["program_hash"]}'),
 (RV, 'if st is None: raise Refusal(feature_key.key(), code="NO_ACCEPTED_RECORD")', 'if st is None: st = None'),
 (RV, 'if (body["feature_key"], body["feature_version"]) != (feature_key.key(), feature_key.feature_version): raise', 'if False: raise'),
 (PL, 'if not self._store.put_if_absent(mk, mb):', 'if False:'),
 (PL, '"materialization_hash": rec["materialization_hash"]}', '"materialization_hash": rec["materialization_hash"][::-1]}'),
 (RS, 'if isinstance(b, AcceptedBinding):', 'if False:'),
 (SJ, '(hypothesis_family_id is None or family_map.get(hypothesis_family_id) != j["family_ref"])', "False"),
 (SJ, 'elif j["consulted_available_asof"] >= fence:', 'elif j["consulted_available_asof"] > fence:'),
 (SJ, "ok = sn is not None and sn == request_snapshot and isinstance(j4, dict)", "ok = sn is not None and isinstance(j4, dict)"),
 (SJ, "(sn.manifest_id, sn.manifest_hash) == (j4.get(\"manifest_id\"), j4.get(\"manifest_hash\"))", "True"),
 (SJ, 'or j["epoch"] > registry.epoch or', "or"),
 (SJ, 'if isinstance(j, dict) and ("ML_LOCAL_STATE" in j or "EVIDENCE_REFS" in j):', "if False:"),
 (SJ, "not any(s in (MISSING, MISMATCH) for _, s, _ in list(out) + corr)", "not any(s in (MISSING, MISMATCH) for _, s, _ in out)"),
 (DB, "if k in NEVER_A_SUBSTITUTE or (isinstance(k, str) and k.upper() in NEVER_A_SUBSTITUTE): raise", "if False: raise"),
 (DB, 'if st == MISSING_EXACT_SOURCE_MAPPING: held[f] = "EXACT_SOURCE_MAPPING_UNBOUND"; continue', "if False: pass"),
 (DB, 'if st == INTERNAL_DERIVATION_UNBOUND: held[f] = "FW_OWNED_INTERNAL_DERIVATION_UNBOUND"; continue', "if False: pass"),
 (DB, "[0] >= vals[\"DEPENDENCY_INTERVAL_END\"][0]: raise", "[0] > vals[\"DEPENDENCY_INTERVAL_END\"][0]: raise"),
 (DB, "return Descriptor(vals, held, False)", "return Descriptor(vals, held, not held)"),
 (RS, "if not (isinstance(v, dict) and set(v) == {\"value\", \"source_ref\"}", "if not (isinstance(v, dict)"),
 (RS, 'isinstance(v["source_ref"], str) and v["source_ref"])', "True)"),
 (RS, 'if not (type(c) is int and c >= 0): out.append(PassItem(sub, work[sub], "SKIPPED_COST_UNKNOWN")); continue', "c = c or 0"),
 (RS, "if spent + c > sl[\"max_cost\"][\"value\"]:", "if False:"),
 (RS, 'if n >= sl["max_items"]["value"]:', "if False:"),
 (RS, "if sub not in work or (work[sub] is None): work[sub] = trig", "work[sub] = trig"),
 (RS, 'if set(slots) - set(SLOT_NAMES): raise', "if False: raise"),
]
T = ["tests/trk_stage_a/test_r32_six_joins.py", "tests/trk_stage_a/test_r32_descriptor.py", "tests/trk_stage_a/test_r25_scheduler.py", "tests/trk_stage_a/test_r31_order_lifecycle.py", "tests/trk_stage_a/test_r26_snapshot.py", "tests/trk_stage_a/test_r29_intake_order.py", "tests/trk_stage_a/test_r33_composed.py"]
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
