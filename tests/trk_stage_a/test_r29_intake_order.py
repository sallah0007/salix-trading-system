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

from stage_a.composer import order_authority as OA
from stage_a.composer.build_gate import accept_build_start as abs_
from .fixtures import Rig, package, ANCHOR, SIM_CONF
from stage_a.tracker.quant_intake_adapter import admit
SRC = "SRC-BINDING-1"
def issue(claims, r=None, l=None, **k): return OA.issue_order(claims, r or rec(), lk() if l is None else l, **dict(dict(subject_key="SUBJ-1", source_binding_hash=SRC, issued_by="MANAGER"), **k))
def br(**k): return dict(dict((f, "x") for f in IN.CONSUMER_LOCAL_ORDER_FIELDS), **dict(dict(CANDIDATE_IDENTITY="cand-1", EXPECTED_DELIVERY_CONTRACT="edc1", OUTCOME_INFORMATION_ACCESS="FORBIDDEN"), **k))

class TrackerIssuedOrder(unittest.TestCase):
    def test_only_proceed_issues_through_ClaimService_and_is_idempotent_across_restart(self):
        rig = Rig(); c = rig.claims; r = issue(c); self.assertEqual(r["status"], "ISSUED"); oid = r["order_id"]
        o = c.order(oid); self.assertEqual((o["issued_by"], o["constraints"]["CANDIDATE_IDENTITY"], o["constraints"]["REQUEST_SCHEMA_VERSION"], o["constraints"]["FORBIDDEN_INPUTS"]), ("MANAGER", "cand-1", "1", "x"))
        self.assertEqual(c.lineage(oid), ["ORDER_ISSUED"])                                                                                  # the SAME journal the pipeline reads
        self.assertEqual(issue(c)["status"], "ATTACHED_EXISTING_IDEMPOTENT")
        from tracker_component.claims import ClaimService; c2 = ClaimService(rig.claims_journal, ANCHOR); self.assertEqual(c2.order(oid)["constraints"]["REQUESTER_ID"], "mgr-1")
        bad = issue(c, l=lk(REGISTRY_LOOKUP=1)); self.assertEqual((bad["status"], bad["order_id"]), (IN.FAIL_CLOSED, None))
        self.assertEqual(issue(c, rec(CANDIDATE_IDENTITY="other"), {})["order_id"], None)
        self.assertEqual(code(OA.issue_order, c, rec(), lk(), subject_key="", source_binding_hash=SRC, issued_by="M"), "ORDER_AUTHORITY_INPUT_MISSING")
        self.assertFalse(hasattr(__import__("stage_a.core.tracker_core", fromlist=["TrackerCore"]).TrackerCore, "issue_order"))      # no second authority in Core
    def test_same_candidate_other_consumer_attaches_provenance_but_changed_constraints_are_not_coalesced(self):
        c = Rig().claims; a = issue(c); ml = rec(TARGET_CONSUMER="MACHINE_LEARNING", REQUESTER_TYPE="AI", REQUESTER_ID="ai-1")
        b = issue(c, ml); self.assertEqual((b["status"], b["order_id"]), ("ATTACHED_AS_PROVENANCE", a["order_id"])); self.assertEqual(len(c.order_provenance(a["order_id"])), 1)
        self.assertEqual(issue(c, ml)["status"], "ATTACHED_EXISTING_IDEMPOTENT")
        d = issue(c, rec(CANDIDATE_IDENTITY="cand-2"), subject_key="SUBJ-2"); self.assertEqual(d["status"], "ISSUED"); self.assertNotEqual(d["order_id"], a["order_id"])      # unrelated candidate: its own order
        for k, v in (("FORBIDDEN_INPUTS", "changed"), ("EXPECTED_DELIVERY_CONTRACT", "edc2"), ("OUTCOME_INFORMATION_ACCESS", "PERMITTED_UNDER_DECLARED_FITTING_CONTRACT"), ("SCOPE", "other"), ("ALLOWED_INPUTS", "y")):
            x = issue(c, rec(**{k: v, "RESEARCH_FAMILY_REFERENCE": "fam"}, REQUESTER_ID="mgr-9")); self.assertEqual(x["status"], "REVIEW_REQUIRED", k); self.assertTrue(x["reasons"][0].startswith("ORDER_CONSTRAINTS_CONFLICT") and k in x["reasons"][0], k)
        self.assertEqual(len(c.order_provenance(a["order_id"])), 1)                                                                          # nothing appended by the refused changes
        self.assertEqual(issue(c, subject_key="SUBJ-OTHER", r=rec(REQUESTER_ID="mgr-8"))["status"], "REVIEW_REQUIRED")                      # different subject binding is not coalesced either
    def test_build_gate_verifies_the_claim_order_and_requires_every_constraint(self):
        c = Rig().claims; o = issue(c)
        self.assertEqual(abs_(c, o["order_id"], br()).issued_by, "MANAGER")                                                              # positive
        self.assertEqual(code(abs_, c, rec(), br()), "COMPOSER_BUILD_NEEDS_TRACKER_ORDER_ID"); self.assertEqual(code(abs_, c, c.order(o["order_id"]), br()), "COMPOSER_BUILD_NEEDS_TRACKER_ORDER_ID")
        self.assertEqual(code(abs_, c, "forged-id", br()), "COMPOSER_BUILD_WITHOUT_TRACKER_ORDER"); self.assertEqual(code(abs_, Rig().claims, o["order_id"], br()), "COMPOSER_BUILD_WITHOUT_TRACKER_ORDER")
        self.assertEqual(code(abs_, object(), o["order_id"], br()), "COMPOSER_BUILD_NEEDS_CLAIM_AUTHORITY")
        for k, v in (("CANDIDATE_IDENTITY", "x"), ("EXPECTED_DELIVERY_CONTRACT", "y"), ("OUTCOME_INFORMATION_ACCESS", "PERMITTED_UNDER_DECLARED_FITTING_CONTRACT"), ("FORBIDDEN_INPUTS", "changed"), ("ALLOWED_INPUTS", "z"), ("SCOPE", "w"), ("VINTAGE_MODE", "v")):
            self.assertEqual(code(abs_, c, o["order_id"], br(**{k: v})), "COMPOSER_BUILD_DIFFERS_FROM_ORDER", k)                            # contradiction (FORBIDDEN_INPUTS bound 'x', build says 'changed')
        for k in IN.CONSUMER_LOCAL_ORDER_FIELDS + ("EXPECTED_DELIVERY_CONTRACT",): b = br(); del b[k]; self.assertEqual(code(abs_, c, o["order_id"], b), "COMPOSER_BUILD_OMITS_ORDER_CONSTRAINT", k)
    def test_unadmitted_anchor_revocation_and_expiry_refuse_the_gate(self):
        c = Rig().claims
        self.assertEqual(code(abs_, c, issue(c, r=rec(CANDIDATE_IDENTITY="c-a"), issued_by="ROGUE")["order_id"], br(CANDIDATE_IDENTITY="c-a")), "COMPOSER_BUILD_ORDER_NOT_VERIFIED:ISSUER_NOT_ANCHORED")
        self.assertEqual(code(abs_, c, issue(c, r=rec(CANDIDATE_IDENTITY="c-b"), source_binding_hash="OTHER")["order_id"], br(CANDIDATE_IDENTITY="c-b")), "COMPOSER_BUILD_ORDER_NOT_VERIFIED:SOURCE_BINDING_MISMATCH")
        e = issue(c, r=rec(CANDIDATE_IDENTITY="c-c"), valid_until_seq=0)["order_id"]; self.assertEqual(code(abs_, c, e, br(CANDIDATE_IDENTITY="c-c")), "COMPOSER_BUILD_ORDER_NOT_VERIFIED:ORDER_EXPIRED")
        g = issue(c, r=rec(CANDIDATE_IDENTITY="c-d"))["order_id"]; abs_(c, g, br(CANDIDATE_IDENTITY="c-d")); c.revoke_order(g, "x"); self.assertEqual(code(abs_, c, g, br(CANDIDATE_IDENTITY="c-d")), "COMPOSER_BUILD_ORDER_NOT_VERIFIED:ORDER_REVOKED")
    def test_order_gate_to_actual_pipeline_in_simulation_and_qualified_stays_held(self):
        rig = Rig(); oid = OA.order_id_for("cand-1"); p = package(order_id=oid); sk = admit(p, accepted_fit_generations=rig.fits, conformance=SIM_CONF).subject_key
        o = issue(rig.claims, subject_key=sk); self.assertEqual(o["order_id"], oid)
        abs_(rig.claims, oid, br())                                                                                                          # gate verifies the SAME ClaimService order the pipeline reserves
        out = rig.pipe.run(p); self.assertEqual(rig.claims.claim("CLAIM:" + p.request_id)["state"], "CONSUMED"); self.assertEqual(rig.claims.lineage(oid, p.request_id), ["ORDER_ISSUED", "REQUEST_CLAIM_EXISTS"])
        p2 = package(request_id="REQ-2", attempt_id="ATT-2", order_id=OA.order_id_for("never-issued")); r2 = rig.pipe.run(p2); self.assertIsNone(rig.claims.claim("CLAIM:REQ-2"))      # no order => no claim: the pipeline needs the journaled order
        q = Rig(simulation=False); self.assertEqual(code(abs_, q.claims, issue(q.claims, issued_by="UNADMITTED")["order_id"], br()), "COMPOSER_BUILD_ORDER_NOT_VERIFIED:ISSUER_NOT_ANCHORED")      # unadmitted principal: qualified use held

