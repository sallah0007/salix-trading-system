import unittest
from dataclasses import replace

from tracker_identity import (
    CanonicalIdentityStore,
    CreationProvenanceRecord,
    FeatureIdentity,
    GovernedStateTransitionRecord,
    NormalizerSpec,
    SearchPolicy,
    TransitionClass,
    stale_state_sweep,
    transition_authority_state,
)


def policy():
    p=SearchPolicy("transition-test","1","",("current_active",),("current_active",),{})
    return SearchPolicy(p.policy_id,p.version,p.computed_hash(),p.required_scopes,p.searched_scopes,p.scope_exclusions)


def normalizer():
    n=NormalizerSpec("transition-test","1","",("EXACT_STRUCTURAL_IDENTITY",))
    return NormalizerSpec(n.normalizer_id,n.version,n.computed_hash(),n.equivalence_classes)


def tracked_store():
    identity=FeatureIdentity(
        feature_id="gold.future.feature",feature_version="1",
        definition_hash="abc",graph_hash="def",lifecycle_state="CURRENT",
        is_current=True,scope="current_active",era_id="ERA_1",
        instrument="XAUUSD",timeframe="H1",
    )
    creation=CreationProvenanceRecord(
        creation_record_id="creation:ERA_1:gold.future.feature:1",
        segment_id="TRACKER",object_id=identity.feature_id,
        object_version=identity.feature_version,era_id=identity.era_id,
        initial_state="CURRENT",creation_reason_ref="decision:create",
        created_ts="2026-09-19T22:30:00+10:00",created_by="SALIX_MANAGER",
        authority_ref="owner:era1",evidence_ref="evidence:definition",
    )
    return CanonicalIdentityStore(records=[identity],creation_records=[creation])


def transition(store, **changes):
    vals=dict(
        store=store,object_id="gold.future.feature",object_version="1",era_id="ERA_1",
        from_state="CURRENT",to_state="QUARANTINED",
        transition_id="T-1",transition_class=TransitionClass.QUARANTINE,
        reason_class="DATA_INTEGRITY",reason_ref="incident:1",
        evidence_ref="evidence:incident-1",changed_ts="2026-09-19T22:31:00+10:00",
        changed_by="SALIX_MANAGER",authority_ref="owner:quarantine",
        record_version="1",prior_transition_id="creation:ERA_1:gold.future.feature:1",
    )
    vals.update(changes)
    return transition_authority_state(**vals)


