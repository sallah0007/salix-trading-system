"""D1: protected composition binding prepared for review. Not installed; baseline default stays False; admission is an explicit hold."""
import unittest
from unittest import mock
from tracker_identity.models import LookupOutcome
from tracker_identity import store as baseline_store
from stage_a.errors import Refusal
from stage_a.tracker.construction_binding import ConstructionAuthorityBinding, PrincipalSourceAdmission, HELD_ADMISSION, SIMULATION_EVIDENCE, ADMISSION_ASSERTED
from stage_a.coordination.object_store_journal import ObjectStoreJournal
from tracker_component.claims import ClaimService
from .fixtures import Rig, package, ANCHOR
class Binding(unittest.TestCase):
    def setUp(self):
        self.rig = Rig(); self.p = package(); self.adm = self.rig.issue(self.p); self.v = {"content_key_composite": self.adm.subject_key, "request_id": "REQ-1"}
    def reserve(self): self.rig.claims.reserve(subject_key=self.adm.subject_key, request_id="REQ-1", order_id="ORD-1", lookup_outcome=LookupOutcome.ABSENT)
    def test_simulation_claim_service_resolves_only_as_explicit_simulation_evidence(self):
        b = ConstructionAuthorityBinding(self.rig.claims); self.assertEqual(b.status(), SIMULATION_EVIDENCE); self.assertFalse(b.resolver(self.v)); self.reserve(); self.assertTrue(b.resolver(self.v))
    def test_follows_revocation_and_one_shot_consumption_and_never_a_caller_flag(self):
        b = ConstructionAuthorityBinding(self.rig.claims); self.reserve(); self.assertFalse(b.resolver(dict(self.v, request_id="OTHER")))
        self.rig.claims.consume("CLAIM:REQ-1", "x"); self.assertFalse(b.resolver(self.v))
    def test_revoked_order_is_false(self):
        b = ConstructionAuthorityBinding(self.rig.claims); self.reserve(); self.rig.claims.revoke_order("ORD-1", "r"); self.assertFalse(b.resolver(self.v))
    def test_restart_recovers_from_the_journal(self):
        b = ConstructionAuthorityBinding(self.rig.claims); self.reserve()
        j2 = ObjectStoreJournal(self.rig.store, "claims", "claims-writer-2"); j2.acquire_epoch(); cs2 = ClaimService(j2, ANCHOR)
        self.assertTrue(ConstructionAuthorityBinding(cs2).resolver(self.v))
    def test_binding_is_never_installed_and_baseline_default_is_unchanged(self):
        b = ConstructionAuthorityBinding(self.rig.claims); self.assertIs(b.installed, False); self.assertIs(baseline_store._governed_construction_authority({}), False)
    def test_admission_must_be_typed_and_complete(self):
        self.assertRaises(Refusal, ConstructionAuthorityBinding, self.rig.claims, "yes"); self.assertRaises(Refusal, PrincipalSourceAdmission, "", "x")
    def test_test_only_patch_is_labelled_instrumentation_not_an_installed_path(self):
        b = ConstructionAuthorityBinding(self.rig.claims); self.reserve()
        with mock.patch.object(baseline_store, "_governed_construction_authority", b.resolver):
            self.assertTrue(baseline_store._governed_construction_authority(self.v))
        self.assertIs(baseline_store._governed_construction_authority(self.v), False)
class QualifiedHold(unittest.TestCase):
    def test_held_even_when_the_claim_service_would_authorize(self):
        rig = Rig(simulation=False); adm = rig.issue(package()); rig.claims.reserve(subject_key=adm.subject_key, request_id="REQ-1", order_id="ORD-1", lookup_outcome=LookupOutcome.ABSENT)
        v = {"content_key_composite": adm.subject_key, "request_id": "REQ-1"}
        self.assertTrue(rig.claims.authorizes(adm.subject_key, "REQ-1"))                              # the inner service would say yes
        self.assertFalse(ConstructionAuthorityBinding(rig.claims).resolver(v))                        # but the unbound admission holds it
        self.assertTrue(ConstructionAuthorityBinding(rig.claims, PrincipalSourceAdmission("REC", "p")).resolver(v))
    def test_qualified_claim_service_without_admission_is_held_and_with_asserted_admission_delegates(self):
        from stage_a.storage.object_store import InMemoryObjectStore
        j = ObjectStoreJournal(InMemoryObjectStore(), "claims-q", "w"); j.acquire_epoch(); cs = ClaimService(j, ANCHOR)
        b = ConstructionAuthorityBinding(cs); self.assertEqual(b.status(), HELD_ADMISSION); self.assertFalse(b.resolver({"content_key_composite": "k", "request_id": "r"}))
        b2 = ConstructionAuthorityBinding(cs, PrincipalSourceAdmission("REC-1", "principal")); self.assertEqual(b2.status(), ADMISSION_ASSERTED); self.assertFalse(b2.resolver({}))   # no claim -> still False
if __name__ == "__main__": unittest.main()
