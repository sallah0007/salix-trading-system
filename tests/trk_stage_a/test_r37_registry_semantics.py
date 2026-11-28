"""R37: Registry p105-124 snapshot manifest, p122-123/p182-183 vintage and fence rules, p242 merge direction + survivor chain, p267-279 lifecycle vocabulary."""
import dataclasses, unittest
from stage_a.errors import Refusal
from stage_a.tracker import registry_semantics as RS
def code(f, *a, **k):
    try: f(*a, **k)
    except Refusal as e: return e.code
def man(**o):
    d = dict(tracker_snapshot_id="S1", instrument_id="XAUUSD", timeframe_or_event_class="H4", canonical_bar_or_event_identity="BAR1", broker_server_time_identity="BT1", utc_identity="U1", broker_utc_rule_version="R1", source_provider_identity="P1", raw_source_version="V1", tracker_schema_calculation_family_version="C1",
             data_quality_missingness_staleness="Q1", creation_effective_available_asof_identities="T1", data_vintage_mode="ORIGINAL_AS_OBSERVED", external_enrichment_ids=(), fence_read_boundary_identity="F1", query_asof=100, snapshot_fence_ts=100, timeframe_watermarks=(("H1", 99), ("H4", 90)))
    d.update(o); return RS.TrackerSnapshotManifest(**d)
class Snapshot(unittest.TestCase):
    def test_complete_manifest_hashes_deterministically_and_each_field_is_load_bearing(self):
        h = man().manifest_hash(); self.assertEqual(h, man().manifest_hash()); self.assertEqual(len(dataclasses.fields(RS.TrackerSnapshotManifest)) - 3, 15)
        for f in dataclasses.fields(RS.TrackerSnapshotManifest):
            if f.name in ("external_enrichment_ids", "timeframe_watermarks"): continue
            v = man(**{f.name: (101 if f.name == "snapshot_fence_ts" else 5 if f.name == "query_asof" else "ORIGINAL_AS_OBSERVED" if False else "CURRENT_CORRECTED" if f.name == "data_vintage_mode" else "X")}); self.assertNotEqual(v.manifest_hash(), h, f.name)       # changing any identity changes the hash
        self.assertNotEqual(man(timeframe_watermarks=(("H1", 98), ("H4", 90))).manifest_hash(), h); self.assertNotEqual(man(external_enrichment_ids=("E1",)).manifest_hash(), h)
    def test_missing_or_malformed_fields_refuse_and_false_simultaneity_is_impossible(self):
        for f in ("tracker_snapshot_id", "instrument_id", "utc_identity", "broker_utc_rule_version", "fence_read_boundary_identity"): self.assertEqual(code(man(**{f: ""}).validate), "SNAPSHOT_MANIFEST_FIELD_MISSING", f)
        self.assertEqual(code(man(data_vintage_mode="LATEST").validate), "SNAPSHOT_VINTAGE_MODE_UNKNOWN"); self.assertEqual(code(man(timeframe_watermarks=()).validate), "SNAPSHOT_TIMEFRAME_WATERMARKS_REQUIRED"); self.assertEqual(code(man(timeframe_watermarks=(("H1", 1), ("H1", 2))).validate), "SNAPSHOT_TIMEFRAME_WATERMARKS_REQUIRED")
        self.assertEqual(code(man(timeframe_watermarks=(("H1", 101),)).validate), "SNAPSHOT_WATERMARK_AFTER_FENCE"); self.assertEqual(code(man(query_asof=101).validate), "SNAPSHOT_QUERY_ASOF_AFTER_FENCE"); self.assertEqual(code(man(query_asof=True).validate), "SNAPSHOT_MANIFEST_FIELD_INVALID")
    def test_half_open_fence_and_mixed_vintage_default_deny(self):
        self.assertTrue(RS.included_in_snapshot(99, 100)); self.assertFalse(RS.included_in_snapshot(100, 100)); self.assertFalse(RS.included_in_snapshot(101, 100)); self.assertEqual(code(RS.included_in_snapshot, True, 100), "SNAPSHOT_TS_INVALID")
        o, c = "ORIGINAL_AS_OBSERVED", "CURRENT_CORRECTED"; self.assertEqual(RS.check_mixed_vintage({"a": o, "b": o}, None, o), o); self.assertEqual(code(RS.check_mixed_vintage, {"a": o, "b": c}, True, o), "MIXED_VINTAGE_NOT_DECLARED"); self.assertEqual(code(RS.check_mixed_vintage, {"a": o, "b": o}, None, c), "CLAIMED_MODE_NOT_HOMOGENEOUS_MODE")
        for pol in (None, False): self.assertEqual(code(RS.check_mixed_vintage, {"a": o, "b": c}, pol, "MIXED_DECLARED"), "MIXED_VINTAGE_POLICY_UNSET")
        self.assertEqual(RS.check_mixed_vintage({"a": o, "b": c}, True, "MIXED_DECLARED"), "MIXED_DECLARED")
