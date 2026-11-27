"""R11: BOTH enforcement at the Gateway boundary (v038). Code event only."""
import unittest
from stage_a.errors import Refusal
from stage_a.gateway import v038 as V

def lane(cls, tag, ml=False, target="BOTH"):
    f = {k: "x-" + tag for k in V.H1_REQUIRED}
    f.update(ISSUER="TRACKER_CONSUMER_GATEWAY", PACKAGE_CLASS=cls, TARGET_CONSUMER=target, REQUEST_ID="REQ-B",
             RESOLUTION_VISIBILITY_WATERMARK="w")
    if ml: f.update(ML_MANIFEST_CLASS="m", GENERATION_AUTHORITY_CLASS="g")
    return f
def pair(): return lane("FW_PACKAGE", "fw"), lane("ML_PACKAGE", "ml", ml=True)
def code(fw, ml):
    with unittest.TestCase().assertRaises(Refusal) as c: V.check_both_separation(fw, ml)
    return c.exception.code

class BothSeparation(unittest.TestCase):
    def test_distinct_lanes_pass(self): V.check_both_separation(*pair())
    def test_each_shared_identity_field_refused(self):
        for f in V.BOTH_DISTINCT_FIELDS:
            fw, ml = pair(); ml[f] = fw[f]
            self.assertEqual(code(fw, ml), "BOTH_LANES_SHARE_IDENTITY_FIELD", f)
    def test_fw_lane_is_h1_checked_too(self):
        fw, ml = pair(); del fw["PURPOSE"]
        self.assertEqual(code(fw, ml), "H1_FIELD_MISSING")
    def test_ml_lane_needs_ml_fields(self):
        fw, ml = pair(); del ml["ML_MANIFEST_CLASS"]
        self.assertEqual(code(fw, ml), "H1_FIELD_MISSING")
    def test_wrong_package_class_refused(self):
        fw, ml = pair(); fw["PACKAGE_CLASS"] = "ML_PACKAGE"; ml["PACKAGE_CLASS"] = "FW_PACKAGE"
        self.assertEqual(code(fw, ml), "BOTH_LANE_PACKAGE_CLASS_MISMATCH")
    def test_lane_target_mismatch_refused(self):
        fw, ml = pair(); fw["TARGET_CONSUMER"] = "MACHINE_LEARNING"
        self.assertEqual(code(fw, ml), "BOTH_LANE_TARGET_MISMATCH")
    def test_different_request_refused(self):
        fw, ml = pair(); ml["REQUEST_ID"] = "OTHER"
        self.assertEqual(code(fw, ml), "BOTH_LANES_DIFFERENT_REQUEST")

class BothResolution(unittest.TestCase):
    I_FW = V.FinalResolutionIdentity("FW", "b-fw", "XAUUSD/H4", "F1")
    I_ML = V.FinalResolutionIdentity("ML", "b-ml", "XAUUSD/H4", "F1")
    def test_lanes_resolve_independently_and_one_failure_does_not_touch_the_other(self):
        s = V.FinalResolutionStore()
        def bad(): raise Refusal("x", code="ML_EVAL_FAIL")
        r = V.resolve_both(s, "R", self.I_FW, self.I_ML, lambda: "fw-out", bad)
        self.assertEqual(r["FORWARD_WALK"], ("RESOLVED", "fw-out")); self.assertEqual(r["MACHINE_LEARNING"], ("REFUSED", "ML_EVAL_FAIL"))
        r2 = V.resolve_both(s, "R", self.I_FW, self.I_ML, lambda: "CHANGED", lambda: "ml-out")
        self.assertEqual(r2["FORWARD_WALK"], ("RESOLVED", "fw-out"))          # immutable final outcome reused, never re-evaluated
        self.assertEqual(r2["MACHINE_LEARNING"], ("RESOLVED", "ml-out"))      # failed lane may retry
    def test_shared_identity_refused(self):
        with self.assertRaises(Refusal) as c:
            V.resolve_both(V.FinalResolutionStore(), "R", self.I_FW, self.I_FW, lambda: 1, lambda: 2)
        self.assertEqual(c.exception.code, "BOTH_LANES_SHARE_RESOLUTION_IDENTITY")
    def test_same_consumer_id_refused(self):
        j = V.FinalResolutionIdentity("FW", "b-ml", "XAUUSD/H4", "F1")
        with self.assertRaises(Refusal): V.resolve_both(V.FinalResolutionStore(), "R", self.I_FW, j, lambda: 1, lambda: 2)
if __name__ == "__main__": unittest.main()
