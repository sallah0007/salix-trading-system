import unittest
from stage_a.errors import Refusal
from stage_a.health import subject_coverage as SC
from stage_a.gateway import contracts as G
from .test_r25_scheduler import core, ver, KEY
from .test_boundaries import I, R
def code(f, *a, **k):
    try: f(*a, **k)
    except Refusal as e: return e.code
class SubjectCoverage(unittest.TestCase):
    def test_only_three_kinds_have_a_source_and_a_healthy_recording_alone_is_not_healthy(self):
        c = core(); ver(c, KEY, version="1", at=10, age=50); r = SC.coverage(c, KEY, "1", 11)
        d = {k: (s, src) for k, s, src in r.local}; self.assertEqual(d["RECORDING_VERIFICATION"][0], "HEALTHY")
        self.assertTrue(all(d[k] == ("UNKNOWN", SC.NO_SOURCE) for k in SC.LOCAL_KINDS if k not in ("RECORDING_VERIFICATION", "GATEWAY_BINDING_NON_DELIVERY")))
        self.assertEqual((r.local_aggregate, r.complete, r.admitted), ("UNKNOWN", False, False))
    def test_not_healthy_dominates_and_supplied_readings_are_labelled_unadmitted_and_validated(self):
        c = core(); ver(c, KEY, version="1", at=10, age=50)
        full = {k: "HEALTHY" for k in SC.LOCAL_KINDS if k != "RECORDING_VERIFICATION"}
        r = SC.coverage(c, KEY, "1", 11, supplied=full)                                                                                         # every other kind SUPPLIED: complete, still unadmitted
        self.assertEqual((r.local_aggregate, r.complete, r.admitted), ("HEALTHY", True, False)); self.assertTrue(all(src == "CALLER_ASSERTED_UNADMITTED" for k, s, src in r.local if k != "RECORDING_VERIFICATION"))
        part = {k: v for k, v in full.items() if k != "FIT_GENERATION"}; r = SC.coverage(c, KEY, "1", 11, supplied=part); self.assertEqual((r.local_aggregate, r.complete), ("UNKNOWN", False))        # one kind without a source: never HEALTHY
        self.assertEqual(SC.coverage(c, KEY, "1", 11, supplied=dict(full, SCHEDULER_RESOURCE_STATE="NOT_HEALTHY")).local_aggregate, "NOT_HEALTHY")
        self.assertEqual(code(SC.coverage, c, KEY, "1", 11, supplied={"BOGUS": "HEALTHY"}), "HEALTHY_SUBJECT_KIND_UNKNOWN".replace("HEALTHY_", "HEALTH_")); self.assertEqual(code(SC.coverage, c, KEY, "1", 11, supplied={"FIT_GENERATION": "OK"}), "HEALTH_SUBJECT_STATE_INVALID")
    def test_carried_upstream_impact_never_changes_the_local_state_and_a_foreign_snapshot_is_not_evidence(self):
        c = core(); b = G.HealthBinding(I, "1", I, I); c.declare_dependency("DOWN", KEY)
        for k in (KEY, "DOWN"): ver(c, k, version="1", at=10, age=50)
        c.associate_subject(KEY, b, "a"); snap = c.gateway_health(KEY, "1", 12, R("hl"), 11, binding=b)
        r = SC.coverage(c, KEY, "1", 12, gateway_snapshot=snap); d = {k: s for k, s, _ in r.local}; self.assertEqual((d["GATEWAY_BINDING_NON_DELIVERY"], r.carried), ("HEALTHY", (("FW_ML_CARRIED_UPSTREAM_IMPACT", ("DOWN",)),)))
        up = SC.coverage(c, "DOWN", "1", 12); self.assertEqual(dict((k, s) for k, s, _ in up.local)["RECORDING_VERIFICATION"], "HEALTHY")             # the dependent's LOCAL reading is its own, not the upstream's
        c.quarantine(KEY, "DEFECT"); r2 = SC.coverage(c, KEY, "1", 12, gateway_snapshot=snap); self.assertEqual(dict((k, s) for k, s, _ in r2.local)["GATEWAY_BINDING_NON_DELIVERY"], "UNKNOWN")      # stale/unconfirmed snapshot is not evidence
        self.assertEqual(dict((k, s) for k, s, _ in SC.coverage(c, "DOWN", "1", 12, gateway_snapshot=snap).local)["GATEWAY_BINDING_NON_DELIVERY"], "UNKNOWN")                 # snapshot for another subject
class RequestedVersion(unittest.TestCase):
    def test_a_snapshot_for_version_1_is_not_evidence_for_version_999(self):
        c = core(); b = G.HealthBinding(I, "1", I, I); ver(c, KEY, version="1", at=10, age=50); c.associate_subject(KEY, b, "a"); snap = c.gateway_health(KEY, "1", 12, R("hl"), 11, binding=b)
        g = lambda v: dict((k, s) for k, s, _ in SC.coverage(c, KEY, v, 12, gateway_snapshot=snap).local)["GATEWAY_BINDING_NON_DELIVERY"]
        self.assertEqual((g("1"), g("999")), ("HEALTHY", "UNKNOWN"))

if __name__ == "__main__": unittest.main()
