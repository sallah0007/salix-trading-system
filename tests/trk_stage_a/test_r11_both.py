"""BOTH enforcement at the Gateway boundary (v038): per-lane source-defined consumer identity, binding/identity agreement,
consumer-local request keys (no alias namespace), replay, rebinding, isolation. Helper-level evidence only."""
import unittest
from stage_a.errors import Refusal
from stage_a.gateway import v038 as V
I = V.FinalResolutionIdentity

def lane(name, ml=False, **over):
    cls = "ML_PACKAGE" if ml else "FW_PACKAGE"
    f = {k: "x-" + name for k in V.H1_REQUIRED}
    f.update(ISSUER="TRACKER_CONSUMER_GATEWAY", PACKAGE_CLASS=cls, TARGET_CONSUMER="BOTH", CONSUMER_ID=name, REQUEST_ID="request",
             RESOLUTION_VISIBILITY_WATERMARK="w", MANIFEST_OR_DATASET_BINDING_ID="b-" + name)
    if ml: f.update(ML_MANIFEST_CLASS="m", GENERATION_AUTHORITY_CLASS="g")
    f.update(over); return f
def pair(): return lane("FW"), lane("ML", ml=True)
def ids(): return I("FW", "b-FW", "s", "w"), I("ML", "b-ML", "s", "w")
def refused(fn, *a):
    try: fn(*a)
    except Refusal as e: return e.code
    return None

class BothSeparation(unittest.TestCase):
    def test_distinct_correct_lanes_pass(self): V.check_both_separation(*pair())
    def test_each_shared_identity_field_refused(self):
        for f in V.BOTH_DISTINCT_FIELDS:
            fw, ml = pair(); ml[f] = fw[f]
            self.assertEqual(refused(V.check_both_separation, fw, ml), "BOTH_LANES_SHARE_IDENTITY_FIELD", f)
    def test_swapped_lane_labels_refused(self):
        fw, ml = pair(); fw["CONSUMER_ID"], ml["CONSUMER_ID"] = "ML", "FW"
        self.assertEqual(refused(V.check_both_separation, fw, ml), "BOTH_LANE_CONSUMER_ID_WRONG")
    def test_unknown_or_arbitrary_consumer_label_refused(self):
        for bad in ("WRONG_FW", "OTHER_AUTHORIZED", "", "fw", "FORWARD_WALK"):
            fw, ml = pair(); fw["CONSUMER_ID"] = bad
            self.assertEqual(refused(V.check_both_separation, fw, ml), "BOTH_LANE_CONSUMER_ID_WRONG", bad)
        fw, ml = pair(); ml["CONSUMER_ID"] = "FW"
        self.assertEqual(refused(V.check_both_separation, fw, ml), "BOTH_LANE_CONSUMER_ID_WRONG")
    def test_same_record_in_both_slots_refused(self):
        fw, _ = pair(); self.assertIsNotNone(refused(V.check_both_separation, fw, dict(fw)))
    def test_wrong_package_class_refused(self):
        fw, ml = pair(); fw["PACKAGE_CLASS"] = "ML_PACKAGE"; ml["PACKAGE_CLASS"] = "FW_PACKAGE"
        self.assertEqual(refused(V.check_both_separation, fw, ml), "BOTH_LANE_PACKAGE_CLASS_MISMATCH")
    def test_neutral_package_class_refused_in_both(self):
        fw, ml = pair(); fw["PACKAGE_CLASS"] = "NEUTRAL_GOVERNED_PACKAGE"
        self.assertEqual(refused(V.check_both_separation, fw, ml), "BOTH_LANE_PACKAGE_CLASS_MISMATCH")
    def test_target_must_be_both(self):
        fw, ml = pair(); fw["TARGET_CONSUMER"] = "FORWARD_WALK"
        self.assertEqual(refused(V.check_both_separation, fw, ml), "BOTH_LANE_TARGET_NOT_BOTH")
    def test_fw_lane_is_h1_checked(self):
        fw, ml = pair(); del fw["PURPOSE"]
        self.assertEqual(refused(V.check_both_separation, fw, ml), "H1_FIELD_MISSING")
    def test_ml_lane_needs_ml_fields(self):
        fw, ml = pair(); del ml["ML_MANIFEST_CLASS"]
        self.assertEqual(refused(V.check_both_separation, fw, ml), "H1_FIELD_MISSING")

class BindingIdentityAgreement(unittest.TestCase):
    def test_identity_consumer_must_match_binding(self):
        self.assertEqual(refused(V.check_binding_matches_identity, lane("FW"), I("ML", "b-FW", "s", "w")), "IDENTITY_CONSUMER_DIFFERS_FROM_BINDING")
    def test_identity_binding_id_must_match_binding(self):
        self.assertEqual(refused(V.check_binding_matches_identity, lane("FW"), I("FW", "b-OTHER", "s", "w")), "IDENTITY_BINDING_DIFFERS_FROM_BINDING")
        self.assertEqual(refused(V.check_binding_matches_identity, lane("FW"), I("FW", None, "s", "w")), "IDENTITY_BINDING_DIFFERS_FROM_BINDING")
    def test_no_binding_id_in_h1_does_not_constrain(self):
        h = lane("FW"); h["MANIFEST_OR_DATASET_BINDING_ID"] = None
        self.assertIsNone(refused(V.check_binding_matches_identity, h, I("FW", None, "s", "w")))

