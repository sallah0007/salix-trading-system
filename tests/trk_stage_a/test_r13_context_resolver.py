"""R13: News Hub V2 EVENT_RECORD / DAILY_EVENT_STATE_RECORD validators and the context resolver (market Event/Context, not Decision Context)."""
import unittest
from stage_a.errors import Refusal
from stage_a.context import news_hub_v2 as N
def ev(i="E1", seq=1, rev_at=10, h="h1", **o):
    r = {g[0]: "x" for g in N.EVENT_REQUIRED}
    r.update(EVENT_ID=i, REVISION_SEQ=seq, REVISION_AVAILABLE_AT=rev_at, KNOWABILITY_MODE="OBSERVED", FACTUAL_PAYLOAD_HASH=h, PUBLICLY_AVAILABLE_AT=1, SALIX_RECEIVED_AT=2, AVAILABLE_ASOF=2)
    r.update(o); return r
def daily(**o):
    r = dict(DAILY_EVENT_STATE_ID="D", GOVERNED_SCOPE="s", GOVERNED_DAY="d", ISSUED_AT=5, CONTEXT_REQUIREMENT_CLASS="REQUIRED", SOURCE_AVAILABILITY_STATE="AVAILABLE",
             COVERAGE_STATE="COMPLETE", EVENT_PRESENCE_STATE="EVENTS_PRESENT", COVERAGE_BASIS="basis", SOURCE_SET="ss", RECORD_HASH="rh"); r.update(o); return r
def code(fn, *a):
    try: fn(*a)
    except Refusal as e: return e.code
class Records(unittest.TestCase):
    def test_event_record_valid_and_each_required_group_enforced(self):
        N.check_event_record(ev())
        for g in N.EVENT_REQUIRED:
            r = ev()
            for n in g: r.pop(n, None)
            self.assertEqual(code(N.check_event_record, r), "EVENT_RECORD_FIELD_MISSING", g)
    def test_alias_names_accepted(self):
        r = ev(); r["EVENT_RECORD_ID"] = r.pop("EVENT_ID"); N.check_event_record(r)
    def test_knowability_enum(self): self.assertEqual(code(N.check_event_record, ev(KNOWABILITY_MODE="GUESS")), "BAD_KNOWABILITY_MODE")
    def test_actual_requires_both_timestamps_and_max_rule(self):
        self.assertEqual(code(N.check_event_record, ev(ACTUAL_VALUE="1")), "ACTUAL_NOT_CAUSALLY_CONSUMABLE")
        self.assertEqual(code(N.check_event_record, ev(ACTUAL_VALUE="1", ACTUAL_PUBLICLY_AVAILABLE_AT=3, ACTUAL_SALIX_RECEIVED_AT=7)), "ACTUAL_NOT_CAUSALLY_CONSUMABLE")
        self.assertEqual(code(N.check_event_record, ev(ACTUAL_VALUE="1", ACTUAL_PUBLICLY_AVAILABLE_AT=3, ACTUAL_SALIX_RECEIVED_AT=7, ACTUAL_AVAILABLE_ASOF=3)), "ACTUAL_AVAILABLE_ASOF_NOT_MAX_OF_PUBLIC_AND_RECEIPT")
        N.check_event_record(ev(ACTUAL_VALUE="1", ACTUAL_PUBLICLY_AVAILABLE_AT=3, ACTUAL_SALIX_RECEIVED_AT=7, ACTUAL_AVAILABLE_ASOF=7))
    def test_impact_rating_needs_vintage(self): self.assertEqual(code(N.check_event_record, ev(IMPACT_RATING="H")), "IMPACT_RATING_WITHOUT_VINTAGE")
    def test_daily_valid_and_required_fields(self):
        N.check_daily_record(daily())
        for k in N.DAILY_REQUIRED: self.assertEqual(code(N.check_daily_record, {a: b for a, b in daily().items() if a != k}), "DAILY_RECORD_FIELD_MISSING", k)
        self.assertEqual(code(N.check_daily_record, {a: b for a, b in daily().items() if a != "SOURCE_SET"}), "DAILY_RECORD_FIELD_MISSING")
    def test_no_event_recorded_is_not_a_boolean_field(self): self.assertEqual(code(N.check_daily_record, daily(NO_EVENT_RECORDED=True)), "NO_EVENT_RECORDED_IS_A_VALUE_NOT_A_BOOLEAN_FIELD")
    def test_daily_legality_lines(self):
        self.assertEqual(code(N.check_daily_record, daily(EVENT_PRESENCE_STATE="NO_EVENT_RECORDED", COVERAGE_STATE="PARTIAL")), "NO_EVENT_WITHOUT_COMPLETE")
        N.check_daily_record(daily(COVERAGE_STATE="PARTIAL", EVENT_PRESENCE_STATE="EVENTS_PRESENT"))            # PARTIAL + EVENTS_PRESENT is legal
        self.assertEqual(code(N.check_daily_record, daily(SOURCE_AVAILABILITY_STATE="UNAVAILABLE")), "UNAVAILABLE_COMPLETE_INVALID")
        self.assertEqual(code(N.check_daily_record, daily(CONTEXT_REQUIREMENT_CLASS="OPTIONAL", COVERAGE_STATE="PARTIAL")), "OPTIONAL_DEGRADED_WITHOUT_POLICY")
        N.check_daily_record(daily(CONTEXT_REQUIREMENT_CLASS="OPTIONAL", COVERAGE_STATE="PARTIAL", OPTIONAL_DEGRADED_POLICY_REF="P"))
        self.assertEqual(code(N.check_daily_record, daily(CONTEXT_REQUIREMENT_CLASS="MAYBE")), "BAD_CONTEXT_DIMENSION")
