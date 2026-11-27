"""R16/R17: ORDER_READY outcome-access declaration (Composer V9 s7A) bound to the governed order record, and the s28 outcome-access check connected to intake AND pipeline.
Evidence is Tracker-originated (ConformanceEvidence), never taken from the package. Missing/unknown/conflicting declarations refuse; FORBIDDEN needs determined 'not consulted'
evidence; PERMITTED_UNDER_DECLARED_FITTING_CONTRACT is HELD (no verifiable contract reference in any source read). Nothing is defaulted. No real verification path exists."""
import copy, dataclasses, unittest
from stage_a.errors import Refusal
from stage_a.composer.request_record import check_request_record
from stage_a.tracker import build_output_check as B
from stage_a.tracker.quant_intake_adapter import admit, QUANT_FEATURE, FAILED_REQUESTED_BUILD, NO_QUANT_FEATURE
from stage_a.coordination import transition_record as T
from stage_a.replay import replay
from tracker_component.order import ConstructionOrder
from tests.trk_stage_a.fixtures import Rig, package, REQUEST_RECORD

P = "PERMITTED_UNDER_DECLARED_FITTING_CONTRACT"
def pk(order=..., out=...):
    p = package(); rr = copy.deepcopy(p.request_record); bo = dict(p.build_output)
    if order is not ...:
        if order is None: rr.pop("OUTCOME_INFORMATION_ACCESS", None)
        else: rr["OUTCOME_INFORMATION_ACCESS"] = order
    if out is not ...:
        if out is None: bo.pop("OUTCOME_INFORMATION_ACCESS", None)
        else: bo["OUTCOME_INFORMATION_ACCESS"] = out
    return dataclasses.replace(p, request_record=rr, build_output=bo)
EV = lambda v: B.ConformanceEvidence(v, "SIMULATED:test-evidence")
def dims(a, d): return [c for x, c in a.failed if x == d]
def A(p, ev=None): return admit(p, accepted_fit_generations={}, conformance=ev)
class OrderReady(unittest.TestCase):
    def test_order_without_declaration_refuses_at_the_order_seam(self):
        rr = dict(REQUEST_RECORD); del rr["OUTCOME_INFORMATION_ACCESS"]
        with self.assertRaises(Refusal) as c: check_request_record(rr, "ORDER")
        self.assertEqual(c.exception.code, "ORDER_OUTCOME_ACCESS_DECLARATION_MISSING")
        self.assertEqual(check_request_record(rr, "PROPOSAL"), "OK")                      # the declaration is an ORDER_READY duty, not a proposal duty
    def test_unknown_declaration_refuses(self):
        for bad in ("", "forbidden", "ALLOWED", 1, True):
            with self.assertRaises(Refusal) as c: check_request_record(dict(REQUEST_RECORD, OUTCOME_INFORMATION_ACCESS=bad), "ORDER")
            self.assertEqual(c.exception.code, "ORDER_OUTCOME_ACCESS_DECLARATION_UNKNOWN", bad)
    def test_both_legal_values_pass_the_order_seam(self):
        for v in ("FORBIDDEN", P): self.assertEqual(check_request_record(dict(REQUEST_RECORD, OUTCOME_INFORMATION_ACCESS=v), "ORDER"), "OK")
    def test_reported_reproduction_no_declaration_anywhere_no_longer_admits(self):
        a = A(pk(order=None, out=None), EV(False))
        self.assertEqual((a.classification, dims(a, "REQUEST_RECORD")), (FAILED_REQUESTED_BUILD, ["ORDER_OUTCOME_ACCESS_DECLARATION_MISSING"]))
    def test_unknown_order_declaration_refuses_through_intake(self):
        self.assertEqual(dims(A(pk(order="MAYBE", out="MAYBE"), EV(False)), "REQUEST_RECORD"), ["ORDER_OUTCOME_ACCESS_DECLARATION_UNKNOWN"])
