"""R26 candidate predicates: registry evidence-truth and causal imputation/fitted-transform firewall, with Core callpath (eligible_asof). Caller-supplied index/contract instances are NOT admitted authority."""
import unittest
from dataclasses import replace
from stage_a.tracker import evidence_truth as ET
from .test_r24_core import mk, ver, code

def rec(**k):
    d = dict(ref="E1", subject="S", version_or_hash="v1", instrument="XAUUSD", timeframe="H4", battery="B1", vintage="V1", dependencies=("D1",), result="PASS", available_at=10, max_age=5); d.update(k); return ET.EvidenceRecord(**d)
def claim(**k):
    d = dict(subject="S", version_or_hash="v1", instrument="XAUUSD", timeframe="H4", battery="B1", vintage="V1", dependencies=("D1",), expected_result="PASS", required_approval="APPROVED", evidence_refs=("E1",), signed_by="alice"); d.update(k); return ET.TransitionClaim(**d)
class EvidenceTruth(unittest.TestCase):
    def test_fresh_matching_scoped_positive(self): self.assertEqual(ET.judge_transition_evidence(claim(), {"E1": rec()}, 12).status, ET.VALID)
    def test_signed_actor_without_valid_evidence_is_never_valid(self):
        self.assertEqual(ET.judge_transition_evidence(claim(evidence_refs=()), {}, 12).status, ET.INVALID)
        self.assertEqual(ET.judge_transition_evidence(claim(signed_by="owner-and-everyone"), {}, 12).status, ET.INVALID)         # missing evidence
        self.assertEqual(ET.judge_transition_evidence(claim(signed_by=""), {"E1": rec()}, 12).status, ET.VALID)                  # the signature field neither helps nor hurts
    def test_each_dimension_mismatch_and_state_fails_closed(self):
        for kw in (dict(subject="X"), dict(version_or_hash="v2"), dict(instrument="EURUSD"), dict(timeframe="H1"), dict(battery="B2"), dict(vintage="V2"), dict(dependencies=("D2",)), dict(result="FAIL"),
                   dict(approval_state="PENDING"), dict(revoked=True), dict(current=False), dict(available_at=11 + 5), dict(available_at=0), dict(max_age=0), dict(ref="OTHER")):
            r = ET.judge_transition_evidence(claim(), {"E1": rec(**kw)}, 12); self.assertEqual(r.status, ET.INVALID, kw); self.assertTrue(r.reasons)
        self.assertEqual(ET.judge_transition_evidence(claim(evidence_refs=("E1", "E9")), {"E1": rec()}, 12).status, ET.INVALID)         # one resolving ref does not cover a missing one
        for bad in (dict(now=-1), dict(now=True)): self.assertEqual(ET.judge_transition_evidence(claim(), {"E1": rec()}, **bad).status, ET.UNPROVABLE)
    def test_verdict_has_no_truthiness(self):
        with self.assertRaises(TypeError): bool(ET.judge_transition_evidence(claim(), {"E1": rec()}, 12))
    def test_core_callpath_blocks_eligibility_on_invalid_evidence_and_clears_with_valid(self):
        c = mk(); ver(c, "S", version="v1", at=11, age=50); seq = c._j.head().seq
        self.assertEqual(c.eligible_asof("S", "v1", seq, 12)["state"], "SIMULATION_EVIDENCE_ELIGIBLE")                              # no verdict recorded: no claim either way
        c.judge_transition_evidence(claim(), {}, 12); self.assertIn("AUTHORITY_TRANSITION_EVIDENCE_NOT_VALID", c.eligible_asof("S", "v1", c._j.head().seq, 12)["reasons"])
        c.judge_transition_evidence(claim(), {"E1": rec()}, 12); self.assertEqual(c.eligible_asof("S", "v1", c._j.head().seq, 12)["reasons"], [])
class CausalFirewall(unittest.TestCase):
    def spec(self, **k):
        d = dict(kind="IMPUTATION", direction="CAUSAL", version="t1", fit_window_end=5, fit_permitted_until=8, asof=10, lineage_ref="L", missingness_observable=True, provenance_ref="P"); d.update(k); return ET.TransformSpec(**d)
    def test_causal_train_only_positive_control(self): self.assertEqual(ET.judge_transform(self.spec()).status, ET.VALID)
    def test_every_violation_is_refused(self):
        for kw in (dict(direction="BACKWARD"), dict(direction="FUTURE"), dict(direction="CENTERED"), dict(version=""), dict(fit_window_end=9), dict(fit_window_end=10, fit_permitted_until=11), dict(lineage_ref=""),
                   dict(missingness_observable=False), dict(provenance_ref=""), dict(kind="OTHER")):
            self.assertEqual(ET.judge_transform(self.spec(**kw)).status, ET.INVALID, kw)
        for kw in (dict(asof="10"), dict(fit_window_end=True)): self.assertEqual(ET.judge_transform(self.spec(**kw)).status, ET.UNPROVABLE)
    def test_core_callpath(self):
        c = mk(); ver(c, "S", at=11, age=50); c.judge_transform("S", self.spec(direction="FUTURE"))
        self.assertIn("TRANSFORM_NOT_CAUSAL_OR_UNPROVEN", c.eligible_asof("S", "1", c._j.head().seq, 12)["reasons"])
        c.judge_transform("S", self.spec()); self.assertEqual(c.eligible_asof("S", "1", c._j.head().seq, 12)["reasons"], [])
if __name__ == "__main__": unittest.main()
