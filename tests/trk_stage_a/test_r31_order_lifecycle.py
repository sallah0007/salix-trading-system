import unittest
from stage_a.composer import intake as IN, order_authority as OA
from stage_a.composer.build_gate import accept_build_start as G
from stage_a.ml import generation_lifecycle as GL
from .fixtures import Rig
from .test_r29_intake_order import rec, lk, issue, code
from .test_r29_generation_lifecycle import reg, ev
F = IN.CONSUMER_LOCAL_ORDER_FIELDS
def prefixed(side, **k):
    r = rec(**k)
    for f in F: r[side + ":" + f] = r.pop(f)
    return r
def bld(side=None, **k):
    d = dict(CANDIDATE_IDENTITY="cand-1", EXPECTED_DELIVERY_CONTRACT="edc1", OUTCOME_INFORMATION_ACCESS="FORBIDDEN")
    for f in F: d[(side + ":" if side else "") + f] = "x"
    d.update(k); return d

class PrefixedLocalContract(unittest.TestCase):
    def test_fw_prefixed_only_is_bound_omission_and_contradiction_refused_and_positive_control(self):
        c = Rig().claims; o = issue(c, prefixed("FW_LOCAL"))["order_id"]; self.assertEqual(c.order(o)["constraints"]["FW_LOCAL:FORBIDDEN_INPUTS"], "x")
        self.assertEqual(G(c, o, bld("FW_LOCAL")).order_id, o)                                                                      # positive: prefixed restated
        for f in F:
            self.assertEqual(code(G, c, o, bld("FW_LOCAL", **{"FW_LOCAL:" + f: "changed"})), "COMPOSER_BUILD_DIFFERS_FROM_ORDER", f)         # the reproduced hole: all prefixed values changed were ACCEPTED
            b = bld("FW_LOCAL"); del b["FW_LOCAL:" + f]; self.assertEqual(code(G, c, o, b), "COMPOSER_BUILD_OMITS_ORDER_CONSTRAINT", f)
        self.assertEqual(code(G, c, o, bld()), "COMPOSER_BUILD_OMITS_ORDER_CONSTRAINT")                                               # no precedence invented: plain does not stand in for prefixed
        self.assertEqual(code(G, c, o, dict(bld("FW_LOCAL"), **{"ML_LOCAL:SCOPE": "x"})), "COMPOSER_BUILD_DIFFERS_FROM_ORDER")        # another consumer's local field is unbound for a FW-only order
    def test_routing_ml_only_both_and_unapplicable_prefixed_not_bound(self):
        c = Rig().claims
        m = issue(c, prefixed("ML_LOCAL", TARGET_CONSUMER="MACHINE_LEARNING"))["order_id"]; self.assertEqual(G(c, m, bld("ML_LOCAL")).order_id, m); self.assertEqual(code(G, c, m, bld("FW_LOCAL")), "COMPOSER_BUILD_OMITS_ORDER_CONSTRAINT")
        r = prefixed("FW_LOCAL", TARGET_CONSUMER="BOTH", CANDIDATE_IDENTITY="cand-b")
        for f in F: r["ML_LOCAL:" + f] = "y"
        b = issue(c, r)["order_id"]; both = dict(bld("FW_LOCAL", CANDIDATE_IDENTITY="cand-b"), **{"ML_LOCAL:" + f: "y" for f in F}); self.assertEqual(G(c, b, both).order_id, b)
        self.assertEqual(code(G, c, b, dict(both, **{"ML_LOCAL:SCOPE": "z"})), "COMPOSER_BUILD_DIFFERS_FROM_ORDER"); x = dict(both); del x["ML_LOCAL:SCOPE"]; self.assertEqual(code(G, c, b, x), "COMPOSER_BUILD_OMITS_ORDER_CONSTRAINT")
        r2 = prefixed("FW_LOCAL", CANDIDATE_IDENTITY="cand-u"); r2["ML_LOCAL:SCOPE"] = "ignored"; u = issue(c, r2)["order_id"]; self.assertNotIn("ML_LOCAL:SCOPE", c.order(u)["constraints"])      # FW-only order does not store a non-applicable ML field
    def test_ambiguous_plain_plus_prefixed_is_reviewed_at_order_and_conflicting_build_refused(self):
        c = Rig().claims; r = rec(); r["FW_LOCAL:SCOPE"] = "different"; x = issue(c, r); self.assertEqual((x["status"], x["order_id"]), ("REVIEW_REQUIRED", None)); self.assertIn("AMBIGUOUS", x["reasons"][0])
        r["FW_LOCAL:SCOPE"] = "x"; o = issue(c, r)["order_id"]; self.assertIsNotNone(o)                                               # same value both ways is not a conflict
        self.assertEqual(code(G, c, o, dict(bld(), **{"FW_LOCAL:SCOPE": "other"})), "COMPOSER_BUILD_DIFFERS_FROM_ORDER")

