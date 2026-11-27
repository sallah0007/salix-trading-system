"""Protection-disabled mutants for the Annex-verifier / status / speculation / Gateway / FW / ML / lanes / Health modules.
Each mutant must make tests/trk_stage_a/test_boundaries.py FAIL. Run: python3 tests/trk_stage_a/mutation_sweep_boundaries.py"""
import subprocess, sys, pathlib
ROOT = pathlib.Path(__file__).resolve().parents[2]
M = [
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
 ("gateway/contracts.py", "if row.visible_at >= fence:", "if False:"),
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
    return subprocess.run([sys.executable, "-m", "pytest", "-q", "-x", str(ROOT / "tests/trk_stage_a/test_boundaries.py")],
                          cwd=ROOT, capture_output=True, text=True).returncode
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
