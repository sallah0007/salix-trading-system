"""R16: the Composer s28 outcome-access conformance check is connected to intake AND the pipeline. Evidence is Tracker-originated (ConformanceEvidence), never taken from the
package. FORBIDDEN with no/undetermined evidence is HELD; consulted outcome info fails; only a determined 'not consulted' admits. Nothing here is a real verification path."""
import dataclasses, unittest
from stage_a.errors import Refusal
from stage_a.tracker import build_output_check as B
from stage_a.tracker.pipeline import TrackerPipeline
from stage_a.tracker.quant_intake_adapter import admit, QUANT_FEATURE, FAILED_REQUESTED_BUILD
from stage_a.coordination import transition_record as T
from stage_a.replay import replay
from tests.trk_stage_a.fixtures import Rig, package, momentum_manifest, build_output_for

def pkg(**o):
    p = package(); bo = dict(p.build_output, OUTCOME_INFORMATION_ACCESS="FORBIDDEN"); bo.update(o); return dataclasses.replace(p, build_output=bo)
def conf(a): return [c for d, c in a.failed if d == "BUILD_CONFORMANCE"]
EV = lambda v: B.ConformanceEvidence(v, "SIMULATED:test-evidence")
class Intake(unittest.TestCase):
    def test_reported_reproduction_is_now_held(self):
        a = admit(pkg(), accepted_fit_generations={})                                 # FORBIDDEN, no verification evidence
        self.assertEqual((a.classification, conf(a)), (FAILED_REQUESTED_BUILD, ["OUTCOME_ACCESS_UNVERIFIED_UNDER_FORBIDDEN"]))
    def test_undetermined_evidence_held(self):
        self.assertEqual(conf(admit(pkg(), accepted_fit_generations={}, conformance=EV(None))), ["OUTCOME_ACCESS_UNVERIFIED_UNDER_FORBIDDEN"])
    def test_consulted_outcome_info_fails(self):
        self.assertEqual(conf(admit(pkg(), accepted_fit_generations={}, conformance=EV(True))), ["OUTCOME_INFORMATION_CONSULTED_UNDER_FORBIDDEN"])
    def test_positive_control_determined_not_consulted_admits(self):
        a = admit(pkg(), accepted_fit_generations={}, conformance=EV(False)); self.assertEqual((a.classification, a.failed), (QUANT_FEATURE, []))
    def test_package_cannot_vouch_for_itself(self):
        a = admit(pkg(OUTCOME_ACCESS_CONSULTED=False, OUTCOME_INFORMATION_CONSULTED_BY_VERIFICATION=False), accepted_fit_generations={})
        self.assertEqual(conf(a), ["OUTCOME_ACCESS_UNVERIFIED_UNDER_FORBIDDEN"])
    def test_undeclared_outcome_access_is_not_newly_refused_named_residual(self):
        self.assertEqual(admit(package(), accepted_fit_generations={}).classification, QUANT_FEATURE)
    def test_malformed_evidence_refused(self):
        self.assertEqual(conf(admit(pkg(), accepted_fit_generations={}, conformance="PASS")), ["CONFORMANCE_EVIDENCE_MALFORMED"])
        for bad in ("yes", 1, 0):
            with self.assertRaises(Refusal) as c: B.ConformanceEvidence(bad, "r")
            self.assertEqual(c.exception.code, "CONFORMANCE_EVIDENCE_MALFORMED")
        for ref in ("", "  ", None):
            with self.assertRaises(Refusal) as c: B.ConformanceEvidence(False, ref)
            self.assertEqual(c.exception.code, "CONFORMANCE_EVIDENCE_WITHOUT_REF")
    def test_intake_report_still_says_outcome_access_not_assessed(self):
        # honesty control: the 23-field report keeps NOT_ASSESSED_BOUNDARY; simulated evidence in tests must not turn into a PASS claim
        from stage_a.tracker.quant_intake_adapter import build_safe_intake_report
        self.assertIn("NOT_ASSESSED_BOUNDARY", open(build_safe_intake_report.__code__.co_filename).read())
class Pipeline(unittest.TestCase):
    def test_no_conformance_source_holds_the_admission_and_journals_nothing(self):
        rig = Rig(); p = pkg(); self._issue(rig, p)
        o = rig.pipe.run(p)
        self.assertEqual((o.accepted_ok, o.stage), (False, "ADMISSIBILITY"))
        self.assertTrue(any(c == "OUTCOME_ACCESS_UNVERIFIED_UNDER_FORBIDDEN" for _, c in o.admission.failed))
        self.assertEqual(rig.journals.journal("XAUUSD/H4/mom3").read_from(1), [])
    def test_source_saying_consulted_rejects(self):
        rig = Rig(conformance_source=lambda pk: EV(True)); p = pkg(); self._issue(rig, p)
        self.assertEqual(rig.pipe.run(p).stage, "ADMISSIBILITY")
    def test_source_determining_not_consulted_accepts_end_to_end(self):
        rig = Rig(conformance_source=lambda pk: EV(False)); p = pkg(); self._issue(rig, p)
        o = rig.pipe.run(p); self.assertTrue(o.accepted_ok)
        self.assertEqual(replay("XAUUSD/H4/mom3", rig.journals.journal("XAUUSD/H4/mom3").read_from(1))["1"].status, T.CANONICAL_ACCEPTED)
    def _issue(self, rig, p):
        from tracker_component.order import ConstructionOrder
        adm = admit(p, accepted_fit_generations={}, conformance=EV(False)); rig.claims.issue_order(ConstructionOrder(p.order_id, adm.subject_key, "SRC-BINDING-1", "MANAGER"))
if __name__ == "__main__": unittest.main()
