"""R14: Codex-reproduced causal-time gap in the News Hub V2 resolver. Event availability is gated on EVERY causal stamp, daily records are validated inside
resolve_context, malformed/missing timestamps fail closed. Cutoff semantics are the News Hub's own (<= decision cutoff); the Gateway strict < fence is untouched."""
import unittest
from stage_a.errors import Refusal
from stage_a.context import news_hub_v2 as N
from tests.trk_stage_a.test_r13_context_resolver import ev, daily, code

def codex_event():
    e = {names[0]: "x" for names in N.EVENT_REQUIRED}
    e.update(EVENT_ID="E1", KNOWABILITY_MODE="OBSERVED", REVISION_AVAILABLE_AT=50, PUBLICLY_AVAILABLE_AT=200, SALIX_RECEIVED_AT=200, AVAILABLE_ASOF=200, REVISION_SEQ=1, FACTUAL_PAYLOAD_HASH="h1")
    return e
def codex_daily():
    return {"ISSUED_AT": 50, "SOURCE_AVAILABILITY_STATE": "AVAILABLE", "COVERAGE_STATE": "COMPLETE", "EVENT_PRESENCE_STATE": "EVENTS_PRESENT", "COVERAGE_BASIS": {"test": "basis"}}

class CodexReproduction(unittest.TestCase):
    def test_exact_codex_inputs_no_longer_usable(self):
        # the daily record is also incomplete (no id/scope/day/hash/...) => refused by validation inside resolve_context
        self.assertEqual(code(N.resolve_context, "REQUIRED", codex_daily(), [codex_event()], 100), "DAILY_RECORD_FIELD_MISSING")
    def test_codex_event_with_a_complete_daily_record_is_withheld_not_used(self):
        r = N.resolve_context("REQUIRED", daily(ISSUED_AT=50), [codex_event()], 100)
        self.assertEqual((r["events"], r["withheld"]), ([], [("E1", "PUBLICLY_NOT_YET_AVAILABLE")]))
class EachStampGates(unittest.TestCase):
    def w(self, **o): return N.resolve_context("REQUIRED", daily(), [ev(**o)], 100)["withheld"]
    def test_each_general_stamp_after_cutoff_withholds(self):
        self.assertEqual(self.w(PUBLICLY_AVAILABLE_AT=200, AVAILABLE_ASOF=200), [("E1", "PUBLICLY_NOT_YET_AVAILABLE")])
        self.assertEqual(self.w(SALIX_RECEIVED_AT=200, AVAILABLE_ASOF=200), [("E1", "SALIX_NOT_YET_RECEIVED")])        # public earlier, SALIX receipt later: no backfill
        self.assertEqual(self.w(AVAILABLE_ASOF=200), [("E1", "AVAILABLE_ASOF_AFTER_CUTOFF")])
        self.assertEqual(self.w(REVISION_AVAILABLE_AT=200), [("E1", "REVISION_NOT_YET_AVAILABLE")])
    def test_asof_before_public_or_receipt_is_withheld_fail_closed(self):
        self.assertEqual(self.w(PUBLICLY_AVAILABLE_AT=60, SALIX_RECEIVED_AT=70, AVAILABLE_ASOF=10), [("E1", "AVAILABLE_ASOF_BEFORE_PUBLIC_OR_RECEIPT")])
    def test_boundary_equal_to_fence_is_excluded_and_one_tick_earlier_is_consumable(self):
        r = N.resolve_context("REQUIRED", daily(), [ev(PUBLICLY_AVAILABLE_AT=100, SALIX_RECEIVED_AT=100, AVAILABLE_ASOF=100, REVISION_AVAILABLE_AT=100)], 100)
        self.assertEqual(r["events"], [])                                                   # half-open: equality excluded (frozen Blueprint s28 NEWS-02)
        r = N.resolve_context("REQUIRED", daily(), [ev(PUBLICLY_AVAILABLE_AT=99, SALIX_RECEIVED_AT=99, AVAILABLE_ASOF=99, REVISION_AVAILABLE_AT=99)], 100)
        self.assertEqual(len(r["events"]), 1)
        r = N.resolve_context("REQUIRED", daily(), [ev(PUBLICLY_AVAILABLE_AT=100, SALIX_RECEIVED_AT=101, AVAILABLE_ASOF=101)], 100)
        self.assertEqual(r["events"], [])
    def test_actual_gate_still_applies(self):
        a = dict(ACTUAL_VALUE="1", ACTUAL_PUBLICLY_AVAILABLE_AT=150, ACTUAL_SALIX_RECEIVED_AT=150, ACTUAL_AVAILABLE_ASOF=150)
        self.assertEqual(self.w(**a), [("E1", "ACTUAL_NOT_YET_AVAILABLE")])
    def test_consensus_and_previous_need_their_own_verified_stamp(self):
        self.assertEqual(self.w(CONSENSUS_VALUE="1"), [("E1", "CONSENSUS_AVAILABLE_ASOF_MISSING_VALUE_UNVERIFIED")])
        self.assertEqual(self.w(PREVIOUS="1", PREVIOUS_AVAILABLE_ASOF=500), [("E1", "PREVIOUS_AVAILABLE_ASOF_AFTER_CUTOFF")])
        self.assertEqual(len(N.resolve_context("REQUIRED", daily(), [ev(CONSENSUS_VALUE="1", CONSENSUS_AVAILABLE_ASOF=90)], 100)["events"]), 1)
    def test_event_consumable_validates_itself_without_the_caller(self):
        e = ev(); del e["PUBLICLY_AVAILABLE_AT"]
        self.assertEqual(code(N.event_consumable, e, 100), "EVENT_RECORD_FIELD_MISSING")
