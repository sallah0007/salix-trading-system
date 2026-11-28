"""R46 H3 outcome/target-label delivery decision. Mutants: tests/trk_stage_a/mutation_sweep_r46_h3.py. A pass clears no gate."""
import unittest
from stage_a.errors import Refusal
from stage_a.gateway.outcome_delivery import decide, REQUIRED
def code(f, *a, **k):
    try: f(*a, **k)
    except Refusal as e: return e.code
SEG = {"S1": [(0, 100)], "S2": [(100, 200)]}
def rec(**o):
    r = dict(consumer_binding_id="CB1", outcome_or_target_series_id="O1", series_version_or_hash="h", observation_time_origin=0, horizon_id="H", horizon_version="1", dependency_interval_start=10, dependency_interval_end=50,
             authorized_segment_set=["S1"], consumer_stage="TRAIN", outcome_package_hash="ph", available_asof=60, delivery_decision_ts=70); r.update(o); return r
class H3(unittest.TestCase):
    def test_inside_authorized_segment_delivers_but_is_never_qualified(self):
        d = decide(rec(), segments_by_name=SEG); self.assertTrue(d.delivered); self.assertFalse(d.qualified)
    def test_half_open_boundary_and_crossing_into_unauthorized_next_segment_withholds(self):
        self.assertTrue(decide(rec(dependency_interval_end=100), segments_by_name=SEG).delivered)
        d = decide(rec(dependency_interval_end=101), segments_by_name=SEG); self.assertFalse(d.delivered); self.assertEqual(d.reasons, ("INTERVAL_NOT_INSIDE_AUTHORIZED_SEGMENTS",))
        self.assertTrue(decide(rec(dependency_interval_end=150, authorized_segment_set=["S1", "S2"]), segments_by_name=SEG).delivered)          # contiguous authorized segments cover
        self.assertFalse(decide(rec(dependency_interval_end=150, authorized_segment_set=["S1", "S2"]), segments_by_name={"S1": [(0, 100)], "S2": [(120, 200)]}).delivered)   # a gap is not covered
    def test_sealed_holdout_needs_the_unseal_ref_and_unopened_region_withholds(self):
        sh = [(40, 60)]
        self.assertEqual(decide(rec(), segments_by_name=SEG, sealed_holdout=sh).reasons, ("SEALED_HOLDOUT_WITHOUT_UNSEAL_EVENT_REF",))
        self.assertTrue(decide(rec(holdout_unseal_event_ref="U1"), segments_by_name=SEG, sealed_holdout=sh).delivered)
        self.assertFalse(decide(rec(dependency_interval_end=50), segments_by_name=SEG, sealed_holdout=[(50, 60)]).reasons)             # touching only at the half-open end is not overlap
        self.assertIn("INTERVAL_TOUCHES_UNOPENED_REGION", decide(rec(holdout_unseal_event_ref="U1"), segments_by_name=SEG, unopened_regions=[(45, 55)]).reasons)
    def test_malformed_records_refuse(self):
        for o, c in (({"consumer_binding_id": ""}, "H3_FIELD_INVALID"), ({"dependency_interval_start": 50}, "H3_INTERVAL_EMPTY_OR_REVERSED"), ({"available_asof": 71}, "H3_AVAILABLE_AFTER_DECISION"),
                     ({"authorized_segment_set": ["NOPE"]}, "H3_SEGMENT_UNKNOWN"), ({"authorized_segment_set": []}, "H3_FIELD_INVALID"), ({"horizon_id": 1}, "H3_FIELD_INVALID"), ({"holdout_unseal_event_ref": ""}, "H3_FIELD_INVALID"), ({"surprise": 1}, "H3_FIELD_SET")):
            self.assertEqual(code(decide, rec(**o), segments_by_name=SEG), c, o)
        r = rec(); del r["horizon_version"]; self.assertEqual(code(decide, r, segments_by_name=SEG), "H3_FIELD_SET"); self.assertEqual(code(decide, rec()), "H3_SEGMENT_MODEL_UNSUPPLIED_HELD"); self.assertEqual(code(decide, "x", segments_by_name=SEG), "H3_RECORD_NOT_AN_OBJECT")
if __name__ == "__main__": unittest.main()
