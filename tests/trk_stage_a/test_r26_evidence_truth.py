"""R26 candidate predicates: registry evidence-truth and causal imputation/fitted-transform firewall, with Core callpath (eligible_asof). Caller-supplied index/contract instances are NOT admitted authority."""
import unittest
from dataclasses import replace
from stage_a.tracker import evidence_truth as ET
from .test_r24_core import mk, ver, code

def rec(**k):
    d = dict(ref="E1", subject="S", version_or_hash="v1", instrument="XAUUSD", timeframe="H4", battery="B1", vintage="V1", dependencies=("D1",), result="PASS", available_at=10, max_age=5, revoked=False, current=True, approval_state="APPROVED"); d.update(k); return ET.EvidenceRecord(**d)
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
    def test_unstated_or_mistyped_evidence_states_fail_closed(self):
        with self.assertRaises(TypeError): ET.EvidenceRecord(ref="E1", subject="S", version_or_hash="v1", instrument="X", timeframe="H4", battery="B", vintage="V", dependencies=(), result="PASS", available_at=1, max_age=5)
        for kw in (dict(revoked=None), dict(revoked="false"), dict(revoked=0), dict(current=1), dict(current=None), dict(current="yes"), dict(approval_state=""), dict(approval_state=None), dict(approval_state=1),
                   dict(available_at="10"), dict(available_at=True), dict(max_age=5.0), dict(subject=""), dict(dependencies=["D1"]), dict(result=None)):
            r = ET.judge_transition_evidence(claim(), {"E1": rec(**kw)}, 12); self.assertEqual(r.status, ET.INVALID, kw); self.assertTrue(any("MALFORMED" in x for x in r.reasons), kw)
        for kw in (dict(subject=""), dict(evidence_refs=["E1"]), dict(dependencies=["D1"]), dict(battery=None)): self.assertEqual(ET.judge_transition_evidence(claim(**kw), {"E1": rec()}, 12).status, ET.UNPROVABLE, kw)
    def test_codex_r27_verdict_for_another_version_or_scope_never_clears(self):
        c = mk(); ver(c, "S", version="v1", at=11, age=50)
        c.judge_transition_evidence(claim(), {}, 12); self.assertEqual(c.eligible_asof("S", "v1", c._j.head().seq, 12)["reasons"], ["AUTHORITY_TRANSITION_EVIDENCE_NOT_VALID"])
        c.judge_transition_evidence(claim(version_or_hash="v2"), {"E1": rec(version_or_hash="v2")}, 12)                               # VALID verdict for v2 of the same subject
        self.assertEqual(c.eligible_asof("S", "v1", c._j.head().seq, 12)["reasons"], ["AUTHORITY_TRANSITION_EVIDENCE_NOT_VALID"])        # v1 stays blocked
        c.judge_transition_evidence(claim(instrument="EURUSD"), {"E1": rec(instrument="EURUSD")}, 12)                                   # VALID for another scope
        self.assertEqual(c.eligible_asof("S", "v1", c._j.head().seq, 12)["reasons"], ["AUTHORITY_TRANSITION_EVIDENCE_NOT_VALID"])
        c.judge_transition_evidence(claim(), {"E1": rec()}, 13); self.assertEqual(c.eligible_asof("S", "v1", c._j.head().seq, 13)["reasons"], [])      # positive control: ONLY the matching scope's own re-judgement clears it
    def test_invalid_verdict_for_another_version_does_not_block_and_unissued_snapshot_is_not_confirmed(self):
        import dataclasses
        from stage_a.gateway import contracts as G
        from .strict_gateway import bind
        from .test_boundaries import R
        c = mk(); ver(c, "S", version="v1", at=11, age=50); c.judge_transition_evidence(claim(version_or_hash="v2"), {}, 12)
        self.assertEqual(c.eligible_asof("S", "v1", c._j.head().seq, 12)["reasons"], [])                                              # v2's INVALID verdict is not v1's
        ver(c, "S", version="1", at=11, age=50); hs = c.gateway_health("S", "1", 12, R("hl"), 11, binding=bind(c, "S")); self.assertTrue(c.confirm_snapshot(hs))
        ghost = dataclasses.replace(hs, resolved_at=7); ghost = dataclasses.replace(ghost, snapshot_id=c._snapshot_id(ghost.subject, ghost.version, c._bhex(ghost.binding), ghost.resolution_ref, 7, ghost.acceptable, ghost.evidence_class, ghost.evaluated_at, ghost.held_reason))
        self.assertFalse(c.confirm_snapshot(ghost))                                                                                       # self-consistent id but never issued by this Core's journal
    def test_journal_preserves_full_binding_and_replay_asof_and_restart(self):
        from stage_a.core.tracker_core import TrackerCore
        c = mk(); ver(c, "S", version="v1", at=11, age=50); before = c._j.head().seq
        c.judge_transition_evidence(claim(), {}, 12); b = [r for r in c._j.read_from(0) if r.kind == "AUTH_EVIDENCE"][0]
        import json; body = json.loads(b.body_json)
        for k in ("subject", "version", "instrument", "timeframe", "battery", "vintage", "dependencies", "refs", "status", "reasons", "at", "valid_until"): self.assertIn(k, body)
        self.assertEqual(c.eligible_asof("S", "v1", before, 12)["reasons"], [])                                                       # as-of replay before the verdict
        c2 = TrackerCore(c._j, simulation=True); self.assertEqual(c2.eligible_asof("S", "v1", c._j.head().seq, 12)["reasons"], ["AUTHORITY_TRANSITION_EVIDENCE_NOT_VALID"])
    def test_gateway_health_composes_the_predicates_and_checks_freshness_at_use(self):
        from stage_a.gateway import contracts as G
        from .strict_gateway import sgw, bind
        from .test_boundaries import _entry, R, I
        c = mk(); ver(c, "S", version="1", at=11, age=50); c.judge_transition_evidence(claim(version_or_hash="1"), {"E1": rec(version_or_hash="1")}, 12)           # valid until 15
        hs = c.gateway_health("S", "1", 12, R("hl"), 11, binding=bind(c, "S")); self.assertTrue(hs.acceptable); self.assertIsInstance(sgw(c).resolve("o", _entry(ver="1"), I, I, 3, 20, hs), G.Binding)
        self.assertFalse(c.gateway_health("S", "1", 16, R("hl"), 11, binding=bind(c, "S")).acceptable)                                    # stale AT USE although the verdict was VALID when made
        c.judge_transition_evidence(claim(version_or_hash="1"), {}, 12); self.assertFalse(c.gateway_health("S", "1", 12, R("hl"), 11, binding=bind(c, "S")).acceptable)   # same S/1: eligibility blocked => Gateway Health blocked too
    def test_required_proofs_are_held_only_when_the_caller_declares_them(self):
        c = mk(); ver(c, "S", version="1", at=11, age=50)
        self.assertTrue(c.gateway_health("S", "1", 12, None, 11).acceptable)                                                            # nothing declared required: no battery invented
        self.assertFalse(c.gateway_health("S", "1", 12, None, 11, require_authority_evidence=True).acceptable)
        self.assertFalse(c.gateway_health("S", "1", 12, None, 11, require_transform_proof=True).acceptable)
        c.judge_transition_evidence(claim(version_or_hash="1"), {"E1": rec(version_or_hash="1")}, 12); self.assertTrue(c.gateway_health("S", "1", 12, None, 11, require_authority_evidence=True).acceptable)
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
        c = mk(); ver(c, "S", at=11, age=50); c.judge_transform("S", self.spec(direction="FUTURE"), "1")
        self.assertIn("TRANSFORM_NOT_CAUSAL_OR_UNPROVEN", c.eligible_asof("S", "1", c._j.head().seq, 12)["reasons"])
        c.judge_transform("S", self.spec(), "1"); self.assertEqual(c.eligible_asof("S", "1", c._j.head().seq, 12)["reasons"], [])
        c.judge_transform("S", self.spec(direction="BACKWARD"), "2"); self.assertEqual(c.eligible_asof("S", "1", c._j.head().seq, 12)["reasons"], [])      # a failing transform verdict for version 2 does not block version 1
        c.judge_transform("S", self.spec(direction="FUTURE", version="t2"), "1"); self.assertIn("TRANSFORM_NOT_CAUSAL_OR_UNPROVEN", c.eligible_asof("S", "1", c._j.head().seq, 12)["reasons"])
        c.judge_transform("S", self.spec(version="t2"), "1"); self.assertEqual(c.eligible_asof("S", "1", c._j.head().seq, 12)["reasons"], [])
        c.judge_transform("S", self.spec(direction="FUTURE", version="t3"), "1"); c.judge_transform("S", self.spec(version="t1"), "1")
        self.assertIn("TRANSFORM_NOT_CAUSAL_OR_UNPROVEN", c.eligible_asof("S", "1", c._j.head().seq, 12)["reasons"])      # a valid verdict for transform t1 does not clear the failing t3
if __name__ == "__main__": unittest.main()