class GovernedTransitionTests(unittest.TestCase):
    def test_quarantine_is_atomic_and_chained_to_creation(self):
        store=tracked_store()
        result=transition(store)
        self.assertTrue(result.accepted)
        self.assertEqual(store.all()[0].lifecycle_state,"QUARANTINED")
        self.assertFalse(store.all()[0].is_current)
        self.assertEqual(len(store.all_transitions()),1)
        self.assertEqual(store.all_transitions()[0].prior_transition_id,"creation:ERA_1:gold.future.feature:1")
        self.assertTrue(stale_state_sweep(store=store,search_policy=policy(),normalizer=normalizer()).clean)

    def test_recovery_preserves_quarantine_history(self):
        store=tracked_store()
        first=transition(store)
        self.assertTrue(first.accepted)
        second=transition(
            store,from_state="QUARANTINED",to_state="CURRENT",
            transition_id="T-2",transition_class=TransitionClass.RECOVERY,
            reason_class="RESOLUTION",reason_ref="decision:incident-closed",
            evidence_ref="evidence:resolution",prior_transition_id="T-1",
        )
        self.assertTrue(second.accepted)
        self.assertEqual(store.all()[0].lifecycle_state,"CURRENT")
        self.assertTrue(store.all()[0].is_current)
        self.assertEqual([t.transition_id for t in store.all_transitions()],["T-1","T-2"])
        self.assertEqual(store.all_transitions()[0].to_state,"QUARANTINED")

    def test_wrong_from_state_rejected_before_write(self):
        store=tracked_store()
        result=transition(store,from_state="SUPERSEDED")
        self.assertFalse(result.accepted)
        self.assertIn("FROM_STATE_MISMATCH",result.errors)
        self.assertEqual(store.all()[0].lifecycle_state,"CURRENT")
        self.assertEqual(store.all_transitions(),())

    def test_stale_writer_same_predecessor_is_rejected(self):
        store=tracked_store()
        first=transition(store)
        self.assertTrue(first.accepted)
        stale=transition(
            store,from_state="QUARANTINED",to_state="RETIRED",
            transition_id="T-stale",transition_class=TransitionClass.RETIREMENT,
            reason_class="RETIREMENT",reason_ref="decision:retire",
            prior_transition_id="creation:ERA_1:gold.future.feature:1",
        )
        self.assertFalse(stale.accepted)
        self.assertIn("PRIOR_TRANSITION_ID_MISMATCH",stale.errors)
        self.assertEqual(len(store.all_transitions()),1)

    def test_missing_reason_rejected(self):
        store=tracked_store()
        result=transition(store,reason_ref="")
        self.assertFalse(result.accepted)
        self.assertIn("REASON_REF_REQUIRED",result.errors)
        self.assertEqual(store.all_transitions(),())

    def test_other_governed_cannot_use_empty_reason(self):
        store=tracked_store()
        result=transition(
            store,transition_class=TransitionClass.OTHER_GOVERNED,
            reason_ref="",
        )
        self.assertFalse(result.accepted)
        self.assertIn("OTHER_GOVERNED_GOVERNED_REASON_REF_REQUIRED",result.errors)

    def test_missing_creation_provenance_rejected(self):
        store=tracked_store()
        store.creation_records.clear()
        result=transition(store)
        self.assertFalse(result.accepted)
        self.assertIn("CREATION_PROVENANCE_REQUIRED",result.errors)

    def test_duplicate_transition_id_rejected(self):
        store=tracked_store()
        first=transition(store)
        self.assertTrue(first.accepted)
        second=transition(
            store,from_state="QUARANTINED",to_state="CURRENT",
            transition_id="T-1",transition_class=TransitionClass.RECOVERY,
            reason_class="RESOLUTION",reason_ref="decision:recover",prior_transition_id="T-1",
        )
        self.assertFalse(second.accepted)
        self.assertIn("DUPLICATE_TRANSITION_ID",second.errors)

    def test_wrong_era_cannot_transition_object(self):
        store=tracked_store()
        result=transition(store,era_id="ERA_0")
        self.assertFalse(result.accepted)
        self.assertIn("TRACKED_OBJECT_NOT_UNIQUE_OR_NOT_FOUND",result.errors)

    def test_direct_state_mutation_is_detected_by_sweep(self):
        store=tracked_store()
        first=transition(store)
        self.assertTrue(first.accepted)
        store.records[0]=replace(store.records[0],lifecycle_state="CURRENT",is_current=True)
        sweep=stale_state_sweep(store=store,search_policy=policy(),normalizer=normalizer())
        self.assertFalse(sweep.clean)
        self.assertTrue(any(x.startswith("STATE_HISTORY_MISMATCH") for x in sweep.defects))

    def test_creation_state_direct_mutation_is_detected(self):
        store=tracked_store()
        store.records[0]=replace(store.records[0],lifecycle_state="QUARANTINED",is_current=False)
        sweep=stale_state_sweep(store=store,search_policy=policy(),normalizer=normalizer())
        self.assertFalse(sweep.clean)
        self.assertTrue(any(x.startswith("STATE_HISTORY_MISMATCH") for x in sweep.defects))

    def test_unknown_to_state_rejected_before_write(self):
        store=tracked_store()
        result=transition(store,to_state="ACTIVE")
        self.assertFalse(result.accepted)
        self.assertIn("UNKNOWN_TO_STATE",result.errors)
        self.assertEqual(store.all()[0].lifecycle_state,"CURRENT")
        self.assertEqual(store.all_transitions(),())

    def test_unknown_existing_lifecycle_fails_sweep(self):
        store=tracked_store()
        store.records[0]=replace(store.records[0],lifecycle_state="ACTIVE",is_current=False)
        sweep=stale_state_sweep(store=store,search_policy=policy(),normalizer=normalizer())
        self.assertFalse(sweep.clean)
        self.assertTrue(any(x.startswith("UNKNOWN_LIFECYCLE_STATE:") for x in sweep.defects))

    def test_forked_history_is_detected(self):
        store=tracked_store()
        common=dict(
            segment_id="TRACKER",object_id="gold.future.feature",object_version="1",era_id="ERA_1",
            from_state="CURRENT",to_state="QUARANTINED",transition_class=TransitionClass.QUARANTINE,
            reason_class="TEST",reason_ref="decision:test",evidence_ref=None,
            changed_ts="2026-09-19T22:31:00+10:00",changed_by="SALIX_MANAGER",
            authority_ref="owner:test",record_version="1",
            prior_transition_id="creation:ERA_1:gold.future.feature:1",
        )
        store.transitions.extend([
            GovernedStateTransitionRecord(transition_id="T-A",**common),
            GovernedStateTransitionRecord(transition_id="T-B",**common),
        ])
        sweep=stale_state_sweep(store=store,search_policy=policy(),normalizer=normalizer())
        self.assertFalse(sweep.clean)
        self.assertTrue(any(x.startswith("TRANSITION_HISTORY_FORK") for x in sweep.defects))

if __name__=="__main__":
    unittest.main()
