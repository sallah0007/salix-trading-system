import unittest
from stage_a.errors import Refusal
from stage_a.health import expectation as X
def code(f, *a, **k):
    try: f(*a, **k)
    except Refusal as e: return e.code
OK = lambda ref: ref.startswith("ADM-")
A = lambda state, ref="ADM-1", s="SUB1", f=0, u=100: X.ExpectationAssertion(s, state, f, u, ref)
class Exp(unittest.TestCase):
    def test_only_an_admitted_in_window_exact_subject_assertion_counts_else_unknown_never_not_expected(self):
        self.assertEqual(X.expectation_for([A("EXPECTED")], "SUB1", 50, OK), ("EXPECTED", "")); self.assertEqual(X.expectation_for([A("NOT_EXPECTED")], "SUB1", 50, OK), ("NOT_EXPECTED", ""))
        for asr, at, res, subj in (([], 50, OK, "SUB1"), ([A("EXPECTED")], 100, OK, "SUB1"), ([A("EXPECTED")], 50, OK, "OTHER"), ([A("EXPECTED", "unadmitted")], 50, OK, "SUB1"), ([A("EXPECTED")], 50, None, "SUB1"), ([A("EXPECTED")], 50, lambda r: (_ for _ in ()).throw(Refusal("x", code="C")), "SUB1"), (None, 50, OK, "SUB1")):
            self.assertEqual(X.expectation_for(asr, subj, at, res)[0], "EXPECTATION_UNKNOWN")
        self.assertEqual(X.expectation_for([A("EXPECTED"), A("NOT_EXPECTED", "ADM-2")], "SUB1", 50, OK), ("EXPECTATION_UNKNOWN", "CONFLICTING_ASSERTIONS")); self.assertEqual(X.expectation_for([A("EXPECTED"), A("EXPECTED", "ADM-2")], "SUB1", 50, OK)[0], "EXPECTED")
    def test_silence_is_interpreted_only_under_a_governed_expectation_and_expired_absence_is_never_healthy(self):
        self.assertEqual(X.silence_for(60, 55, "SUB1", [A("EXPECTED")], OK)[0], "STALE_NO_PRODUCER"); self.assertEqual(X.silence_for(60, 55, "SUB1", [A("NOT_EXPECTED")], OK)[0], "NOT_APPLICABLE_SILENCE")
        r = X.silence_for(60, 55, "SUB1", [], OK); self.assertEqual(r[:2], ("EXPECTATION_UNKNOWN_SILENCE", "EXPECTATION_UNKNOWN")); self.assertNotEqual(r[0], "HEALTHY"); self.assertIsNone(X.silence_for(50, 55, "SUB1", [], OK)[0])      # inside validity: no silence derived
    def test_invalid_assertions_and_inputs_refuse(self):
        for a in (("", "EXPECTED", 0, 1, "r"), ("S", "MAYBE", 0, 1, "r"), ("S", "EXPECTED", 5, 5, "r"), ("S", "EXPECTED", True, 5, "r"), ("S", "EXPECTED", 0, 1, "")): self.assertEqual(code(X.ExpectationAssertion, *a), "EXPECTATION_ASSERTION_INVALID")
        self.assertEqual(code(X.expectation_for, [], "S", "5", OK), "EXPECTATION_INPUT_INVALID")
if __name__ == "__main__": unittest.main()
