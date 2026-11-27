import unittest
from stage_a.errors import Refusal
from stage_a.health import adapters as AD, subject_coverage as SC
from stage_a.tracker.accepted_manifest import read_accepted_manifest
from stage_a.ml import dataset_manifest as DM, generation_lifecycle as GL
from . import test_r33_composed as TC
from .test_r35_dataset_manifest import ds
class Adapters(unittest.TestCase):
    def setUp(self):
        t = TC.AcceptedRecordVerification(); self.rig, self.fk, self.j, self.body = t.accepted(); self.c, _, _ = t.ver(self.rig, self.fk, self.j)
        self.rb = read_accepted_manifest(self.j, self.rig.store, self.fk); self.A = self.fk.key()
    def test_quant_manifest_profile_is_subject_scoped_and_bound_to_the_accepted_hash(self):
        o = AD.from_accepted_manifest(self.rb); self.assertEqual((o.kind, o.scope, o.facts["manifest_hash"]), ("QUANT_MANIFEST_PROFILE", "SUBJECT", self.body["manifest_hash"])); self.assertGreater(o.facts["nodes"], 0)
        pol = {"QUANT_MANIFEST_PROFILE": lambda f: "HEALTHY"}
        ok = dict((k, s) for k, s, _ in SC.coverage(self.c, self.A, "1", 11, observations={"QUANT_MANIFEST_PROFILE": o}, policies=pol).local)["QUANT_MANIFEST_PROFILE"]
        other = dict((k, s) for k, s, _ in SC.coverage(self.c, "XAUUSD/H4/OTHER/1", "1", 11, observations={"QUANT_MANIFEST_PROFILE": o}, policies=pol).local)["QUANT_MANIFEST_PROFILE"]
        self.assertEqual((ok, other), ("HEALTHY", "UNKNOWN"))                       # an unrelated subject never inherits this manifest's reading
    def test_fit_generation_reports_the_exact_refusal_code_and_ok_when_exact(self):
        refs = [{"generation": 2, "ref_hash": "h2"}]
        self.assertEqual(AD.from_fit_generation_check(self.fk, refs, {2: "h2"}).facts["result"], "OK"); self.assertEqual(AD.from_fit_generation_check(self.fk, refs, {2: "x"}).facts["result"], "FIT_REF_HASH_MISMATCH")
        self.assertEqual(AD.from_fit_generation_check(self.fk, refs, {3: "h3"}).facts["result"], "FIT_GENERATION_UNKNOWN"); self.assertEqual(AD.from_fit_generation_check(self.fk, [{"generation": 1, "ref_hash": "h1"}], {1: "h1", 2: "h2"}).facts["result"], "FIT_GENERATION_STALE")
    def test_replay_backlog_and_journal_handoff_are_read_from_the_actual_journal(self):
        o = AD.from_replay_backlog(self.fk, self.j, 0); self.assertEqual((o.facts["backlog"], o.facts["head_seq"] >= 1), (o.facts["head_seq"], True)); self.assertEqual(AD.from_replay_backlog(self.fk, self.j, o.facts["head_seq"]).facts["backlog"], 0)
        h = AD.from_journal_handoff(self.j, self.fk.namespace()); self.assertEqual((h.facts["replay"], h.facts["legacy_accepted"], h.facts["by_kind"].get("CANONICAL_ACCEPTED")), ("OK", 0, 1)); self.assertTrue(h.scope.startswith("GLOBAL:JOURNAL:"))
    def test_revocation_ledger_facts_and_augmented_checks(self):
        r = DM.DatasetRegistry({"w"}, "S"); r.register("w", ds()); self.assertEqual(AD.from_revocation_ledgers(r, GL.GenerationRegistry()).facts, {"dataset_revocations": 0, "dataset_last_ts": None, "generation_ledger": 0})
        r.revoke("w", "D1", 5, "x", "A"); self.assertEqual(AD.from_revocation_ledgers(r).facts, {"dataset_revocations": 1, "dataset_last_ts": 5, "generation_ledger": None})
        from stage_a.ml.receiver import AugmentedCheck
        o = AD.from_augmented_checks([AugmentedCheck("L", True, "VERIFIED_ISSUED_BINDING"), AugmentedCheck("L", False, "UNVERIFIED_SHAPE_ONLY")]); self.assertEqual(o.facts["by_lane_and_verification"], {"L:UNVERIFIED": 1, "L:VERIFIED": 1})
if __name__ == "__main__": unittest.main()
