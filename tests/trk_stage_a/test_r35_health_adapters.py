import unittest
from stage_a.errors import Refusal
from stage_a.health import adapters as AD, subject_coverage as SC
from stage_a.gateway.v038 import FinalResolutionStore, FinalResolutionIdentity as FI
from stage_a.fw.association import FwAssociation
from stage_a.ml import consumption_claim as CC
from stage_a.tracker.verification.verification_result import make_result, PASS, FAIL, SCOPE_MATERIALIZATION
from .test_r25_scheduler import core, ver, KEY
from .test_r34_health_subjects import code
def res(status=PASS, bad=()):
    from stage_a.tracker.verification.verification_result import PASS_PROFILE
    return make_result(status, SCOPE_MATERIALIZATION, {"k": "v"}, [(n, n not in bad) for n in sorted(PASS_PROFILE)], ())
class Adapters(unittest.TestCase):
    def test_verification_result_facts_have_no_verdict_and_a_non_result_is_no_facts(self):
        o = AD.from_verification_result(res(FAIL, bad=("byte_length",)), "r1"); self.assertEqual((o.facts["status"], o.facts["failed_checks"], o.facts["self_consistent"], o.admitted), ("FAIL", ("byte_length",), True, False)); self.assertIn("thresholds", o.held_slots)
        self.assertIsNone(AD.from_verification_result("not a result", "r1").facts); self.assertEqual(AD.state_for(AD.from_verification_result("x", "r"), lambda f: "HEALTHY"), ("UNKNOWN", "NO_FACTS"))      # a missing record is never healthy, even with a permissive policy
        self.assertEqual(AD.state_for(o), ("UNKNOWN", "NO_POLICY_SUPPLIED")); self.assertEqual(AD.state_for(o, lambda f: "NOT_HEALTHY" if f["status"] == "FAIL" else "UNKNOWN"), ("NOT_HEALTHY", "CALLER_POLICY_UNADMITTED"))
        for bad in ("OK", True, None, "healthy"): self.assertEqual(code(AD.state_for, o, lambda f, b=bad: b), "HEALTH_POLICY_RESULT_INVALID")
    def test_scheduler_facts_come_from_the_recorded_pass_and_skipped_work_is_counted_not_hidden(self):
        c = core(); c.record_reverify_pass("p1", 10, 3, [["A", "STALE", "VERIFIED", "PASS", "PINNED_NEW"], ["B", "ABSENT", "SKIPPED_BOUND_EXCEEDED", "", ""], ["C", "ABSENT", "REFUSED", "X", ""]])
        o = AD.from_reverify_pass(c, "p1"); self.assertEqual((o.facts["items"], o.facts["skipped"], o.facts["by_outcome"]), (3, 1, {"REFUSED": 1, "SKIPPED_BOUND_EXCEEDED": 1, "VERIFIED": 1})); self.assertIsNone(AD.from_reverify_pass(c, "nope").facts)
    def test_gateway_fw_and_ml_facts_are_counts_of_the_real_records(self):
        s = FinalResolutionStore(); W = FI("FW", "B", "S", "W1"); s.resolve("R1", W, lambda: {"x": 1}); a = FwAssociation(s); a.record_return("E1", "R1", "EVIDENCE"); a.record_return("L1", "R1", "LINEAGE", lineage_ref="L")
        self.assertEqual(AD.from_final_store(s).facts, {"windows": 1, "by_outcome": {"dict": 1}}); self.assertEqual(AD.from_fw_association(a).facts["by_class"], {"EVIDENCE": 1, "LINEAGE": 1}); self.assertEqual(AD.from_fw_association(a).facts["payload_fields"], "HELD_UNBOUND")
        self.assertEqual(AD.from_claim_ledger(CC.ClaimLedger()).facts["claims"], 0)
class CoverageUsesObservations(unittest.TestCase):
    def test_an_observation_is_an_evidence_source_but_never_a_verdict_without_a_policy(self):
        c = core(); ver(c, KEY, version="1", at=10, age=50); c.record_reverify_pass("p1", 10, 3, [["A", "STALE", "VERIFIED", "PASS", "PINNED_NEW"]])
        o = AD.from_reverify_pass(c, "p1"); r = SC.coverage(c, KEY, "1", 11, observations={"SCHEDULER_RESOURCE_STATE": o}); d = {k: (s, src) for k, s, src in r.local}
        self.assertEqual(d["SCHEDULER_RESOURCE_STATE"][0], "UNKNOWN"); self.assertTrue(d["SCHEDULER_RESOURCE_STATE"][1].startswith("ADAPTER_FACTS:reverify_pass:p1:NO_POLICY_SUPPLIED"))
        r2 = SC.coverage(c, KEY, "1", 11, observations={"SCHEDULER_RESOURCE_STATE": o}, policies={"SCHEDULER_RESOURCE_STATE": lambda f: "HEALTHY" if f["skipped"] == 0 else "NOT_HEALTHY"}); self.assertEqual(dict((k, s) for k, s, _ in r2.local)["SCHEDULER_RESOURCE_STATE"], "HEALTHY")
        self.assertEqual(code(SC.coverage, c, KEY, "1", 11, observations={"MATERIALIZATION_ROW": o}), "HEALTH_OBSERVATION_INVALID")                       # kind must match the slot it fills
        st = FinalResolutionStore(); r3 = SC.coverage(c, KEY, "1", 11, observations={"FW_RETURNS": AD.from_fw_association(FwAssociation(st))}); self.assertEqual(r3.extra, (("FW_RETURNS", "UNKNOWN", "NO_POLICY_SUPPLIED"),)); self.assertEqual(r3.local_aggregate, "UNKNOWN")
if __name__ == "__main__": unittest.main()
