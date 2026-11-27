"""R18 finding 3: (i) outcome-access equality is SUPPLIED-RECORD STRUCTURAL equality (ConstructionOrder carries no declaration), labelled and held; (ii) mandatory unresolved duties
(capability class/structure firewall, governed-before-build binding) are HELD at the actual certification path: before claim, certify, materialize, accept. No algorithm is invented;
with no Tracker-originated DutyEvidence provider (the only real state) nothing is accepted."""
import copy, dataclasses, unittest
from stage_a.errors import Refusal
from stage_a.tracker import build_output_check as B
from stage_a.tracker.quant_intake_adapter import admit, DutyEvidence, unresolved_mandatory, MANDATORY_UNVERIFIED_DUTIES
from stage_a.tracker.pipeline import Outcome
from tracker_component.order import ConstructionOrder
from tests.trk_stage_a.fixtures import Rig, package, SIM_CONF, SIM_DUTIES
CAP, GOV = "CAPABILITY_CLASS_STRUCTURE", "OUTCOME_ACCESS_DECLARATION_GOVERNED_BEFORE_BUILD"
def run(p, duty, rig=None):
    rig = rig or Rig(duty_source=duty); a = admit(p, accepted_fit_generations={}, conformance=SIM_CONF)
    rig.claims.issue_order(ConstructionOrder(p.order_id, a.subject_key, "SRC-BINDING-1", "MANAGER")); return rig, rig.pipe.run(p)
def untouched(rig, o):
    return (o.accepted_ok, o.certification, o.materialization, o.verification) == (False, None, None, None) and rig.journals.journal("XAUUSD/H4/mom3").read_from(1) == []
class SuppliedRecordEquality(unittest.TestCase):
    def test_order_anchor_carries_no_declaration_so_equality_is_structural(self):
        self.assertNotIn("OUTCOME_INFORMATION_ACCESS", ConstructionOrder.__dataclass_fields__)
        p = package()
        self.assertEqual(p.request_record["OUTCOME_INFORMATION_ACCESS"], "FORBIDDEN")
        # REPRODUCTION: the caller rewrites BOTH supplied copies; the same anchored order is issued either way and admission cannot tell (the second is held only because PERMITTED is held).
        a = admit(p, accepted_fit_generations={}, conformance=SIM_CONF); self.assertEqual(a.failed, [])
        rr = dict(p.request_record, OUTCOME_INFORMATION_ACCESS="PERMITTED_UNDER_DECLARED_FITTING_CONTRACT"); bo = dict(p.build_output, OUTCOME_INFORMATION_ACCESS="PERMITTED_UNDER_DECLARED_FITTING_CONTRACT")
        q = dataclasses.replace(p, request_record=rr, build_output=bo); a2 = admit(q, accepted_fit_generations={}, conformance=SIM_CONF)
        self.assertEqual(a.subject_key, a2.subject_key)                                       # same subject => the same anchored order would authorise either package
        self.assertEqual([c for _, c in a2.failed], ["PERMITTED_FITTING_CONTRACT_NOT_VERIFIABLE"])
    def test_label_is_always_present_when_the_declaration_passes(self):
        a = admit(package(), accepted_fit_generations={}, conformance=SIM_CONF)
        self.assertIn((GOV, "NOT_VERIFIED_SUPPLIED_RECORD_STRUCTURAL_EQUALITY"), a.unverified); self.assertIn((CAP, "NOT_VERIFIED_NO_SOURCE_COMPATIBILITY_RULE"), a.unverified)