class FieldSetCoalescing(unittest.TestCase):
    def test_added_or_removed_material_fields_are_reviewed_not_discarded_and_provenance_preserved(self):
        c = Rig().claims; a = issue(c)["order_id"]
        r = rec(); r["FW_LOCAL:FORBIDDEN_INPUTS"] = "new-forbidden-constraint"                                                        # the reproduced case (conflicts with the plain value): reviewed, constraint not lost
        x = issue(c, r); self.assertEqual(x["status"], "REVIEW_REQUIRED"); self.assertIn("FORBIDDEN_INPUTS", x["reasons"][0])
        r = rec(); r["FW_LOCAL:FORBIDDEN_INPUTS"] = "x"; x = issue(c, r); self.assertEqual(x["status"], "REVIEW_REQUIRED"); self.assertIn("FW_LOCAL:FORBIDDEN_INPUTS", x["reasons"][0])      # added key, same value: field set changed => reviewed
        y = rec(RESEARCH_FAMILY_REFERENCE="fam"); self.assertEqual(issue(c, y)["status"], "REVIEW_REQUIRED")                          # added RESEARCH_FAMILY_REFERENCE
        z = rec(); del z["SCOPE"]; self.assertEqual(issue(c, z)["status"], "REVIEW_REQUIRED")                                          # removed (REVIEW at intake: required missing)
        self.assertEqual(len(c.order_provenance(a)), 0)
        ok = issue(c, rec(TARGET_CONSUMER="MACHINE_LEARNING", REQUESTER_TYPE="AI", REQUESTER_ID="ai-1")); self.assertEqual(ok["status"], "ATTACHED_AS_PROVENANCE")   # identical constraints: legitimate provenance
        self.assertEqual(issue(c)["status"], "ATTACHED_EXISTING_IDEMPOTENT"); self.assertEqual(issue(c, rec(TARGET_CONSUMER="MACHINE_LEARNING", REQUESTER_TYPE="AI", REQUESTER_ID="ai-1"))["status"], "ATTACHED_EXISTING_IDEMPOTENT")
    def test_consumer_local_addition_by_another_consumer_is_explicitly_reviewed(self):
        c = Rig().claims; issue(c); r = prefixed("ML_LOCAL", TARGET_CONSUMER="MACHINE_LEARNING", REQUESTER_ID="ai-2", REQUESTER_TYPE="AI")
        x = issue(c, r); self.assertEqual(x["status"], "REVIEW_REQUIRED"); self.assertTrue(x["reasons"][0].startswith("ORDER_CONSTRAINTS_CONFLICT"))

class RiskReducingRevocation(unittest.TestCase):
    def test_superseded_then_revoked_is_allowed_restoration_and_revival_stay_held(self):
        r = reg("M1", "M2"); r.append_lifecycle("M1", "SUPERSEDED", 20, "new gen", "A"); r.append_lifecycle("M1", "REVOKED", 30, "defect", "A")             # reproduced refusal
        self.assertEqual(r.read_class("M1", 10)["class"], "SERVING_ELIGIBLE"); h = r.read_class("M1", 25); self.assertEqual((h["class"], h["later_revoked"]), ("HISTORICAL_READABLE", True))
        self.assertEqual(r.read_class("M1")["class"], "FORENSIC_ONLY"); self.assertFalse(r.eligible("M1")); self.assertEqual(r.read_class("M2")["later_revoked"], False)       # unrelated generation unaffected
        for st in ("COMPLETE_CERTIFIED", "SUPERSEDED", "CANDIDATE"):
            self.assertEqual(code(r.append_lifecycle, "M1", st, 40, "x", "A"), "ML_LIFECYCLE_RESTORATION_HELD", st)                                      # REVOKED revival / un-revoke held
        r2 = reg("M1"); r2.append_lifecycle("M1", "SUPERSEDED", 20, "x", "A"); self.assertEqual(code(r2.append_lifecycle, "M1", "COMPLETE_CERTIFIED", 30, "x", "A"), "ML_LIFECYCLE_RESTORATION_HELD")   # SUPERSEDED -> COMPLETE held
        self.assertEqual(code(r2.append_lifecycle, "M1", "CANDIDATE", 31, "x", "A"), "ML_LIFECYCLE_RESTORATION_HELD")

class DetachedPublicReads(unittest.TestCase):
    def test_returned_order_provenance_and_verified_order_cannot_mutate_the_projection_cache(self):
        rig = Rig(); c = rig.claims; o = issue(c)["order_id"]; issue(c, rec(TARGET_CONSUMER="MACHINE_LEARNING", REQUESTER_TYPE="AI", REQUESTER_ID="ai-1"))
        self.assertEqual(G(c, o, bld()).order_id, o)                                                                                  # genuine positive
        row = c.order(o); row["constraints"]["FORBIDDEN_INPUTS"] = "changed"; row["constraints"]["lookup_refs"]["X"] = "y"
        self.assertEqual(code(G, c, o, bld(FORBIDDEN_INPUTS="changed")), "COMPOSER_BUILD_DIFFERS_FROM_ORDER")                          # reproduced: this used to be ACCEPTED
        self.assertEqual(G(c, o, bld()).order_id, o)
        v = c.verified_order(o); v.constraints["FORBIDDEN_INPUTS"] = "changed2"; v.constraints["applicability"]["FW_LOCAL"] = "NOT_APPLICABLE"
        self.assertEqual(code(G, c, o, bld(FORBIDDEN_INPUTS="changed2")), "COMPOSER_BUILD_DIFFERS_FROM_ORDER")
        pv = c.order_provenance(o); pv[0]["constraints"]["SCOPE"] = "tampered"; self.assertEqual(c.order_provenance(o)[0]["constraints"]["SCOPE"], "x")
        from tracker_component.claims import ClaimService; from .fixtures import ANCHOR
        fresh = ClaimService(rig.claims_journal, ANCHOR); self.assertEqual(fresh.order(o)["constraints"], c.order(o)["constraints"]); self.assertEqual(fresh.order(o)["constraints"]["FORBIDDEN_INPUTS"], "x")      # fresh replay parity
        self.assertEqual(issue(c)["status"], "ATTACHED_EXISTING_IDEMPOTENT")                                                          # coalescing reads the true row too
