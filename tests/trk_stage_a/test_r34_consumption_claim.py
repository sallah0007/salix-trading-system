import unittest, dataclasses
from stage_a.errors import Refusal
from stage_a.ml import consumption_claim as CC
from stage_a.ml import generation_lifecycle as GL
from .test_r29_generation_lifecycle import man
def code(f, *a, **k):
    try: f(*a, **k)
    except Refusal as e: return e.code
L = CC.FamilyLedgerRef("FL1", "v3", "h" * 8, 5)
def claim(**k): d = dict(claim_id="C1", consumer_binding_id="B1", manifest_id="M1", claim_ts=10, authority_bearing=True, feed_era_id="E1", family_ledger=L); d.update(k); return CC.ConsumptionClaim(**d)
class FamilyLedger(unittest.TestCase):
    def test_authority_bearing_claim_needs_complete_ledger_ref_available_by_claim_time(self):
        led = CC.ClaimLedger(); self.assertEqual(led.record(claim(), manifest_feed_era_id="E1").claim_id, "C1")
        self.assertEqual(code(led.record, claim(claim_id="C2", family_ledger=None), manifest_feed_era_id="E1"), "AUTHORITY_BEARING_CLAIM_WITHOUT_FAMILY_LEDGER_REF")
        self.assertEqual(code(led.record, claim(claim_id="C3", family_ledger=CC.FamilyLedgerRef("FL1", "v3", "h", 11)), manifest_feed_era_id="E1"), "FAMILY_LEDGER_NOT_AVAILABLE_AT_CLAIM_TIME")
        for bad in (("", "v", "h", 1), ("r", "", "h", 1), ("r", "v", "", 1), ("r", "v", "h", None), ("r", "v", "h", True)): self.assertEqual(code(CC.FamilyLedgerRef, *bad), "FAMILY_LEDGER_REF_INCOMPLETE")
    def test_later_ledger_state_never_rewrites_the_historical_binding(self):
        led = CC.ClaimLedger(); c = led.record(claim(), manifest_feed_era_id="E1"); self.assertIs(led.record(claim(), manifest_feed_era_id="E1"), c)
        later = dataclasses.replace(L, version="v4", available_asof=9); self.assertEqual(code(led.record, claim(family_ledger=later), manifest_feed_era_id="E1"), "CONSUMPTION_CLAIM_IMMUTABLE"); self.assertEqual(led.bound_ledger("C1"), L)
class Era(unittest.TestCase):
    def test_era_must_exist_and_equal_the_manifests_era_and_unsupplied_is_held(self):
        led = CC.ClaimLedger(); self.assertEqual(code(led.record, claim(), manifest_feed_era_id="E2"), "FEED_ERA_MISMATCH"); self.assertEqual(code(led.record, claim()), "MANIFEST_FEED_ERA_UNSUPPLIED_HELD"); self.assertEqual(code(led.record, claim(feed_era_id=None), manifest_feed_era_id="E1"), "FEED_ERA_ID_MISSING")
class Revocation(unittest.TestCase):
    D = {"M3": ["M2"], "M2": ["M1"], "M1": []}
    def test_direct_and_transitive_revoked_contributors_are_reported_and_unknowns_fail_closed(self):
        r = CC.revocation_report("M3", self.D, lambda m: m == "M1"); self.assertEqual((r["status"], r["affected"], r["qualified"]), ("AFFECTED", {"M1": {"direct": False, "transitive": True, "codes": (CC.DERIVED_FROM_REVOKED,)}}, False))
        r = CC.revocation_report("M3", self.D, lambda m: m == "M2"); self.assertEqual(r["affected"], {"M2": {"direct": True, "transitive": False, "codes": (CC.CONTRIBUTOR_LATER_REVOKED,)}})
        self.assertEqual(CC.revocation_report("M3", self.D, lambda m: False)["status"], "CLEAN")
        self.assertEqual(CC.revocation_report("M3", self.D, lambda m: None if m == "M1" else False)["status"], "UNKNOWN")             # unknown revocation state is not clean
        self.assertEqual(CC.revocation_report("M3", {"M3": ["M2"]}, lambda m: False)["unresolved"], ("M2",))                           # ancestor missing from lineage map
        self.assertEqual(code(CC.revocation_report, "A", {"A": ["B"], "B": ["A"]}, lambda m: False), "LINEAGE_CYCLE"); self.assertEqual(code(CC.revocation_report, "A", {"A": "B"}, lambda m: False), "LINEAGE_ENTRY_MALFORMED")
    def test_malformed_callback_results_never_become_clean(self):
        for bad in ("UNKNOWN", 1, 0, {}, [], "", "False", 0.0): self.assertEqual(code(CC.revocation_report, "R", {"R": ["A"], "A": []}, lambda m, b=bad: b), "REVOCATION_CALLBACK_RESULT_INVALID", repr(bad))
        D = {"R": ["A"], "A": []}; self.assertEqual(CC.revocation_report("R", D, lambda m: False)["status"], "CLEAN"); self.assertEqual(CC.revocation_report("R", D, lambda m: True)["status"], "AFFECTED"); self.assertEqual(CC.revocation_report("R", D, lambda m: None)["status"], "UNKNOWN")
    def test_ancestor_order_permutation_and_a_shared_direct_plus_transitive_ancestor_keep_all_path_facts(self):
        a = CC.revocation_report("R", {"R": ["B", "A"], "B": ["A"], "A": []}, lambda m: m == "A"); b = CC.revocation_report("R", {"R": ["A", "B"], "B": ["A"], "A": []}, lambda m: m == "A")
        self.assertEqual(a, b); self.assertEqual(a["affected"]["A"], {"direct": True, "transitive": True, "codes": (CC.CONTRIBUTOR_LATER_REVOKED, CC.DERIVED_FROM_REVOKED)})
        self.assertEqual(CC.revocation_report("R", {"R": ["X"], "X": [], "Y": ["A"], "A": []}, lambda m: m == "A")["status"], "CLEAN")                # an unrelated revoked generation does not affect a fully resolved baseline
    def test_against_the_real_registry_revoked_state(self):
        r = GL.GenerationRegistry()
        for i in ("M1", "M2"): r.register_manifest(man(i)); r.append_lifecycle(i, "COMPLETE_CERTIFIED", 10, "c", "A")
        r.append_lifecycle("M1", "REVOKED", 11, "bad", "A")
        rev = lambda m: (None if r.manifest_of(m) is None else r.read_class(m)["class"] == "FORENSIC_ONLY")
        self.assertEqual(CC.revocation_report("M2", {"M2": ["M1"], "M1": []}, rev)["affected"], {"M1": {"direct": True, "transitive": False, "codes": (CC.CONTRIBUTOR_LATER_REVOKED,)}})
if __name__ == "__main__": unittest.main()