class HealthBlastRadius(unittest.TestCase):
    def test_dependents_blocked_and_unrelated_baseline_positive_and_required_unknown_fails_closed(self):
        from .test_r24_core import ver
        c = mk()
        c.declare_dependency("MID", "UP"); c.declare_dependency("TOP", "MID")                                                            # edges first: Health recorded under another basis would be UNKNOWN
        for s in ("UP", "MID", "TOP", "BASE"): ver(c, s, version="1", at=11, age=50)
        self.assertEqual(c.blast_radius("UP")["dependents"], ["MID", "TOP"]); self.assertEqual(c.blast_radius("BASE")["dependents"], []); self.assertEqual(c.blast_radius("TOP")["dependents"], [])
        self.assertTrue(c.gateway_health("TOP", "1", 12, None, 11).acceptable and c.gateway_health("BASE", "1", 12, None, 11).acceptable)          # before: positive controls
        c.quarantine("UP", "DEFECT")
        self.assertFalse(c.gateway_health("TOP", "1", 13, None, 11).acceptable); self.assertFalse(c.gateway_health("MID", "1", 13, None, 11).acceptable)
        self.assertTrue(c.gateway_health("BASE", "1", 13, None, 11).acceptable)                                                                 # unrelated baseline unaffected
        self.assertFalse(c.gateway_health("NEVER_VERIFIED", "1", 13, None, 11).acceptable)                                                      # required, unknown => held, not healthy

