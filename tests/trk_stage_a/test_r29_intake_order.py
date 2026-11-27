import dataclasses, unittest
from stage_a.composer import intake as IN
from stage_a.composer.build_gate import accept_build_start
from stage_a.errors import Refusal
from .test_r24_core import mk

def rec(**k):
    d = dict(REQUEST_SCHEMA_VERSION="1", REQUESTER_TYPE="MANAGER", REQUESTER_ID="mgr-1", REQUEST_CLASS="GOVERNED_INTAKE_REQUEST", TARGET_CONSUMER="FORWARD_WALK", REQUEST_CONTEXT="MANUAL_CHECKUP",
             PURPOSE_STATEMENT="bounded purpose", OUTCOME_INFORMATION_ACCESS="FORBIDDEN", REQUESTED_AT=5, IDEA_ORIGIN="o", IDEA_BASIS="b", EXPECTED_DELIVERY_CONTRACT="edc1", CANDIDATE_IDENTITY="cand-1")
    for f in IN.CONSUMER_LOCAL_ORDER_FIELDS: d[f] = "x"
    d.update(k); return d
def lk(**drop): return {l: {"state": "DONE", "ref": "r-" + l} for l in IN.COMMON_LOOKUPS if l not in drop}
def code(f, *a, **k):
    try: f(*a, **k)
    except Refusal as e: return e.code

class Intake(unittest.TestCase):
    def test_positive_control_proceeds_and_is_not_order_authority(self):
        d = IN.evaluate_intake(rec(), "ORDER", lk()); self.assertEqual((d.disposition, d.order_authority), (IN.PROCEED, False))
    def test_every_common_gate_missing_is_fail_closed(self):
        for l in IN.COMMON_LOOKUPS: self.assertEqual(IN.evaluate_intake(rec(), "ORDER", lk(**{l: 1})).disposition, IN.FAIL_CLOSED, l)
        for f in IN.COMMON_FIELDS_ORDER:
            r = rec(); del r[f]; self.assertEqual(IN.evaluate_intake(r, "ORDER", lk()).disposition, IN.FAIL_CLOSED, f)
        self.assertEqual(IN.evaluate_intake(rec(OUTCOME_INFORMATION_ACCESS="PERMITTED_UNDER_DECLARED_FITTING_CONTRACT"), "ORDER", lk()).disposition, IN.FAIL_CLOSED)       # outcome-bearing needs the family ref
        self.assertEqual(IN.evaluate_intake(rec(OUTCOME_INFORMATION_ACCESS="PERMITTED_UNDER_DECLARED_FITTING_CONTRACT", RESEARCH_FAMILY_REFERENCE="fam"), "ORDER", lk()).disposition, IN.PROCEED)
        self.assertEqual(IN.evaluate_intake(rec(), "ORDER", {}).disposition, IN.FAIL_CLOSED)                                                                                    # no lookups at all
        self.assertEqual(IN.evaluate_intake(rec(REQUESTER_ID=""), "ORDER", lk()).disposition, IN.FAIL_CLOSED)
    def test_applicability_is_derived_from_class_and_consumer_only_never_requester(self):
        a = {rt: IN.derive_applicability(rec(REQUESTER_TYPE=rt)) for rt in ("OWNER", "MANAGER", "AI", "FORWARD_WALK")}; self.assertEqual(len({str(v) for v in a.values()}), 1)
        self.assertEqual(IN.derive_applicability(rec(TARGET_CONSUMER="UNKNOWN"))["FW_LOCAL"], "NOT_APPLICABLE"); self.assertEqual(IN.derive_applicability(rec(TARGET_CONSUMER="UNKNOWN"))["ML_LOCAL"], "NOT_APPLICABLE")
        b = IN.derive_applicability(rec(TARGET_CONSUMER="BOTH")); self.assertEqual((b["FW_LOCAL"], b["ML_LOCAL"], b["ADOPTION_GOVERNANCE"]), ("CONSUMER_LOCAL_REQUIRED", "CONSUMER_LOCAL_REQUIRED", "NOT_APPLICABLE"))
        d = IN.evaluate_intake(rec(FIELD_APPLICABILITY="NOT_APPLICABLE"), "ORDER", lk()); self.assertTrue(any("REQUESTER_ASSERTED_APPLICABILITY_DISREGARDED" in r for r in d.reasons)); self.assertEqual(d.field_applicability["FW_LOCAL"], "CONSUMER_LOCAL_REQUIRED")
    def test_consumer_local_missing_reviews_only_for_the_derived_consumer_and_unknown_consumer_reviews(self):
        r = rec(); del r["VINTAGE_MODE"]; self.assertEqual(IN.evaluate_intake(r, "ORDER", lk()).disposition, IN.REVIEW_REQUIRED)
        self.assertEqual(IN.evaluate_intake(dict(r, TARGET_CONSUMER="UNKNOWN"), "ORDER", lk()).disposition, IN.REVIEW_REQUIRED)       # UNKNOWN at ORDER
        self.assertEqual(IN.evaluate_intake(dict(r, TARGET_CONSUMER="UNKNOWN"), "PROPOSAL", {}).disposition, IN.PROCEED)               # allowed at PROPOSAL; unrelated/no consumer-local requirement
        self.assertNotIn("ADOPTION", " ".join(IN.evaluate_intake(r, "ORDER", lk()).reasons))                                            # adoption governance is never demanded by an order
    def test_malformed_record_is_fail_closed_with_the_exact_code(self):
        d = IN.evaluate_intake(rec(REQUEST_CONTEXT="OTHER"), "ORDER", lk()); self.assertEqual((d.disposition, d.reasons), (IN.FAIL_CLOSED, ("REQUEST_OTHER_WITHOUT_GOVERNED_REASON",)))
        self.assertEqual(IN.evaluate_intake(rec(REQUEST_CLASS="ML_DATASET_OR_MODEL_REQUEST"), "ORDER", lk()).disposition, IN.FAIL_CLOSED)       # retired class