class Registry(unittest.TestCase):
    def test_merge_direction_follows_the_source_rules_and_refuses_what_it_does_not_decide(self):
        n = dict(id="N", origin="NATIVE", independent_source_authority=False, proven_identical=True); b = dict(id="B", origin="BUILDER", independent_source_authority=False, proven_identical=True); e = dict(id="E", origin="EXTERNAL", independent_source_authority=True, proven_identical=True)
        self.assertEqual(RS.merge_direction(b, n)["survivor"], "N"); self.assertEqual(RS.merge_direction(b, n)["rule"], "NATIVE_OVER_BUILDER"); self.assertEqual(RS.merge_direction(n, e)["survivor"], "E"); self.assertEqual(RS.merge_direction(b, dict(n, independent_source_authority=True))["rule"], "INDEPENDENT_GOVERNED_SOURCE_AUTHORITY")
        self.assertEqual(code(RS.merge_direction, b, dict(b, id="B2")), "MERGE_DIRECTION_UNDETERMINED"); self.assertEqual(code(RS.merge_direction, b, dict(b, id="B2", independent_source_authority=True)), "MERGE_DIRECTION_UNDETERMINED"); self.assertEqual(code(RS.merge_direction, b, dict(n, proven_identical=False)), "MERGE_DIRECTION_UNDETERMINED"); self.assertEqual(code(RS.merge_direction, b, dict(e, independent_source_authority=False)), "MERGE_DIRECTION_UNDETERMINED"); self.assertEqual(code(RS.merge_direction, b, {}), "MERGE_INPUT_INVALID")
        self.assertEqual(code(RS.merge_direction, dict(b, independent_source_authority=True), dict(e)), "MERGE_DIRECTION_UNDETERMINED")        # both authoritative, neither NATIVE/BUILDER pair
    def test_survivor_chain_is_transitive_acyclic_and_terminating(self):
        self.assertEqual(RS.resolve_survivor_chain({"A": "B", "B": "C"}, "A"), ("A", "B", "C")); self.assertEqual(RS.resolve_survivor_chain({}, "A"), ("A",)); self.assertEqual(code(RS.resolve_survivor_chain, {"A": "B", "B": "A"}, "A"), "SURVIVOR_CYCLE"); self.assertEqual(code(RS.resolve_survivor_chain, {"A": "A"}, "A"), "SURVIVOR_CYCLE")
        self.assertEqual(code(RS.resolve_survivor_chain, {"A": 1}, "A"), "SURVIVOR_INPUT_INVALID"); long = {str(i): str(i + 1) for i in range(100)}; self.assertEqual(code(RS.resolve_survivor_chain, long, "0", 10), "SURVIVOR_CHAIN_NOT_TERMINATING")
    def test_lifecycle_vocabulary_is_the_twelve_source_states_and_unknown_refuses(self):
        self.assertEqual(len(RS.LIFECYCLE_STATES), 12); [self.assertEqual(RS.check_lifecycle_state(s), s) for s in RS.LIFECYCLE_STATES]; self.assertEqual(code(RS.check_lifecycle_state, "LIVE_SAFE"), "LIFECYCLE_STATE_UNKNOWN")
if __name__ == "__main__": unittest.main()