class MalformedTimestamps(unittest.TestCase):
    def test_bad_event_stamps_refuse(self):
        for f in N.TS_FIELDS:
            for bad in ("100", 1.5, True, None, [1]):
                e = ev(); e[f] = bad
                self.assertIn(code(N.resolve_context, "REQUIRED", daily(), [e], 100), ("EVENT_TIMESTAMP_MALFORMED", "EVENT_RECORD_FIELD_MISSING"), (f, bad))
    def test_bad_actual_and_value_stamps_refuse(self):
        self.assertEqual(code(N.check_event_record, ev(ACTUAL_VALUE="1", ACTUAL_PUBLICLY_AVAILABLE_AT="3", ACTUAL_SALIX_RECEIVED_AT=3, ACTUAL_AVAILABLE_ASOF=3)), "EVENT_TIMESTAMP_MALFORMED")
        self.assertEqual(code(N.check_event_record, ev(CONSENSUS_AVAILABLE_ASOF="x")), "EVENT_TIMESTAMP_MALFORMED")
    def test_bad_cutoff_and_non_mapping_refuse(self):
        for bad in ("100", None, True, 1.0): self.assertEqual(code(N.resolve_context, "REQUIRED", daily(), [ev()], bad), "CUTOFF_MALFORMED")
        self.assertEqual(code(N.check_event_record, "x"), "EVENT_RECORD_MALFORMED")
        self.assertEqual(code(N.resolve_context, "REQUIRED", "x", [], 100), "DAILY_RECORD_MALFORMED")
class RevisionRule(unittest.TestCase):
    def test_same_top_revision_different_payload_stays_multiple_even_under_the_rule(self):
        r = N.resolve_context("REQUIRED", daily(), [ev(seq=2, h="a"), ev(seq=2, h="b"), ev(seq=1, h="c")], 100, "HIGHEST_REVISION_SEQ")
        self.assertEqual((r["events"], r["multiple_candidates"]), ([], ["E1"]))
    def test_identical_payload_duplicates_collapse_without_a_rule(self):
        r = N.resolve_context("REQUIRED", daily(), [ev(h="a"), ev(h="a")], 100); self.assertEqual((len(r["events"]), r["multiple_candidates"]), (1, []))