class TrackerIssuedOrder(unittest.TestCase):
    def test_only_proceed_issues_a_journaled_order_and_is_idempotent_across_restart(self):
        from stage_a.core.tracker_core import TrackerCore
        c = mk(); r = c.issue_order(rec(), lk(), 10); self.assertEqual(r["status"], "ISSUED"); oid = r["order_id"]
        o = c.order(oid); self.assertEqual((o["issuer"], o["bindings"]["CANDIDATE_IDENTITY"]), ("TRACKER", "cand-1"))
        self.assertEqual(c.issue_order(rec(), lk(), 11)["status"], "ATTACHED_EXISTING_IDEMPOTENT")
        c2 = TrackerCore(c._j, simulation=True); self.assertEqual(c2.order(oid)["bindings"]["REQUESTER_ID"], "mgr-1")
        bad = c.issue_order(rec(), lk(REGISTRY_LOOKUP=1), 12); self.assertEqual((bad["status"], bad["order_id"]), (IN.FAIL_CLOSED, None))
        self.assertEqual(c.issue_order(rec(CANDIDATE_IDENTITY="other"), {}, 13)["order_id"], None)
    def test_same_candidate_other_consumer_or_requester_attaches_provenance_not_a_second_order(self):
        c = mk(); a = c.issue_order(rec(), lk(), 10); b = c.issue_order(rec(TARGET_CONSUMER="MACHINE_LEARNING", REQUESTER_TYPE="AI", REQUESTER_ID="ai-1"), lk(), 11)
        self.assertEqual((b["status"], b["order_id"]), ("ATTACHED_AS_PROVENANCE", a["order_id"])); self.assertEqual(len(c.order_provenance(a["order_id"])), 1)
        self.assertEqual(c.issue_order(rec(TARGET_CONSUMER="MACHINE_LEARNING", REQUESTER_TYPE="AI", REQUESTER_ID="ai-1"), lk(), 12)["status"], "ATTACHED_EXISTING_IDEMPOTENT")
        d = c.issue_order(rec(CANDIDATE_IDENTITY="cand-2"), lk(), 13); self.assertEqual(d["status"], "ISSUED"); self.assertNotEqual(d["order_id"], a["order_id"])      # unrelated candidate: its own order
    def test_build_gate_accepts_only_journaled_order_ids_not_equal_requests_or_objects(self):
        c = mk(); o = c.issue_order(rec(), lk(), 10); br = dict(CANDIDATE_IDENTITY="cand-1", EXPECTED_DELIVERY_CONTRACT="edc1", OUTCOME_INFORMATION_ACCESS="FORBIDDEN")
        self.assertEqual(accept_build_start(c, o["order_id"], br)["issuer"], "TRACKER")                                                                                 # positive
        self.assertEqual(code(accept_build_start, c, rec(), br), "COMPOSER_BUILD_NEEDS_TRACKER_ORDER_ID")                                                               # the request itself is not an order
        self.assertEqual(code(accept_build_start, c, c.order(o["order_id"]), br), "COMPOSER_BUILD_NEEDS_TRACKER_ORDER_ID")                                              # a copy of the order object is not an order id
        self.assertEqual(code(accept_build_start, c, "forged-id", br), "COMPOSER_BUILD_WITHOUT_TRACKER_ORDER")
        self.assertEqual(code(accept_build_start, mk(), o["order_id"], br), "COMPOSER_BUILD_WITHOUT_TRACKER_ORDER")                                                     # another journal never issued it
        for k, v in (("CANDIDATE_IDENTITY", "x"), ("EXPECTED_DELIVERY_CONTRACT", "y"), ("OUTCOME_INFORMATION_ACCESS", "PERMITTED_UNDER_DECLARED_FITTING_CONTRACT")):
            self.assertEqual(code(accept_build_start, c, o["order_id"], dict(br, **{k: v})), "COMPOSER_BUILD_DIFFERS_FROM_ORDER")
