"""R28 mutants for code changed in R27/R28 defects 1-4 (scope keys, snapshot currentness at use, verifier-run receipts, delivered-entry owner/independent verification). Author-run; a survivor is a finding.
Known equivalent (NOT killable by behaviour): replacing the independent composition call with the producer composition is behaviourally identical when both are correct - independence is structural, proven by the two-implementation equality tests, not by this sweep."""
import subprocess, sys, pathlib, os
ROOT = pathlib.Path(__file__).resolve().parents[2]
TC = "stage_a/core/tracker_core.py"; VR = "stage_a/tracker/verification/verification_result.py"; GC = "stage_a/gateway/contracts.py"; GB = "stage_a/gateway/binding.py"; MLR = "stage_a/ml/receiver.py"; FWR = "stage_a/fw/receiver.py"; CLS = "stage_a/ml/closure.py"; H3 = "stage_a/gateway/outcome_series.py"
M = [
 (TC, 'return json.dumps(list(parts), separators=(",", ":"), ensure_ascii=True)', 'return "|".join(",".join(x) if isinstance(x, list) else x for x in parts)'),
 (TC, 'if not self.confirm_snapshot(snap) or not _int(use_at) or use_at < snap.evaluated_at: return False', 'if False: return False'),
 (TC, 'return self._current_ok(st, snap.subject, snap.version, use_at, snap.require_authority_evidence, snap.require_transform_proof)', 'return True'),
 (TC, 'return self._current_ok(st, snap.subject, snap.version, use_at, snap.require_authority_evidence, snap.require_transform_proof)', 'return self._current_ok(st, snap.subject, snap.version, snap.evaluated_at, snap.require_authority_evidence, snap.require_transform_proof)'),
 (TC, 'snap.held_reason, snap.require_authority_evidence, snap.require_transform_proof) != snap.snapshot_id', 'snap.held_reason) != snap.snapshot_id' ),
 (TC, 'if not issued_by_verifier_run(result): raise', 'if False: raise'),
 (GC, 'if type(health) is CoreHealthSnapshot and not self.health_source.snapshot_current_at_use(health, fence):', 'if False:'),
 (GC, 'd = B.build_delivered_entry(row, st.status, health.resolution_ref, health.resolved_at)', 'd = B.build_delivered_entry(row, "CURRENT", health.resolution_ref, health.resolved_at)'),
 (VR, 'return isinstance(result, VerificationResult) and result.result_hash in _RECEIPTS and result_is_self_consistent(result)', 'return isinstance(result, VerificationResult)'),
 (VR, 'return isinstance(result, VerificationResult) and result.result_hash in _RECEIPTS and result_is_self_consistent(result)', 'return isinstance(result, VerificationResult) and result.result_hash in _RECEIPTS'),
 (GB, 'if h != claimed_hash: raise Refusal("hash", code="HASH_MISMATCH")', 'pass'),
 (GB, 'if tuple(entry.__dataclass_fields__) != ANNEX_XII_FIELDS: raise', 'if False: raise'),
 (GB, 'if type(entry) is not DeliveredFeatureEntry: raise', 'if False: raise'),
 (GB, 'except (ValueError, TypeError, KeyError, AttributeError) as e: raise Refusal(str(e), code="DELIVERED_ENTRY_NOT_INDEPENDENTLY_COMPOSABLE")', 'except (ValueError, TypeError, KeyError, AttributeError) as e: return'),
 (GB, 'if t is None or sym not in t: raise', 'if False: raise'),
 (MLR, 'elif not allow_unverified_hash: raise', 'elif False: raise'),
 (MLR, 'verify_delivered(tables, o.entry, o.delivered_feature_hash)', 'pass'),
 (FWR, 'verify_delivered(tables, e, binding.delivered_feature_hash)', 'pass'),
 (CLS, 'if e.edge_class == "FW_PREDICTIVE_EDGE" or e.parent in r.fw_taint_source_ids: taint = True', 'if e.edge_class == "FW_PREDICTIVE_EDGE": taint = True'),
 (CLS, 'if e.edge_class == "FW_PREDICTIVE_EDGE" or e.parent in r.fw_taint_source_ids: taint = True', 'if e.parent in r.fw_taint_source_ids: taint = True'),
 (CLS, 'if not e.content_carrying: continue', 'pass'),
 (CLS, 'if not r.closure_complete: reasons.append("CLOSURE_COMPLETE_FALSE")', 'pass'),
 (CLS, 'if r.missing_required_edges: reasons.append("MISSING_REQUIRED_EDGES_PRESENT")', 'pass'),
 (CLS, 'if r.unresolved_edges: reasons.append("UNRESOLVED_EDGES_PRESENT")', 'pass'),
 (CLS, 'if r.unknown_edge_types: reasons.append("UNKNOWN_EDGE_TYPES_PRESENT")', 'pass'),
 (CLS, 'if e.parent not in nodes or e.child not in nodes: reasons.append("EDGE_ENDPOINT_NOT_IN_NODE_SET"); continue', 'pass'),
 (CLS, 'if e.edge_class == "UNKNOWN" or e.edge_class not in EDGE_CLASSES: reasons.append("UNKNOWN_EDGE_TYPE_ON_REQUIRED_PATH"); continue', 'pass'),
 (CLS, 'if taint and not r.fw_taint_present: reasons.append("FW_TAINT_UNDECLARED")', 'pass'),
 (CLS, 'if r.fw_taint_present and not r.fw_taint_source_ids: raise', 'if False: raise'),
 (MLR, 'if v.verdict != "PASS": raise Refusal(",".join(v.reasons), code="ML_STANDALONE_CLOSURE_FAIL_CLOSED")', 'pass'),
 (MLR, 'if closure.subject_id != m.manifest_id: raise', 'if False: raise'),
 (H3, 'if not _covered(s, e, segs): w.append("INTERVAL_OUTSIDE_AUTHORIZED_SEGMENTS")', 'pass'),
 (H3, 'if s > cur: break', 'pass'),
 (H3, 'if any(s <= se and hs <= e for hs, se in sealed) and not _s(pkg.holdout_unseal_event_ref): w.append("SEALED_HOLDOUT_WITHOUT_UNSEAL_EVENT_REF")', 'pass'),
 (H3, 'if any(s <= se and hs <= e for hs, se in sealed) and not _s(pkg.holdout_unseal_event_ref): w.append("SEALED_HOLDOUT_WITHOUT_UNSEAL_EVENT_REF")', 'if any(s <= se and hs <= e for hs, se in sealed) and False: w.append("SEALED_HOLDOUT_WITHOUT_UNSEAL_EVENT_REF")'),
 (H3, 'if getattr(ctx, flag) and not _s(getattr(pkg, ref)): w.append("MISSING_CONDITIONAL:" + ref)', 'pass'),
 (H3, 'pkg.available_asof >= pkg.delivery_decision_ts', 'pkg.available_asof > pkg.delivery_decision_ts'),
 (H3, 'if not _s(getattr(pkg, f)): w.append("MISSING_REQUIRED:" + f)', 'pass'),
 (FWR, 'return require_delivery(pkg, ctx)', 'return None'),
]
T = ["tests/trk_stage_a/test_r25_defects.py", "tests/trk_stage_a/test_r26_evidence_truth.py", "tests/trk_stage_a/test_r27_binding.py", "tests/trk_stage_a/test_boundaries.py", "tests/trk_stage_a/test_r24_core.py", "tests/trk_stage_a/test_r25_scheduler.py", "tests/trk_stage_a/test_r28_closure.py", "tests/trk_stage_a/test_r28_h3.py"]
def run():
    try: return subprocess.run([sys.executable, "-B", "-m", "pytest", "-q", "-x", *[str(ROOT / t) for t in T]], cwd=ROOT, capture_output=True, text=True, timeout=120, env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1")).returncode
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