class Resolver(unittest.TestCase):
    def test_not_requested_needs_nothing(self): self.assertEqual(N.resolve_context("NOT_REQUESTED", None, [], 1)["coverage"], "NOT_REQUESTED")
    def test_missing_or_future_daily_record_never_quiet_day(self):
        self.assertEqual(code(N.resolve_context, "REQUIRED", None, [], 9), "REQUIRED_CONTEXT_FAIL_CLOSED")
        self.assertEqual(code(N.resolve_context, "REQUIRED", daily(ISSUED_AT=50), [], 9), "REQUIRED_CONTEXT_FAIL_CLOSED")          # no backward join before ISSUED_AT
        self.assertEqual(code(N.resolve_context, "OPTIONAL", None, [], 9), "OPTIONAL_DEGRADED_WITHOUT_POLICY")
    def test_complete_with_no_events_is_exhaustive(self):
        r = N.resolve_context("REQUIRED", daily(EVENT_PRESENCE_STATE="NO_EVENT_RECORDED"), [], 9); self.assertTrue(r["exhaustive"]); self.assertEqual(r["events"], [])
    def test_partial_is_not_exhaustive_and_required_fails_closed(self):
        d = daily(COVERAGE_STATE="PARTIAL")
        self.assertEqual(code(N.resolve_context, "REQUIRED", d, [], 9), "REQUIRED_CONTEXT_FAIL_CLOSED")
        r = N.resolve_context("OPTIONAL", dict(d, CONTEXT_REQUIREMENT_CLASS="OPTIONAL", OPTIONAL_DEGRADED_POLICY_REF="P"), [ev()], 20)
        self.assertFalse(r["exhaustive"]); self.assertEqual(len(r["events"]), 1)
    def test_actual_and_revision_withheld_before_their_availability(self):
        e = ev(ACTUAL_VALUE="1", ACTUAL_PUBLICLY_AVAILABLE_AT=3, ACTUAL_SALIX_RECEIVED_AT=30, ACTUAL_AVAILABLE_ASOF=30)
        r = N.resolve_context("REQUIRED", daily(), [e], 20); self.assertEqual((r["events"], r["withheld"]), ([], [("E1", "ACTUAL_NOT_YET_AVAILABLE")]))
        self.assertEqual(len(N.resolve_context("REQUIRED", daily(), [e], 30)["events"]), 1)
        self.assertEqual(N.resolve_context("REQUIRED", daily(), [ev(rev_at=99)], 20)["withheld"], [("E1", "REVISION_NOT_YET_AVAILABLE")])
    def test_highest_available_revision_wins_and_later_one_is_not_backfilled(self):
        r1, r2 = ev(seq=1, rev_at=10, h="a"), ev(seq=2, rev_at=40, h="b")
        self.assertEqual(N.resolve_context("REQUIRED", daily(), [r2, r1], 20)["events"][0]["FACTUAL_PAYLOAD_HASH"], "a")
        self.assertEqual(N.resolve_context("REQUIRED", daily(), [r1, r2], 50)["events"][0]["FACTUAL_PAYLOAD_HASH"], "b")
    def test_same_revision_different_payload_is_multiple_candidates(self):
        r = N.resolve_context("REQUIRED", daily(), [ev(h="a"), ev(h="b")], 20); self.assertEqual((r["multiple_candidates"], r["events"]), (["E1"], []))
    def test_deterministic_under_input_order(self):
        evs = [ev("E2", h="x"), ev("E1", h="y")]
        self.assertEqual(N.resolve_context("REQUIRED", daily(), evs, 20), N.resolve_context("REQUIRED", daily(), evs[::-1], 20))
    def test_invalid_event_record_refused(self): self.assertEqual(code(N.resolve_context, "REQUIRED", daily(), [ev(KNOWABILITY_MODE="Z")], 20), "BAD_KNOWABILITY_MODE")
if __name__ == "__main__": unittest.main()
