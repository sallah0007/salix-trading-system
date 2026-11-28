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
    def test_coverage_basis_is_required_only_when_coverage_was_evaluated(self):
        for st in ("COMPLETE", "PARTIAL", "DELAYED"):
            d = dict(CTX, COVERAGE_STATE=st); del d["COVERAGE_BASIS"]; self.assertEqual(code(check_h1, h1(**d)), "H1_CONDITIONAL_GROUP_INCOMPLETE", st); self.assertEqual(code(TypedH1, h1(**d)), "H1_CONDITIONAL_GROUP_INCOMPLETE", st)
        for st in ("NOT_EVALUATED", "UNKNOWN"):
            d = dict(CTX, COVERAGE_STATE=st); del d["COVERAGE_BASIS"]; self.assertIsNone(check_h1(h1(**d)), st)                       # source vocabulary: NOT_EVALUATED needs no basis; UNKNOWN is unconstrained (open question)
        d = dict(CTX, COVERAGE_STATE="NOT_EVALUATED"); self.assertIsNone(check_h1(h1(**d)))                                               # with a basis present it is also legal
if __name__ == "__main__": unittest.main()
