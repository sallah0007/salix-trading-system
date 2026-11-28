"""R41: NL0034/0262/0250/0258/0266 candidate oracles: two-part gate, stale-resolver negatives, complete-slice negatives, no current-generation fallback. Generic; supplied state names are TEST values, not a lifecycle graph."""
import unittest
from stage_a.errors import Refusal
from stage_a.tracker import historical_eligibility as H
E = H.Entry; EL = frozenset({"CERTIFIED"}); RV = frozenset({"REVOKED"})
LEDGER = [E(1, 1, 10, "G1", "CERTIFIED"), E(1, 2, 20, "G1", "SUPERSEDED"), E(1, 3, 20, "G2", "CERTIFIED"), E(2, 4, 40, "G2", "REVOKED")]
def rec(**k):
    a = dict(event_time=15, required_through_seq=4, resolved_through_seq=4, slice_closed_through_time=40, eligible_states=EL); a.update(k); return H.reconstruct_eligibility(LEDGER, **a)
class Hist(unittest.TestCase):
    def test_genuine_fresh_complete_read_resolves_the_generation_certified_at_the_event_time_not_the_current_one(self):
        d = rec(); self.assertEqual((d.status, d.generation_id), (H.READY, "G1"))
        d2 = rec(event_time=25); self.assertEqual((d2.status, d2.generation_id), (H.READY, "G2"))           # certified then, though revoked LATER at seq 4 (history is not rewritten)
    def test_stale_resolver_is_missed_never_a_current_generation_fallback(self):
        d = rec(resolved_through_seq=2); self.assertEqual((d.status, d.generation_id), (H.MISSED, "")); self.assertIn("CURRENT_READ_FRESHNESS_FAIL", d.reasons)
    def test_incomplete_slice_each_way_is_missed_even_when_the_read_is_fresh(self):
        d = rec(slice_closed_through_time=10); self.assertEqual(d.status, H.MISSED); self.assertTrue(any(r.startswith("HISTORICAL_SLICE_COMPLETENESS_FAIL") for r in d.reasons))
        gap = [E(1, 1, 10, "G1", "CERTIFIED"), E(1, 3, 20, "G2", "CERTIFIED")]
        d = H.reconstruct_eligibility(gap, event_time=15, required_through_seq=3, resolved_through_seq=3, slice_closed_through_time=40, eligible_states=EL); self.assertIn("HISTORICAL_SLICE_COMPLETENESS_FAIL:SEQUENCE_GAP", d.reasons)
    def test_both_failing_reports_both_and_no_eligible_or_ambiguous_is_missed(self):
        d = rec(resolved_through_seq=1, slice_closed_through_time=5); self.assertEqual(len(d.reasons), 2)
        self.assertEqual(rec(event_time=5).reasons, ("NO_ELIGIBLE_GENERATION",))
        amb = [E(1, 1, 10, "G1", "CERTIFIED"), E(1, 2, 10, "G2", "CERTIFIED")]
        self.assertEqual(H.reconstruct_eligibility(amb, event_time=12, required_through_seq=2, resolved_through_seq=2, slice_closed_through_time=12, eligible_states=EL).reasons, ("AMBIGUOUS_ELIGIBLE_GENERATIONS",))
    def test_the_decision_has_no_truthiness_and_malformed_inputs_refuse(self):
        with self.assertRaises(TypeError): bool(rec())
        for bad in (dict(event_time=True), dict(eligible_states=set()), dict(eligible_states=frozenset()), dict(required_through_seq=-1), dict(slice_closed_through_time="x")):
            with self.assertRaises(Refusal): rec(**bad)
        for led in ([E(1, 1, 10, "G", "S"), E(1, 1, 11, "G", "S")], [E(2, 1, 10, "G", "S"), E(1, 2, 11, "G", "S")], ["x"]):
            with self.assertRaises(Refusal): H.reconstruct_eligibility(led, event_time=1, required_through_seq=1, resolved_through_seq=1, slice_closed_through_time=1, eligible_states=EL)
    def test_artificial_index_lag_after_revocation_is_detected_not_reported_as_trusted(self):
        self.assertEqual(H.present_trust(LEDGER, "G2", required_through_seq=4, resolved_through_seq=4, revoked_states=RV), "REVOKED")
        self.assertEqual(H.present_trust(LEDGER, "G2", required_through_seq=4, resolved_through_seq=3, revoked_states=RV), "UNKNOWN_STALE")         # lagged resolver: revocation at seq 4 not yet seen
        self.assertEqual(H.present_trust(LEDGER, "G1", required_through_seq=4, resolved_through_seq=4, revoked_states=RV), "TRUSTED")
        self.assertEqual(H.present_trust(LEDGER, "GX", required_through_seq=4, resolved_through_seq=4, revoked_states=RV), "UNKNOWN_STALE")
if __name__ == "__main__": unittest.main()