class SafeConsumerHandling(unittest.TestCase):
    R = "HIGHEST_REVISION_SEQ"
    def two(self): return [ev(seq=1, rev_at=10, h="a"), ev(seq=2, rev_at=40, h="b")]
    def test_ambiguity_is_never_the_usable_verdict(self):
        r = N.resolve_context("REQUIRED", daily(), self.two(), 100)
        self.assertEqual((r["verdict"], r["multiple_candidates"]), ("MULTIPLE_CANDIDATES", ["E1"]))
        self.assertEqual(code(N.consumer_events, r), "CONTEXT_NOT_CONSUMER_RELIANCE_SAFE")
    def test_caller_string_selection_is_non_authoritative_and_not_relied_on(self):
        r = N.resolve_context("REQUIRED", daily(), self.two(), 100, self.R)
        self.assertEqual((r["verdict"], r["selection_rule_verified"], len(r["events"])), ("NON_AUTHORITATIVE_SELECTION", False, 1))
        self.assertEqual(code(N.consumer_events, r), "CONTEXT_NOT_CONSUMER_RELIANCE_SAFE")
    def test_plain_usable_is_consumable_and_declares_structural_only_admission(self):
        r = N.resolve_context("REQUIRED", daily(), [ev()], 100)
        self.assertEqual((r["verdict"], r["admission"], r["selection_rule_verified"]), ("USABLE", N.ADMISSION_STATE, False))
        self.assertEqual(len(N.consumer_events(r)), 1)
        self.assertTrue(N.ADMISSION_STATE.startswith("STRUCTURAL_ONLY"))
    def test_rule_string_with_no_ambiguity_stays_usable(self):
        self.assertEqual(N.resolve_context("REQUIRED", daily(), [ev()], 100, self.R)["verdict"], "USABLE")
    def test_consumer_events_refuses_malformed_input(self):
        for bad in (None, "USABLE", {}, {"verdict": "usable"}): self.assertEqual(code(N.consumer_events, bad), "CONTEXT_NOT_CONSUMER_RELIANCE_SAFE")
class DirectConsumable(unittest.TestCase):
    def test_event_consumable_rejects_malformed_cutoff_itself(self):
        for bad in ("100", None, True): self.assertEqual(code(N.event_consumable, ev(), bad), "CUTOFF_MALFORMED")
class DailyRecordValidatedInsideResolver(unittest.TestCase):
    def test_every_required_daily_field_missing_refuses(self):
        for k in N.DAILY_REQUIRED:
            d = {a: b for a, b in daily().items() if a != k}
            self.assertEqual(code(N.resolve_context, "REQUIRED", d, [], 100), "DAILY_RECORD_FIELD_MISSING", k)
    def test_malformed_issued_at_refuses_instead_of_type_error(self):
        for bad in ("5", 5.0, True): self.assertEqual(code(N.resolve_context, "REQUIRED", daily(ISSUED_AT=bad), [], 100), "DAILY_TIMESTAMP_MALFORMED")
    def test_boolean_no_event_field_refused_in_resolver(self):
        self.assertEqual(code(N.resolve_context, "REQUIRED", daily(NO_EVENT_RECORDED=True), [], 100), "NO_EVENT_RECORDED_IS_A_VALUE_NOT_A_BOOLEAN_FIELD")
    def test_not_yet_issued_still_fails_closed_and_valid_record_passes(self):
        self.assertEqual(code(N.resolve_context, "REQUIRED", daily(ISSUED_AT=200), [], 100), "REQUIRED_CONTEXT_FAIL_CLOSED")
        self.assertEqual(N.resolve_context("REQUIRED", daily(), [ev()], 100)["verdict"], "USABLE")
    def test_no_event_recorded_cannot_coexist_with_a_consumable_event(self):
        self.assertEqual(code(N.resolve_context, "REQUIRED", daily(EVENT_PRESENCE_STATE="NO_EVENT_RECORDED"), [ev()], 100), "DAILY_PRESENCE_CONTRADICTS_EVENTS")
        r = N.resolve_context("REQUIRED", daily(EVENT_PRESENCE_STATE="NO_EVENT_RECORDED"), [ev(PUBLICLY_AVAILABLE_AT=500, SALIX_RECEIVED_AT=500, AVAILABLE_ASOF=500)], 100)
        self.assertEqual(r["events"], [])                                                # a future event does not contradict a quiet-day attestation at this cutoff
if __name__ == "__main__": unittest.main()
class AvailableAsofEquality(unittest.TestCase):
    def test_available_asof_equal_to_cutoff_is_excluded_half_open(self):
        ok, why = N.event_consumable(ev(PUBLICLY_AVAILABLE_AT=50, SALIX_RECEIVED_AT=50, AVAILABLE_ASOF=100, REVISION_AVAILABLE_AT=50), 100)
        self.assertEqual((ok, why), (False, "AVAILABLE_ASOF_AFTER_CUTOFF"))