class DirectSeamCodes(unittest.TestCase):
    def test_order_seam_refuses_a_near_miss_value_by_code(self):
        rec = dict(REQUEST_RECORD, OUTCOME_INFORMATION_ACCESS="OTHER")
        try: check_request_record(rec, "ORDER"); self.fail("accepted")
        except Refusal as e: self.assertEqual(e.code, "ORDER_OUTCOME_ACCESS_DECLARATION_UNKNOWN")
    def test_conformance_validates_the_order_declaration_itself_before_comparing(self):
        for bad in (None, "OTHER", "forbidden"):
            for bo in ({}, {"OUTCOME_INFORMATION_ACCESS": bad}):
                try: B.check_conformance(bo, None, bad); self.fail("accepted")
                except Refusal as e: self.assertEqual(e.code, "ORDER_OUTCOME_ACCESS_DECLARATION_UNKNOWN", (bad, bo))
class BoundToTheOrder(unittest.TestCase):
    def test_returned_package_must_carry_the_declaration(self):
        self.assertEqual(dims(A(pk(out=None), EV(False)), "BUILD_CONFORMANCE"), ["BUILD_OUTPUT_OUTCOME_ACCESS_DECLARATION_MISSING"])
    def test_conflicting_declaration_refused_both_directions(self):
        self.assertEqual(dims(A(pk(order="FORBIDDEN", out=P), EV(False)), "BUILD_CONFORMANCE"), ["OUTCOME_ACCESS_DECLARATION_CONFLICT"])
        self.assertEqual(dims(A(pk(order=P, out="FORBIDDEN"), EV(False)), "BUILD_CONFORMANCE"), ["OUTCOME_ACCESS_DECLARATION_CONFLICT"])
    def test_package_cannot_upgrade_itself_over_a_forbidden_order(self):
        a = A(pk(order="FORBIDDEN", out=P), EV(False)); self.assertNotEqual(a.classification, QUANT_FEATURE)
    def test_permitted_is_held_not_certified(self):
        self.assertEqual(dims(A(pk(order=P, out=P), EV(False)), "BUILD_CONFORMANCE"), ["PERMITTED_FITTING_CONTRACT_NOT_VERIFIABLE"])
class ForbiddenNeedsTrackerEvidence(unittest.TestCase):
    def test_no_evidence_held(self): self.assertEqual(dims(A(pk()), "BUILD_CONFORMANCE"), ["OUTCOME_ACCESS_UNVERIFIED_UNDER_FORBIDDEN"])
    def test_undetermined_held(self): self.assertEqual(dims(A(pk(), EV(None)), "BUILD_CONFORMANCE"), ["OUTCOME_ACCESS_UNVERIFIED_UNDER_FORBIDDEN"])
    def test_consulted_fails(self): self.assertEqual(dims(A(pk(), EV(True)), "BUILD_CONFORMANCE"), ["OUTCOME_INFORMATION_CONSULTED_UNDER_FORBIDDEN"])
    def test_positive_control(self):
        a = A(pk(), EV(False)); self.assertEqual((a.classification, a.failed), (QUANT_FEATURE, []))
    def test_package_fields_cannot_vouch_for_the_build(self):
        p = pk(); p = dataclasses.replace(p, build_output=dict(p.build_output, OUTCOME_ACCESS_CONSULTED=False, OUTCOME_INFORMATION_CONSULTED_BY_VERIFICATION=False))
        self.assertEqual(dims(A(p), "BUILD_CONFORMANCE"), ["OUTCOME_ACCESS_UNVERIFIED_UNDER_FORBIDDEN"])
    def test_malformed_evidence_refused(self):
        self.assertEqual(dims(admit(pk(), accepted_fit_generations={}, conformance="PASS"), "BUILD_CONFORMANCE"), ["CONFORMANCE_EVIDENCE_MALFORMED"])
        for bad in ("yes", 1, 0):
            with self.assertRaises(Refusal) as c: B.ConformanceEvidence(bad, "r")
            self.assertEqual(c.exception.code, "CONFORMANCE_EVIDENCE_MALFORMED")
        for ref in ("", "  ", None):
            with self.assertRaises(Refusal) as c: B.ConformanceEvidence(False, ref)
            self.assertEqual(c.exception.code, "CONFORMANCE_EVIDENCE_WITHOUT_REF")
    def test_no_quant_semantics_preserved_only_when_no_quant_was_requested(self):
        a = admit(package(None, quant=False, request_record=None), accepted_fit_generations={}); self.assertEqual(a.classification, NO_QUANT_FEATURE)
    def test_intake_report_still_says_outcome_access_not_assessed(self):
        from stage_a.tracker import quant_intake_adapter as Q
        self.assertIn("NOT_ASSESSED_BOUNDARY", open(Q.__file__).read())                    # honesty control: full s28 conformance is NOT claimed certified
