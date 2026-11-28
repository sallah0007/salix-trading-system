"""R52: candidate positive/negative tests for the eight minimum cases listed in News Hub V2 section 9.3 item 4 (Drive 1GSaxvVSkRmJDOgr7SqbPO2vHmuWEASVHzmn6Nuc5Ehw, read this pass).
These exercise the pure legality function only. They are NOT the formal first-execution acceptance, prove no ingestion, and name no provider. Items 1-3 and 5-9 of the same gate remain unperformed here."""
import unittest
from stage_a.context.news_hub_v2 import check_dimensions
from stage_a.errors import Refusal

B = "BASIS-X"   # opaque placeholder; the source does not define a byte form for COVERAGE_BASIS
def code(**kw):
    try: return check_dimensions(**kw)
    except Refusal as e: return e.code

class EightCases(unittest.TestCase):
    def test_1_required_available_complete_events_present(self):
        self.assertEqual(code(req="REQUIRED", src="AVAILABLE", cov="COMPLETE", pres="EVENTS_PRESENT", coverage_basis=B), "USABLE")
    def test_2_required_available_complete_no_event_recorded(self):
        self.assertEqual(code(req="REQUIRED", src="AVAILABLE", cov="COMPLETE", pres="NO_EVENT_RECORDED", coverage_basis=B), "USABLE")
        self.assertEqual(code(req="REQUIRED", src="AVAILABLE", cov="COMPLETE", pres="NO_EVENT_RECORDED"), "COMPLETE_WITHOUT_BASIS")
    def test_3_partial_with_events_is_non_exhaustive(self):
        self.assertEqual(code(req="REQUIRED", src="AVAILABLE", cov="PARTIAL", pres="EVENTS_PRESENT", coverage_basis=B), "REQUIRED_CONTEXT_FAIL_CLOSED")
        self.assertEqual(code(req="REQUIRED", src="AVAILABLE", cov="PARTIAL", pres="NO_EVENT_RECORDED", coverage_basis=B), "NO_EVENT_WITHOUT_COMPLETE")
        self.assertEqual(code(req="OPTIONAL", src="AVAILABLE", cov="PARTIAL", pres="EVENTS_PRESENT"), "OPTIONAL_DEGRADED_WITHOUT_POLICY")
    def test_4_unavailable(self):
        self.assertEqual(code(req="REQUIRED", src="UNAVAILABLE", cov="UNKNOWN", pres="UNKNOWN"), "REQUIRED_CONTEXT_FAIL_CLOSED")
    def test_5_unknown(self):
        for cov, pres in (("UNKNOWN", "EVENTS_PRESENT"), ("COMPLETE", "UNKNOWN")):
            self.assertEqual(code(req="REQUIRED", src="AVAILABLE", cov=cov, pres=pres, coverage_basis=B), "REQUIRED_CONTEXT_FAIL_CLOSED")
    def test_6_not_evaluated(self):
        self.assertEqual(code(req="REQUIRED", src="NOT_EVALUATED", cov="NOT_EVALUATED", pres="NOT_EVALUATED"), "REQUIRED_CONTEXT_FAIL_CLOSED")
        self.assertEqual(code(req="REQUIRED", src="AVAILABLE", cov="COMPLETE", pres="NOT_EVALUATED", coverage_basis=B), "REQUIRED_CONTEXT_FAIL_CLOSED")
    def test_7_optional_degraded_needs_explicit_policy_ref(self):
        kw = dict(req="OPTIONAL", src="AVAILABLE", cov="PARTIAL", pres="EVENTS_PRESENT")
        self.assertEqual(code(**kw), "OPTIONAL_DEGRADED_WITHOUT_POLICY")
        self.assertEqual(code(optional_degraded_policy_ref="POLICY-REF-X", **kw), "USABLE")
    def test_8_stale_prior_coverage_not_containing_window(self):
        kw = dict(req="REQUIRED", src="UNAVAILABLE", cov="COMPLETE", pres="EVENTS_PRESENT", coverage_basis=B, prior_coverage_issued_at=5, decision_cutoff=10)
        self.assertEqual(code(prior_coverage_contains_window=False, **kw), "UNAVAILABLE_COMPLETE_INVALID")
        self.assertEqual(code(prior_coverage_contains_window=None, **kw), "UNAVAILABLE_COMPLETE_INVALID")
        self.assertEqual(code(prior_coverage_contains_window=True, **{**kw, "prior_coverage_issued_at": 10}), "UNAVAILABLE_COMPLETE_INVALID")
        self.assertEqual(code(prior_coverage_contains_window=True, **kw), "USABLE")
