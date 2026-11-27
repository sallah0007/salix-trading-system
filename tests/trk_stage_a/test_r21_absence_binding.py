"""R21: absence / non-delivery must be bound to the exact dependency, rule and an actually ISSUED immutable Gateway outcome in FW and ML receiving. No real consumer/provider is connected."""
import unittest
from stage_a.errors import Refusal
from stage_a.gateway import contracts as G
from stage_a.fw import receiver as FW
from stage_a.ml import receiver as ML
from .test_boundaries import _entry, _gw, _health, I, J, R, NONE_
def code(fn, *a, **k):
    try: fn(*a, **k)
    except Refusal as e: return e.code
def row(gw, entries, outs, fn=lambda o: NONE_): return ML.build_row("r", R("gen"), entries, outs, gw, "ORIGINAL_AS_OBSERVED", NONE_, fn)
class FwAbsence(unittest.TestCase):
    def setUp(self):
        self.gw = _gw(); self.e = _entry(opt=True, fid=J); self.good = self.gw.resolve("o", self.e, I, I, 3, 10, _health())
    def test_genuinely_issued_optional_absence_is_accepted_positive_control(self):
        self.assertIs(FW.receive_verified(self.good, self.e, I, I, None, self.gw), self.good)
    def test_codex_repro_forged_foreign_absence_is_refused(self):
        forged = G.AbsenceApplied("foreign-request", J, "wrong-version", R("different-abs-rule"))
        self.assertIn(code(FW.receive, forged, self.e, I, I, None), ("ABSENCE_FOR_DIFFERENT_DEPENDENCY",))
    def test_each_binding_dimension_is_enforced(self):
        a = self.good
        for bad, want in ((G.AbsenceApplied(a.request_id, a.feature_id, "wrong-version", a.absence_handling_applied_ref), "ABSENCE_FOR_DIFFERENT_DEPENDENCY"),
                           (G.AbsenceApplied(a.request_id, I, a.feature_version, a.absence_handling_applied_ref), "ABSENCE_FOR_DIFFERENT_DEPENDENCY"),
                           (G.AbsenceApplied(a.request_id, a.feature_id, a.feature_version, R("different-abs-rule")), "ABSENCE_RULE_MISMATCH"),
                           (G.AbsenceApplied("foreign-request", a.feature_id, a.feature_version, a.absence_handling_applied_ref), "OUTCOME_NOT_FROM_GATEWAY")):
            self.assertEqual(code(FW.receive_verified, bad, self.e, I, I, None, self.gw), want)
    def test_replayed_cross_request_outcome_is_not_the_stored_one(self):
        other = G.AbsenceApplied("another-request", self.good.feature_id, self.good.feature_version, self.good.absence_handling_applied_ref)
        self.assertEqual(code(FW.receive_verified, other, self.e, I, I, None, self.gw), "OUTCOME_NOT_FROM_GATEWAY")
    def test_required_dependency_absence_refuses_and_verified_path_needs_the_gateway(self):
        req = _entry(fid=J); a = G.AbsenceApplied("o", J, "f1", R("abs"))
        self.assertEqual(code(FW.receive_verified, a, req, I, I, None, self.gw), "REQUIRED_DEPENDENCY_ABSENT")
        self.assertEqual(code(FW.receive_verified, self.good, self.e, I, I, None, None), "GATEWAY_REQUIRED_FOR_VERIFIED_RECEIVE")
    def test_forged_non_delivery_is_not_accepted_as_a_settlement_failure(self):
        nd = G.NonDeliveryResolution("foreign", J, "wrong", "SETTLEMENT", 3)
        self.assertEqual(code(FW.receive, nd, self.e, I, I, None), "ABSENCE_FOR_DIFFERENT_DEPENDENCY")
class MlAbsence(unittest.TestCase):
    def setUp(self):
        self.gw = _gw(); self.e = _entry(opt=True, fid=J); self.good = self.gw.resolve("o", self.e, I, I, 3, 10, _health())
    def test_issued_optional_absence_positive_control(self):
        r = row(self.gw, [self.e], [self.good]); self.assertTrue(r.included); self.assertEqual(r.absence_applied, (self.good,))
    def test_codex_repro_wrong_dependency_absence_is_refused(self):
        forged = G.AbsenceApplied("foreign-request", J, "wrong-version", self.e.absence_rule_ref)
        self.assertEqual(code(row, self.gw, [self.e], [forged]), "ABSENCE_FOR_DIFFERENT_DEPENDENCY")
        class NoneGw:
            def outcome(self, rid): return None
        self.assertEqual(code(row, NoneGw(), [self.e], [forged]), "ABSENCE_FOR_DIFFERENT_DEPENDENCY")
    def test_right_dependency_but_not_issued_is_refused(self):
        fake = G.AbsenceApplied("never-issued", self.good.feature_id, self.good.feature_version, self.e.absence_rule_ref)
        self.assertEqual(code(row, self.gw, [self.e], [fake]), "OUTCOME_NOT_FROM_GATEWAY")
    def test_forged_non_delivery_cannot_exclude_a_required_row(self):
        req = _entry(fid=J); forged = G.NonDeliveryResolution("foreign", J, "f1", "SETTLEMENT", 3)
        self.assertEqual(code(row, self.gw, [req], [forged], lambda o: ("ENUM", "REASON", "NONE")), "OUTCOME_NOT_FROM_GATEWAY")
        issued = self.gw.resolve("z", req, I, I, 3, 10, _health())
        r = row(self.gw, [req], [issued], lambda o: ("ENUM", "REASON", "NONE"))
        self.assertFalse(r.included)                                                          # genuine issued non-delivery still excludes explicitly
if __name__ == "__main__": unittest.main()
