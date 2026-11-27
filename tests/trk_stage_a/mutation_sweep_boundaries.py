"""Protection-disabled mutants for the Annex-verifier / status / speculation / Gateway / FW / ML / lanes / Health modules.
Each mutant must make tests/trk_stage_a/test_boundaries.py FAIL. Run: python3 tests/trk_stage_a/mutation_sweep_boundaries.py"""
import subprocess, sys, pathlib
ROOT = pathlib.Path(__file__).resolve().parents[2]
M = [
 ("gateway/v038.py", "with self._lock:\n            bound = self._req_ids.get(request_id)", "if True:\n            bound = self._req_ids.get(request_id)"),
 ("gateway/v038.py", "if identity in self._inflight:", "if False:"),
 ("gateway/v038.py", "if out is None:", "if False:"),
 ("gateway/v038.py", "self._inflight.discard(identity)", "pass"),
 ("schema/independent.py", "raise ValueError(\"unknown tag\")", "return b\"\\x02\" + _ref(v[1])"),
 ("schema/independent.py", "if type(code) is not int or code not in table.values():", "if type(code) is not int:"),
 ("schema/independent.py", "if table is None: raise", "if False: raise"),
 ("schema/independent.py", "if \"refit_mode_is_scheduled\" in m and m[\"refit_mode_is_scheduled\"] is not sched:", "if False:"),
 ("schema/independent.py", "if (r[\"speculation_mode\"] == _sym(enums, \"SPECULATION_MODE\", \"GATED_ONE_STEP\"))", "if (r[\"speculation_mode\"] == 2)"),
 ("context/news_hub_v2.py", "if publicly_available_at is None or salix_received_at is None:", "if False:"),
 ("context/news_hub_v2.py", "if asof > decision_cutoff:", "if False:"),
 ("context/news_hub_v2.py", 'if pres == "NO_EVENT_RECORDED" and cov != "COMPLETE":', "if False:"),
 ("context/news_hub_v2.py", 'if cov == "COMPLETE" and coverage_basis is None:', "if False:"),
 ("context/news_hub_v2.py", "if not ok:", "if False:"),
 ("context/news_hub_v2.py", "prior_coverage_issued_at <= decision_cutoff", "prior_coverage_issued_at <= decision_cutoff + 9"),
 ("context/news_hub_v2.py", "if degraded and optional_degraded_policy_ref is None:", "if False:"),
 ("context/news_hub_v2.py", "return bar_or_decision_time >= issued_at", "return True"),
 ("context/decision_context.py", 'if "NEXT_PERMITTED_ACTION" in o:', "if False:"),
 ("context/decision_context.py", "if o[\"CONTEXT_DOMAIN\"] not in DOMAINS:", "if False:"),
 ("context/decision_context.py", "if not context_known:", "if False:"),
 ("context/decision_context.py", "return e[\"CREATED_AT\"] <= t and e[\"AVAILABLE_ASOF\"] <= t", "return e[\"EFFECTIVE_AT\"] <= t"),
 ("context/decision_context.py", "return dict(apply=True, review=\"CONTEXT_DOMAIN_RESOLUTION_FAILURE\"", "return dict(apply=False, review=\"CONTEXT_DOMAIN_RESOLUTION_FAILURE\""),
 ("context/decision_context.py", "restoration_allowed=False)", "restoration_allowed=True)"),
 ("context/decision_context.py", "if not risk_reducing:\n        if not domain_resolvable:", "if not risk_reducing:\n        if False:"),
 ("schema/independent.py", 'if m["shared_evaluator_operator_set_version"] != "SQE_OPSET_V1_1":', "if False:"),
 ("schema/independent.py", 'if sched != (m["refit_rule_ref"] is not None) or sched != (m["parameter_generation_source_ref"] is not None):', "if False:"),
 ("schema/independent.py", 'if not pairs: raise ValueError("empty")', "if False: pass"),
 ("schema/independent.py", 'if len({k for k, _ in enc}) != len(enc): raise ValueError("dup")\n        return _lst([e for _, e in enc], lambda b: b)\n    if not', 'if False: pass\n        return _lst([e for _, e in enc], lambda b: b)\n    if not'),
 ("schema/independent.py", "if not ops or ops != sorted(set(ops)): raise ValueError(\"opcodes\")", "if False: pass"),
 ("schema/independent.py", "caps.sort(key=lambda p: p[0])", "pass"),
 ("schema/independent.py", "for k, r in pairs), key=lambda p: p[0])\n        if len", "for k, r in pairs), key=lambda p: 0)\n        if len"),
 ("gateway/v038.py", "if self.status not in NON_DELIVERY_STATUSES:", "if False:"),
 ("gateway/v038.py", "if self.status == NOT_READY and not self.omissions:", "if False:"),
 ("gateway/v038.py", "if self.expected_key.feature_version != self.feature_version:", "if False:"),
 ("gateway/v038.py", "if not isinstance(self.expected_key, ExpectedDependencyKey):", "if False:"),
 ("gateway/v038.py", "if certified_max_visibility_lag is None:", "if False:"),
 ("gateway/v038.py", "if settlement_delay < certified_max_visibility_lag:", "if False:"),
 ("gateway/v038.py", "if resolution_time < fence + settlement_delay:", "if False:"),
 ("gateway/v038.py", "if available_asof >= fence:", "if available_asof > fence:"),
 ("gateway/v038.py", "if publish_log_position > watermark.status_log_position:", "if publish_log_position >= watermark.status_log_position:"),
 ("gateway/v038.py", "if bound is not None and bound != identity:", "if False:"),
 ("gateway/v038.py", "if identity in self._by_identity:\n                self._req_ids", "if False:\n                self._req_ids"),
 ("gateway/v038.py", "if identity in self._by_identity:\n                raise", "if False:\n                raise"),
 ("gateway/v038.py", "if missing:", "if False:"),
 ("gateway/v038.py", "if fields[\"PACKAGE_CLASS\"] not in", "if False and fields[\"PACKAGE_CLASS\"] not in"),
 ("gateway/v038.py", "return NOT_READY\n    return REJECTED", "return NOT_READY\n    return NOT_READY"),
 ("tracker/chain_status.py", "if prev.status == HALTED:", "if False:"),
 ("tracker/chain_status.py", "if f.sequence <= prev.sequence:", "if False:"),
 ("tracker/chain_status.py", "if f.available_asof < prev.available_asof:", "if False:"),
 ("tracker/chain_status.py", "if prev.correction_marked and not f.correction_marked:", "if False:"),
 ("tracker/chain_status.py", "if f.correction_marked and f.status == CURRENT:", "if False:"),
 ("tracker/chain_status.py", "and f.status == CURRENT and not f.tracker_designated:", "and f.status == CURRENT and False:"),
 ("tracker/chain_status.py", "e.available_asof < fence", "e.available_asof <= fence"),
 ("tracker/speculation.py", "if src.transitive_speculation_depth != 0 or not src.all_content_inputs_publishable:", "if False:"),
 ("tracker/speculation.py", "if c.staged_inputs and c.transitive_speculation_depth != 1:", "if False:"),
 ("tracker/speculation.py", "if c.transitive_speculation_depth not in (0, 1):", "if False:"),
 ("gateway/contracts.py", "if row.available_asof >= fence:", "if row.available_asof > fence:"),
 ("gateway/contracts.py", "if row.visible_at >= obs:", "if False:"),
 ("gateway/contracts.py", "if self.watermark < fence:", "if False:"),
 ("gateway/contracts.py", "if require_current and st.status != CURRENT:", "if False:"),
 ("gateway/contracts.py", "if not health.acceptable:", "if False:"),
 ("gateway/contracts.py", "if done is not None:", "if False:"),
 ("gateway/contracts.py", "if extra:", "if False:"),
 ("gateway/contracts.py", "if (self.requirement_class == OPTIONAL) != (self.absence_rule_ref is not None):", "if False:"),
 ("gateway/contracts.py", "if data_vintage_mode is not None and row.data_vintage_mode != data_vintage_mode:", "if False:"),
 ("gateway/contracts.py", "if st is None:", "if False:"),
 ("fw/receiver.py", "if O.delivered_hash(tables, e) != binding.delivered_feature_hash:", "if False:"),
 ("fw/receiver.py", "if e.instrument_id != instrument_id or e.timeframe_id != timeframe_id:", "if False:"),
 ("fw/receiver.py", "if require_current and e.chain_status_at_bind != \"CURRENT\":", "if False:"),
 ("fw/receiver.py", "if gateway is not None and gateway.outcome(binding.request_id) is not binding:", "if False:"),
 ("ml/receiver.py", "if o.entry.data_vintage_mode != requested_vintage_mode:", "if False:"),
 ("ml/receiver.py", "if gateway.outcome(o.request_id) is not o:", "if False:"),
 ("ml/receiver.py", "if e.requirement_class != OPTIONAL or o.absence_handling_applied_ref != e.absence_rule_ref:", "if False:"),
 ("ml/receiver.py", "if kind == \"ML_STANDALONE\" and lane != BASELINE:", "if False:"),
 ("fw/lanes.py", "or cur.post_target_retuning:", ":"),
 ("fw/lanes.py", "raise Refusal(m.manifest_id, code=\"HIDDEN_QUANT_ANCESTOR\")", "pass"),
 ("fw/lanes.py", "if m.declared_lane is not None and m.declared_lane != lane:", "if False:"),
 ("health/evidence.py", "if not isinstance(evidence, (FeatureHealthEvidence, LatencyMetricsV1, ResourceMetricsV1, ModelMetric)):", "if False:"),
 ("health/evidence.py", "if len(set(ids)) != len(ids):", "if False:"),
 ("context/edge.py", "if undeclared:", "if False:"),
 ("schema/independent.py", "_vid(r[\"state_schema_version\"]) + _vid(r[\"logical_encoding_version\"])", "_vid(r[\"logical_encoding_version\"]) + _vid(r[\"state_schema_version\"])"),
 ("schema/independent.py", "return b\"\\x01\" if x else b\"\\x00\"", "return b\"\\x00\""),
 ("schema/independent.py", "if c[\"available_asof\"] != c[\"canonical_accepted_at\"]:", "if False:"),
 ("schema/independent.py", "e[0] == \"INTERVAL\" and e[2] > e[1]", "e[0] == \"INTERVAL\""),
 ("coordination/scheduler.py", "PRIORITY_ORDER = (\"P0_LIVE_HEAD\", \"P1_LIVE_CRITICAL\", \"P2_HISTORICAL_REPLAY\")", "PRIORITY_ORDER = (\"P2_HISTORICAL_REPLAY\", \"P1_LIVE_CRITICAL\", \"P0_LIVE_HEAD\")"),
 ("coordination/scheduler.py", "if cls not in by:", "if False:"),
 ("coordination/scheduler.py", "for ns in sorted(queues):", "for ns in sorted(queues, key=lambda n: -len(queues[n])):"),
 ("tracker/epoch_reresolution.py", "if current_state in FENCED_STATES:", "if False:"),
 ("tracker/epoch_reresolution.py", "if request_epoch != current_epoch:", "if False:"),
 ("tracker/epoch_reresolution.py", "if expected_state != current_state:", "if False:"),
 ("tracker/epoch_reresolution.py", "if current_epoch is None or current_state is None:", "if False:"),
 ("schema/candidate_code_tables.py", "enumerate(v, 1)", "enumerate(v, 0)"),
]
def run():
    return subprocess.run([sys.executable, "-B", "-m", "pytest", "-q", "-x", str(ROOT / "tests/trk_stage_a/test_boundaries.py"), str(ROOT / "tests/trk_stage_a/test_v038_conformance.py"), str(ROOT / "tests/trk_stage_a/test_schema_annex.py"), str(ROOT / "tests/trk_stage_a/test_context_contracts.py")],
                          cwd=ROOT, capture_output=True, text=True, env=dict(__import__('os').environ, PYTHONDONTWRITEBYTECODE='1')).returncode
def main():
    assert run() == 0, "baseline must pass"
    survived = []
    for rel, old, new in M:
        p = ROOT / "stage_a" / rel; src = p.read_text()
        if src.count(old) != 1:
            print("NOT APPLICABLE (count=%d): %s :: %s" % (src.count(old), rel, old)); survived.append((rel, old, "not-applied")); continue
        try:
            p.write_text(src.replace(old, new)); killed = run() != 0
        finally:
            p.write_text(src)
        print(("killed  " if killed else "SURVIVED"), rel, "::", old[:70])
        if not killed: survived.append((rel, old))
    print("mutants: %d, survived/unapplied: %d" % (len(M), len(survived)))
    assert run() == 0
    return 1 if survived else 0
if __name__ == "__main__": sys.exit(main())