class HealthRequiredAncestry(unittest.TestCase):
    def test_undeclared_ancestry_fails_closed_proven_empty_and_unrelated_pass_and_completeness_is_unadmitted(self):
        from .test_r24_core import ver
        c = mk(); c.declare_dependency("MID", "UP"); c.declare_dependency("TOP", "MID")
        for s in ("UP", "MID", "TOP", "BASE", "LEAF"): ver(c, s, version="1", at=11, age=50)
        ok = lambda s, **k: c.gateway_health(s, "1", 12, None, 11, **k).acceptable
        self.assertTrue(ok("TOP") and ok("TOP", require_ancestry=True) is False)                                                         # not required: unchanged; required but undeclared => UNKNOWN, fails closed
        c.declare_ancestry_complete("TOP", "src-1"); c.declare_ancestry_complete("MID", "src-1")
        self.assertFalse(ok("TOP", require_ancestry=True))                                                                              # UP (an ancestor) still undeclared: the unknown propagates to dependents
        c.declare_ancestry_complete("UP", "src-1"); self.assertTrue(ok("TOP", require_ancestry=True))                                  # complete chain, healthy: positive
        c.declare_ancestry_complete("BASE", "src-2"); self.assertTrue(ok("BASE", require_ancestry=True))                               # PROVEN-EMPTY (declared, no edges) is not UNKNOWN
        self.assertFalse(ok("LEAF", require_ancestry=True)); self.assertTrue(ok("BASE", require_ancestry=True))                         # an unrelated undeclared subject does not affect BASE, and BASE's declaration does not rescue LEAF
        self.assertEqual(c._replay()["anc"]["BASE"]["admission"], "CALLER_ASSERTED_UNADMITTED")                                         # completeness is supplied, not verified
        self.assertEqual(code(c.declare_dependency, "TOP", "BASE"), "ANCESTRY_ALREADY_DECLARED_COMPLETE")                               # late edge contradicts the assertion
        c.quarantine("UP", "DEFECT"); self.assertFalse(ok("TOP", require_ancestry=True)); self.assertTrue(ok("BASE", require_ancestry=True))
        self.assertEqual(code(c.declare_ancestry_complete, "", "s"), "ANCESTRY_DECLARATION_INVALID")
    def test_snapshot_binds_the_ancestry_requirement(self):
        from .test_r24_core import ver
        from stage_a.core.tracker_core import CoreHealthSnapshot
        c = mk(); ver(c, "S", version="1", at=11, age=50); c.declare_ancestry_complete("S", "src")
        a = c.gateway_health("S", "1", 12, None, 11, require_ancestry=False); b = c.gateway_health("S", "1", 12, None, 11, require_ancestry=True)
        self.assertEqual((a.require_ancestry, b.require_ancestry), (False, True))
        self.assertNotEqual(c._snapshot_id("S", "1", None, None, 11, True, "SIMULATION", 12, "", False, False, False), c._snapshot_id("S", "1", None, None, 11, True, "SIMULATION", 12, "", False, False, True))