class BothResolution(unittest.TestCase):
    def test_wrong_identity_labels_refused_before_any_evaluation(self):          # reproduction (A)
        s = V.FinalResolutionStore(); ran = []
        fw, ml = pair()
        self.assertEqual(refused(V.resolve_both, s, fw, ml, I("WRONG_FW", "b-FW", "s", "w"), I("WRONG_ML", "b-ML", "s", "w"),
                                 lambda: ran.append(1), lambda: ran.append(2)), "IDENTITY_CONSUMER_DIFFERS_FROM_BINDING")
        self.assertEqual((ran, s.evaluations), ([], 0))
    def test_swapped_identities_refused(self):
        fw, ml = pair(); a, b = ids()
        self.assertIsNotNone(refused(V.resolve_both, V.FinalResolutionStore(), fw, ml, b, a, lambda: 1, lambda: 2))
    def test_cross_lane_binding_refused(self):                                  # FW binding id used in ML identity
        fw, ml = pair(); a, _ = ids()
        self.assertEqual(refused(V.resolve_both, V.FinalResolutionStore(), fw, ml, a, I("ML", "b-FW", "s", "w"), lambda: 1, lambda: 2),
                         "IDENTITY_BINDING_DIFFERS_FROM_BINDING")
    def test_one_lane_failure_leaves_other_untouched_and_replay_reuses(self):
        s = V.FinalResolutionStore(); fw, ml = pair(); a, b = ids()
        def bad(): raise Refusal("x", code="ML_EVAL_FAIL")
        r = V.resolve_both(s, fw, ml, a, b, lambda: "fw-out", bad)
        self.assertEqual(r, {"FW": ("RESOLVED", "fw-out"), "ML": ("REFUSED", "ML_EVAL_FAIL")})
        r2 = V.resolve_both(s, fw, ml, a, b, lambda: "CHANGED", lambda: "ml-out")
        self.assertEqual(r2, {"FW": ("RESOLVED", "fw-out"), "ML": ("RESOLVED", "ml-out")})
        self.assertEqual(s.evaluations, 3)                                      # fw once, ml twice (failed lane may retry)
    def test_ordinary_request_with_suffix_looking_id_does_not_collide(self):    # reproduction (B)
        s = V.FinalResolutionStore(); fw, ml = pair(); a, b = ids()
        s.resolve("request#FORWARD_WALK", I("FW", None, "other", "w"), lambda: "ordinary")
        r = V.resolve_both(s, fw, ml, a, b, lambda: "fw", lambda: "ml")
        self.assertEqual(r, {"FW": ("RESOLVED", "fw"), "ML": ("RESOLVED", "ml")})
    def test_ordinary_resolve_of_the_parent_request_id_is_isolated_per_consumer_and_still_rebind_checked(self):
        s = V.FinalResolutionStore(); fw, ml = pair(); a, b = ids()
        V.resolve_both(s, fw, ml, a, b, lambda: "fw", lambda: "ml")
        self.assertEqual(s.resolve("request", a, lambda: "never"), "fw")                          # same identity: reused
        self.assertEqual(refused(s.resolve, "request", I("FW", "b-FW", "other-scope", "w"), lambda: 1), "REQUEST_ID_REBOUND_TO_OTHER_IDENTITY")
    def test_caller_request_id_is_preserved_unchanged(self):
        s = V.FinalResolutionStore(); fw, ml = pair(); a, b = ids()
        V.resolve_both(s, fw, ml, a, b, lambda: 1, lambda: 2)
        self.assertEqual(sorted(s._req_ids), [("FW", "request"), ("ML", "request")])
    def test_lane_rebinding_within_a_consumer_refused(self):
        s = V.FinalResolutionStore(); fw, ml = pair(); a, b = ids()
        V.resolve_both(s, fw, ml, a, b, lambda: 1, lambda: 2)
        fw2 = lane("FW", CONSUMER_BINDING_ID="x2", BOUND_PAYLOAD_OR_PACKAGE_ID="x2", PACKAGE_HASH="x2", FINAL_PACKAGE_HASH="x2", MANIFEST_OR_DATASET_BINDING_ID="b-FW2")
        r = V.resolve_both(s, fw2, ml, I("FW", "b-FW2", "s", "w"), b, lambda: 9, lambda: 9)
        self.assertEqual(r["FW"], ("REFUSED", "REQUEST_ID_REBOUND_TO_OTHER_IDENTITY")); self.assertEqual(r["ML"], ("RESOLVED", 2))
    def test_pair_defect_alone_refuses_before_evaluation(self):
        s = V.FinalResolutionStore(); fw, ml = pair(); ml["PACKAGE_HASH"] = fw["PACKAGE_HASH"]; a, b = ids()
        self.assertEqual(refused(V.resolve_both, s, fw, ml, a, b, lambda: 1, lambda: 2), "BOTH_LANES_SHARE_IDENTITY_FIELD")
        self.assertEqual(s.evaluations, 0)
    def test_same_identity_for_both_lanes_refused(self):
        fw, ml = pair(); a, _ = ids()
        self.assertIsNotNone(refused(V.resolve_both, V.FinalResolutionStore(), fw, ml, a, a, lambda: 1, lambda: 2))
if __name__ == "__main__": unittest.main()
