"""R40/R42: generic per-subject expectation carry. R42: an admitted ref is resolved to the INSTANCE and the supplied assertion must equal its payload (subject/state/window/ref) and the instance must be admitted+current+unrevoked; a known ref is never authority. TEST fixtures only: no producer, profile, threshold or admission is defined."""
import dataclasses, unittest
from stage_a.errors import Refusal
from stage_a.health import expectation as X
def code(f, *a, **k):
    try: f(*a, **k)
    except Refusal as e: return e.code
A = lambda state, ref="ADM-1", s="SUB1", f=0, u=100: X.ExpectationAssertion(s, state, f, u, ref)
def inst(a, **o): return X.ResolvedExpectation(a.admitted_ref, a.subject, a.state, a.valid_from, a.valid_until, **dict(dict(admitted=True, current=True, revoked=False), **o))
def R(*assertions, **o):
    recs = {a.admitted_ref: inst(a, **o) for a in assertions}; return lambda ref: recs.get(ref)
class Exp(unittest.TestCase):
    def test_only_an_admitted_in_window_exact_subject_assertion_counts_else_unknown_never_not_expected(self):
        e, n = A("EXPECTED"), A("NOT_EXPECTED"); self.assertEqual(X.expectation_for([e], "SUB1", 50, R(e)), ("EXPECTED", "")); self.assertEqual(X.expectation_for([n], "SUB1", 50, R(n)), ("NOT_EXPECTED", ""))
        for asr, at, res, subj in (([], 50, R(e), "SUB1"), ([e], 100, R(e), "SUB1"), ([e], 50, R(e), "OTHER"), ([A("EXPECTED", "unadmitted")], 50, R(e), "SUB1"), ([e], 50, None, "SUB1"), ([e], 50, lambda r: (_ for _ in ()).throw(Refusal("x", code="X")), "SUB1")):
            self.assertEqual(X.expectation_for(asr, subj, at, res)[0], "EXPECTATION_UNKNOWN")
        e2 = A("NOT_EXPECTED", "ADM-2"); self.assertEqual(X.expectation_for([e, e2], "SUB1", 50, R(e, e2)), ("EXPECTATION_UNKNOWN", "CONFLICTING_ASSERTIONS")); self.assertEqual(X.expectation_for([e, A("EXPECTED", "ADM-2")], "SUB1", 50, R(e, A("EXPECTED", "ADM-2")))[0], "EXPECTED")
    def test_r42_a_known_ref_with_altered_subject_state_validity_or_ref_is_not_authority(self):
        a = A("EXPECTED", "ADMITTED-A-REF", "OWNED-A"); res = R(a); self.assertEqual(X.expectation_for((a,), "OWNED-A", 10, res), ("EXPECTED", ""))
        for alt in (dataclasses.replace(a, subject="UNRELATED-B", state="NOT_EXPECTED"), dataclasses.replace(a, state="NOT_EXPECTED"), dataclasses.replace(a, valid_until=1000), dataclasses.replace(a, valid_from=5), dataclasses.replace(a, subject="UNRELATED-B")):
            self.assertEqual(X.expectation_for((alt,), alt.subject, 10, res)[0], "EXPECTATION_UNKNOWN", alt)
            self.assertEqual(X.silence_for(10, 5, alt.subject, (alt,), res)[0], "EXPECTATION_UNKNOWN_SILENCE")                      # root's NOT_APPLICABLE_SILENCE forgery no longer lands
        for bad in (lambda ref: ref == "ADMITTED-A-REF", lambda ref: True, lambda ref: {"subject": "OWNED-A"}): self.assertEqual(X.expectation_for((a,), "OWNED-A", 10, bad)[0], "EXPECTATION_UNKNOWN")      # the old boolean resolver is unusable
        other = dataclasses.replace(inst(a), admitted_ref="OTHER-REF"); self.assertEqual(X.expectation_for((a,), "OWNED-A", 10, lambda r: other)[0], "EXPECTATION_UNKNOWN")
    def test_r42_unadmitted_stale_or_revoked_instances_and_expired_assertions_are_unknown(self):
        a = A("EXPECTED")
        for o in (dict(admitted=False), dict(current=False), dict(revoked=True), dict(admitted=1), dict(revoked=0)): self.assertEqual(X.expectation_for([a], "SUB1", 50, R(a, **o))[0], "EXPECTATION_UNKNOWN", o)
        self.assertEqual(X.expectation_for([a], "SUB1", 100, R(a))[0], "EXPECTATION_UNKNOWN")           # half-open window: expired at valid_until
        self.assertEqual(X.expectation_for([a], "SUB1", 50, R(a))[0], "EXPECTED")
    def test_silence_is_interpreted_only_under_a_governed_expectation_and_expired_absence_is_never_healthy(self):
        e, n = A("EXPECTED"), A("NOT_EXPECTED"); self.assertEqual(X.silence_for(60, 55, "SUB1", [e], R(e))[0], "STALE_NO_PRODUCER"); self.assertEqual(X.silence_for(60, 55, "SUB1", [n], R(n))[0], "NOT_APPLICABLE_SILENCE")
        r = X.silence_for(60, 55, "SUB1", [], R(e)); self.assertEqual(r[:2], ("EXPECTATION_UNKNOWN_SILENCE", "EXPECTATION_UNKNOWN")); self.assertNotEqual(r[0], "HEALTHY"); self.assertIsNone(X.silence_for(50, 55, "SUB1", [], R(e))[0])
    def test_invalid_assertions_and_inputs_refuse(self):
        for a in (("", "EXPECTED", 0, 1, "r"), ("S", "MAYBE", 0, 1, "r"), ("S", "EXPECTED", 5, 5, "r"), ("S", "EXPECTED", True, 5, "r"), ("S", "EXPECTED", 0, 1, "")): self.assertEqual(code(X.ExpectationAssertion, *a), "EXPECTATION_ASSERTION_INVALID")
        self.assertEqual(code(X.expectation_for, [], "S", "5", None), "EXPECTATION_INPUT_INVALID")
if __name__ == "__main__": unittest.main()
