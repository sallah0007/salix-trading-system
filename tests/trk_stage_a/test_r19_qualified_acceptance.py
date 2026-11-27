"""R19: (1) QUALIFIED acceptance fails closed: typed DutyEvidence is not authority, baseline must be connected, s28 duties stay held; explicit SIMULATION is separate and never qualified.
(2) A caller-supplied 'no quant requested' flag cannot erase failed/revoked requested-build lineage (TR-06 / D8). No package key, classification mapping or evidence provider is invented."""
import dataclasses, unittest
from tests.trk_stage_a.fixtures import Rig, package, SIM_DUTIES, SIM_CONF
from tests.trk_stage_a.test_pipeline import baseline_binding
from stage_a.tracker.quant_intake_adapter import MANDATORY_UNVERIFIED_DUTIES, NO_QUANT_FEATURE, FAILED_REQUESTED_BUILD
def go(rig, p, issue=True):
    if issue: rig.issue(p)
    return rig.pipe.run(p)
class Qualified(unittest.TestCase):
    def test_full_simulated_evidence_does_not_qualify_acceptance(self):
        rig = Rig(simulation=False, baseline=baseline_binding()); o = go(rig, package())
        self.assertEqual((o.accepted_ok, o.stage), (False, "MANDATORY_VERIFICATION_HELD"))
        self.assertEqual(sorted(c for c, _ in o.admission.failed), sorted(MANDATORY_UNVERIFIED_DUTIES))
        self.assertEqual(rig.journals.journal("XAUUSD/H4/mom3").read_from(1), [])
    def test_baseline_none_is_held_in_qualified_mode(self):
        rig = Rig(simulation=False); o = go(rig, package())
        self.assertIn(("BASELINE_REGISTRATION", "BASELINE_NOT_CONNECTED"), o.admission.failed); self.assertFalse(o.accepted_ok)
    def test_s28_duties_are_mandatory_and_named(self):
        for d in ("S28_INPUTS_RESOLVE", "S28_REPRODUCTION", "S28_FULL_CONFORMANCE"): self.assertIn(d, MANDATORY_UNVERIFIED_DUTIES)
    def test_simulation_is_explicit_and_never_qualified(self):
        rig = Rig(); o = go(rig, package())                                    # Rig default = explicit simulation
        self.assertTrue(o.accepted_ok and o.simulation); self.assertEqual(list(dict(o.limits)), ["SIMULATION_NOT_QUALIFIED"])
    def test_pipeline_default_is_qualified_not_simulation(self):
        import inspect; from stage_a.tracker.pipeline import TrackerPipeline
        self.assertIs(inspect.signature(TrackerPipeline.__init__).parameters["simulation"].default, False)
class NoQuantFlag(unittest.TestCase):
    def test_flag_cannot_erase_revoked_order_lineage_even_without_a_duty_source(self):           # Codex reproduction
        rig = Rig(duty_source=None); p = package(); rig.issue(p); rig.claims.revoke_order(p.order_id, "test")
        q = dataclasses.replace(p, quant_feature_requested=False, manifest=None); o = rig.pipe.run(q)
        self.assertNotEqual(o.classification, NO_QUANT_FEATURE); self.assertEqual(o.classification, FAILED_REQUESTED_BUILD)
        self.assertEqual(o.stage, "CLASSIFICATION"); self.assertIn("ORDER_REVOKED", o.failures[0][1])
    def test_flag_cannot_erase_issued_order_or_request_claim_lineage(self):
        rig = Rig(); p = package(); rig.issue(p)
        q = dataclasses.replace(p, quant_feature_requested=False, manifest=None)
        self.assertEqual(rig.pipe.run(q).classification, FAILED_REQUESTED_BUILD)
        rig2 = Rig(); p2 = package(); rig2.issue(p2); rig2.pipe.run(p2)                         # accepted: request claim now exists
        self.assertEqual(rig2.pipe.run(dataclasses.replace(p2, quant_feature_requested=False, manifest=None)).classification, FAILED_REQUESTED_BUILD)
    def test_genuine_no_quant_positive_control_is_preserved_but_labelled_unverified(self):
        rig = Rig(); p = package(None, quant=False, request_record=None); o = rig.pipe.run(p)
        self.assertEqual(o.classification, NO_QUANT_FEATURE)
        self.assertIn("NO_QUANT_CLASSIFICATION", dict(o.limits))
    def test_lineage_is_read_only_and_never_authority(self):
        rig = Rig(); p = package(); self.assertEqual(rig.claims.lineage(p.order_id, p.request_id), [])
        rig.issue(p); self.assertEqual(rig.claims.lineage(p.order_id), ["ORDER_ISSUED"])
        rig.claims.revoke_order(p.order_id, "x"); self.assertEqual(rig.claims.lineage(p.order_id), ["ORDER_REVOKED"])
if __name__ == "__main__": unittest.main()