class Pipeline(unittest.TestCase):
    def issue(self, rig, p):
        adm = admit(p, accepted_fit_generations={}, conformance=EV(False)); rig.claims.issue_order(ConstructionOrder(p.order_id, adm.subject_key, "SRC-BINDING-1", "MANAGER"))
    def run_p(self, p, src):
        rig = Rig(conformance_source=src); self.issue(rig, p); return rig, rig.pipe.run(p)
    def test_no_conformance_source_rejects_and_journals_nothing(self):
        rig, o = self.run_p(pk(), None)
        self.assertEqual((o.accepted_ok, o.stage), (False, "ADMISSIBILITY"))
        self.assertIn("OUTCOME_ACCESS_UNVERIFIED_UNDER_FORBIDDEN", [c for _, c in o.admission.failed])
        self.assertEqual(rig.journals.journal("XAUUSD/H4/mom3").read_from(1), [])
    def test_consulted_rejects(self): self.assertEqual(self.run_p(pk(), lambda p: EV(True))[1].stage, "ADMISSIBILITY")
    def test_missing_unknown_conflicting_or_held_declarations_reject_through_the_pipeline(self):
        for p in (pk(order=None, out=None), pk(order="MAYBE", out="MAYBE"), pk(order="FORBIDDEN", out=P), pk(order=P, out=P), pk(out=None)):
            rig, o = self.run_p(p, lambda q: EV(False))
            self.assertEqual((o.accepted_ok, o.stage), (False, "ADMISSIBILITY"))
            self.assertEqual(rig.journals.journal("XAUUSD/H4/mom3").read_from(1), [])
    def test_positive_control_accepts_end_to_end(self):
        rig, o = self.run_p(pk(), lambda p: EV(False)); self.assertTrue(o.accepted_ok)
        self.assertEqual(replay("XAUUSD/H4/mom3", rig.journals.journal("XAUUSD/H4/mom3").read_from(1))["1"].status, T.CANONICAL_ACCEPTED)
class UnverifiedDutiesAreLabelled(unittest.TestCase):
    def test_capability_class_structure_is_labelled_unverified_not_certified(self):
        a = A(pk(), EV(False)); self.assertIn(("CAPABILITY_CLASS_STRUCTURE", "NOT_VERIFIED_NO_SOURCE_COMPATIBILITY_RULE"), a.unverified)
    def test_label_absent_when_the_declaration_itself_is_refused(self):
        p = pk(); p = dataclasses.replace(p, capability_declaration=dict(p.capability_declaration, PROGRAM_CAPABILITY_CLASS="NOT_A_CLASS"))
        a = A(p, EV(False)); self.assertEqual(a.unverified, []); self.assertTrue(dims(a, "CAPABILITY_DECLARATION"))
    def test_accepted_outcome_carries_its_limits(self):
        rig = Rig(conformance_source=lambda q: EV(False)); p = pk(); adm = admit(p, accepted_fit_generations={}, conformance=EV(False))
        rig.claims.issue_order(ConstructionOrder(p.order_id, adm.subject_key, "SRC-BINDING-1", "MANAGER")); o = rig.pipe.run(p)
        self.assertTrue(o.accepted_ok)
        self.assertEqual(dict(o.limits), {"CAPABILITY_CLASS_STRUCTURE": "NOT_VERIFIED_NO_SOURCE_COMPATIBILITY_RULE", "S28_FULL_CONFORMANCE": "NOT_ASSESSED_BOUNDARY"})
if __name__ == "__main__": unittest.main()