class MandatoryDutiesHeldAtCertificationPath(unittest.TestCase):
    def test_no_duty_source_holds_before_claim_certify_materialize_accept(self):
        rig, o = run(package(), None)
        self.assertEqual(o.stage, "MANDATORY_VERIFICATION_HELD"); self.assertTrue(untouched(rig, o))
        self.assertEqual(sorted(c for c, _ in o.admission.failed), sorted(MANDATORY_UNVERIFIED_DUTIES))
        self.assertIsNone(rig.claims.claim("CLAIM:REQ-1"))                                       # no claim was even reserved
    def test_held_outcome_limits_still_list_the_unverified_duties(self):
        rig, o = run(package(), None); self.assertEqual({d for d, _ in o.limits}, set(MANDATORY_UNVERIFIED_DUTIES))
    def test_partial_evidence_holds_the_other_duty(self):
        for have, missing in ((CAP, GOV), (GOV, CAP)):
            rig, o = run(package(), lambda p, a, h=have: DutyEvidence(frozenset({h}), "SIMULATED:partial"))
            self.assertEqual((o.stage, sorted(c for c, _ in o.admission.failed)), ("MANDATORY_VERIFICATION_HELD", sorted(set(MANDATORY_UNVERIFIED_DUTIES) - {have}))); self.assertTrue(untouched(rig, o))
    def test_unrelated_or_malformed_evidence_verifies_nothing(self):
        for ev in (DutyEvidence(frozenset({"SOMETHING_ELSE"}), "SIMULATED:x"), "VERIFIED", {"duties": [CAP, GOV]}, True, object()):
            rig, o = run(package(), lambda p, a, e=ev: e)
            self.assertEqual(o.stage, "MANDATORY_VERIFICATION_HELD", ev); self.assertTrue(untouched(rig, o))
    def test_evidence_object_validates_itself(self):
        for bad in (frozenset(), {CAP}, [CAP], frozenset({1})):
            with self.assertRaises(Refusal) as c: DutyEvidence(bad, "r")
            self.assertEqual(c.exception.code, "DUTY_EVIDENCE_MALFORMED")
        for ref in ("", "  ", None):
            with self.assertRaises(Refusal) as c: DutyEvidence(frozenset({CAP}), ref)
            self.assertEqual(c.exception.code, "DUTY_EVIDENCE_WITHOUT_REF")
    def test_positive_control_accepts_only_with_both_duties_evidenced_and_limits_shrink(self):
        rig, o = run(package(), lambda p, a: SIM_DUTIES)
        self.assertTrue(o.accepted_ok); self.assertEqual(list(dict(o.limits)), ["SIMULATION_NOT_QUALIFIED"]); self.assertIn("SIMULATED", o.duty_evidence.evidence_ref); self.assertTrue(o.simulation)
    def test_no_quant_classification_is_not_affected(self):
        a = admit(package(None, quant=False, request_record=None), accepted_fit_generations={}); self.assertEqual(unresolved_mandatory(a, None), [])
    def test_refused_admission_is_not_masked_by_the_duty_hold(self):
        p = package(); p = dataclasses.replace(p, capability_declaration=dict(p.capability_declaration, PROGRAM_CAPABILITY_CLASS="NOT_A_CLASS"))
        rig, o = run(p, None); self.assertEqual(o.stage, "ADMISSIBILITY")                       # the structural refusal comes first and is reported as such
    def test_hold_happens_before_certify(self):
        import stage_a.tracker.pipeline as PL
        calls = []; orig = PL.certify; PL.certify = lambda *a, **k: calls.append(1) or orig(*a, **k)
        try: run(package(), None)
        finally: PL.certify = orig
        self.assertEqual(calls, [])
class Direct(unittest.TestCase):
    class Adm:
        def __init__(self, u): self.unverified = u
    def test_only_mandatory_duties_are_held_and_malformed_evidence_is_named(self):
        self.assertEqual(unresolved_mandatory(self.Adm([("OTHER_LABEL", "x")]), None), [])
        self.assertEqual(unresolved_mandatory(self.Adm([]), "VERIFIED"), [("DUTY_EVIDENCE", "DUTY_EVIDENCE_MALFORMED")])
        self.assertEqual(unresolved_mandatory(self.Adm([]), SIM_DUTIES, simulation=True), [])
if __name__ == "__main__": unittest.main()
