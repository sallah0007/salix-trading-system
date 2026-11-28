"""R54: S6 H1 CONDITIONAL field groups (live Contract re-read): a partially present Event/Context group, applicability-map pair or revocation-watermark pair is refused; whole groups or no group stay legal; COVERAGE_BASIS is required with COVERAGE_STATE. The required 17+health pair+watermark list and the ML conditional rule are unchanged (existing tests)."""
import unittest
from stage_a.errors import Refusal
from stage_a.gateway.v038 import check_h1, H1_CONTEXT_GROUP
from stage_a.gateway.h1_record import TypedH1
from .test_r50_h1_augmented import h1
def code(f, *a, **k):
    try: f(*a, **k)
    except Refusal as e: return e.code
CTX = dict(CONTEXT_REQUIREMENT_CLASS="REQUIRED", SOURCE_AVAILABILITY_STATE="AVAILABLE", COVERAGE_STATE="COMPLETE", EVENT_PRESENCE_STATE="EVENTS_PRESENT", COVERAGE_BASIS="B")
class Conditional(unittest.TestCase):
    def test_whole_groups_and_no_groups_are_legal(self):
        self.assertIsNone(check_h1(h1())); self.assertIsNone(check_h1(h1(**CTX, APPLICABILITY_MAP_ID="a", APPLICABILITY_MAP_VERSION="1", REVOCATION_WATERMARK_REF="r", REVOCATION_WATERMARK_OBSERVED_AT=1))); TypedH1(h1(**CTX))
    def test_each_member_of_each_group_is_required_with_its_peers(self):
        for k in H1_CONTEXT_GROUP:
            d = {x: v for x, v in CTX.items() if x != k}; self.assertEqual(code(check_h1, h1(**d)), "H1_CONDITIONAL_GROUP_INCOMPLETE", k)
        for a in ("APPLICABILITY_MAP_ID", "APPLICABILITY_MAP_VERSION"): self.assertEqual(code(check_h1, h1(**{a: "x"})), "H1_CONDITIONAL_GROUP_INCOMPLETE", a)
        for a in ("REVOCATION_WATERMARK_REF", "REVOCATION_WATERMARK_OBSERVED_AT"): self.assertEqual(code(check_h1, h1(**{a: "x"})), "H1_CONDITIONAL_GROUP_INCOMPLETE", a)
    def test_h1_basis_rule_per_state_and_case(self):
        nb = lambda **k: {x: v for x, v in dict(CTX, **k).items() if x != "COVERAGE_BASIS"}
        for st in ("COMPLETE", "PARTIAL", "DELAYED", "UNKNOWN"):                                         # evaluated results (UNKNOWN can be one): basis required
            self.assertEqual(code(check_h1, h1(**nb(COVERAGE_STATE=st))), "H1_CONDITIONAL_GROUP_INCOMPLETE", st); self.assertEqual(code(TypedH1, h1(**nb(COVERAGE_STATE=st))), "H1_CONDITIONAL_GROUP_INCOMPLETE", st)
            self.assertIsNone(check_h1(h1(**dict(CTX, COVERAGE_STATE=st))), st)                           # UNKNOWN + evaluated (basis present) is legal
        self.assertIsNone(check_h1(h1(**nb(COVERAGE_STATE="NOT_EVALUATED"))))                              # the explicit not-evaluated fact: valid H1 without a basis
        self.assertIsNone(check_h1(h1(**dict(CTX, COVERAGE_STATE="NOT_EVALUATED"))))                       # and with one
        self.assertIsNone(check_h1(h1()))                                                                  # ordinary no-context binding: untouched
    def test_unknown_without_basis_is_held_not_inferred_as_not_evaluated(self):
        # UNKNOWN+not-evaluated cannot be told from UNKNOWN+evaluated in H1 (source gap): it is refused, never silently exempted.
        self.assertEqual(code(check_h1, h1(**{k: v for k, v in dict(CTX, COVERAGE_STATE="UNKNOWN").items() if k != "COVERAGE_BASIS"})), "H1_CONDITIONAL_GROUP_INCOMPLETE")
class H2(unittest.TestCase):
    from stage_a.gateway.v038 import check_h2
    OK = dict(CONSUMER_BINDING_ID="c", CONTEXT_REQUIREMENT_CLASS="REQUIRED", SOURCE_AVAILABILITY_STATE="AVAILABLE", COVERAGE_STATE="COMPLETE", EVENT_PRESENCE_STATE="EVENTS_PRESENT", COVERAGE_BASIS="B",
              REQUESTED_WINDOW_START=1, REQUESTED_WINDOW_END=2, EVENT_RECORD_REFS=[], AVAILABLE_ASOF=3)
    def test_h2_requires_basis_even_when_not_evaluated(self):
        from stage_a.gateway.v038 import check_h2
        self.assertIsNone(check_h2(self.OK)); self.assertIsNone(check_h2(dict(self.OK, COVERAGE_STATE="NOT_EVALUATED")))
        d = dict(self.OK, COVERAGE_STATE="NOT_EVALUATED"); del d["COVERAGE_BASIS"]; self.assertEqual(code(check_h2, d), "H2_FIELD_MISSING")        # H1 would allow this; H2 does not
        self.assertIsNone(check_h1(h1(**{k: v for k, v in dict(CTX, COVERAGE_STATE="NOT_EVALUATED").items() if k != "COVERAGE_BASIS"})))        # the same state stays valid in H1
    def test_h2_each_named_field_and_conditional_pair(self):
        from stage_a.gateway.v038 import check_h2, H2_HELD_SLASH_ITEMS
        for k in self.OK: d = dict(self.OK); del d[k]; self.assertEqual(code(check_h2, d), "H2_FIELD_MISSING", k)
        self.assertEqual(code(check_h2, dict(self.OK, APPLICABILITY_MAP_ID="a")), "H2_CONDITIONAL_GROUP_INCOMPLETE"); self.assertEqual(code(check_h2, dict(self.OK, EVENT_RECORD_REFS="x")), "H2_EVENT_RECORD_REFS_NOT_A_LIST")
        self.assertEqual(code(check_h2, dict(self.OK, COVERAGE_STATE="MAYBE")), "H2_COVERAGE_STATE_VOCABULARY"); self.assertEqual(len(H2_HELD_SLASH_ITEMS), 2)
if __name__ == "__main__": unittest.main()
