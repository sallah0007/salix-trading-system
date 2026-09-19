import unittest

from tracker_identity import (
    BuiltIdentityCandidate, CanonicalEraBoundary, CanonicalIdentityStore,
    LookupOutcome, NormalizerSpec, SearchPolicy,
    composer_boundary_outcome, safe_intake_built_identity,
)

def policy():
    p=SearchPolicy("safe-intake","1","",("current_active",),("current_active",),{})
    return SearchPolicy(p.policy_id,p.version,p.computed_hash(),p.required_scopes,p.searched_scopes,p.scope_exclusions)

def normalizer():
    n=NormalizerSpec("safe-intake","1","",("EXACT_STRUCTURAL_IDENTITY",))
    return NormalizerSpec(n.normalizer_id,n.version,n.computed_hash(),n.equivalence_classes)

def boundary(**changes):
    vals=dict(
        era_id="ERA_1",version="1",boundary_hash="",effective_ts="2026-09-19T20:47:37+10:00",
        predecessor_era_id="ERA_0",registry_id="SALIX-ERA1-REGISTRY",
        catalogue_id="SALIX-ERA1-FEATURE-CATALOGUE",source_universe_id="SALIX-ERA1-SOURCE-UNIVERSE-001",
        pre_era_content_default="UNRESOLVED_NON_IMPORTABLE",historical_gap_status="UNRESOLVED",
        historical_gap_owner="MANAGER",revisit_trigger="IF_ERA0_ARTIFACT_LOCATED_REVIEW_BEFORE_IMPORT",
        absent_proven=False,created_by="SALIX_MANAGER",approval_authority="OWNER",
        created_ts="2026-09-19T20:47:37+10:00",
    )
    vals.update(changes)
    vals["boundary_hash"]=""
    x=CanonicalEraBoundary(**vals)
    vals["boundary_hash"]=x.computed_hash()
    return CanonicalEraBoundary(**vals)

def candidate(**changes):
    vals=dict(
        feature_id="gold.example.future_feature",feature_version="1",
        definition_hash="",graph_hash="",semantic_definition="future feature",formula="x",lifecycle_state="CURRENT",
        is_current=True,scope="current_active",aliases=(),dependencies=(),
        canonical_survivor=None,instrument="XAUUSD",timeframe="H1",
        source_provider="COMPOSER",lineage_ref="build:future",
    )
    vals.update(changes)
    probe=BuiltIdentityCandidate(**vals)
    from tracker_identity import FeatureDefinitionRecord
    d=FeatureDefinitionRecord(probe.feature_id,probe.feature_version,probe.semantic_definition,probe.formula,probe.dependencies,"ERA_1","","",probe.instrument,probe.timeframe)
    if not vals["definition_hash"]: vals["definition_hash"]=d.computed_definition_hash()
    if not vals["graph_hash"]: vals["graph_hash"]=d.computed_graph_hash()
    return BuiltIdentityCandidate(**vals)

class SafeIntakeEraTests(unittest.TestCase):
    def test_safe_intake_assigns_era_only_from_active_boundary(self):
        store=CanonicalIdentityStore()
        result=safe_intake_built_identity(
            target_store=store,candidate=candidate(),era_boundary=boundary(),
            search_policy=policy(),normalizer=normalizer(),
        )
        self.assertTrue(result.accepted)
        self.assertEqual(result.assigned_era_id,"ERA_1")
        self.assertEqual(store.all()[0].era_id,"ERA_1")

    def test_safe_intake_fails_without_active_boundary(self):
        store=CanonicalIdentityStore()
        result=safe_intake_built_identity(
            target_store=store,candidate=candidate(),era_boundary=None,
            search_policy=policy(),normalizer=normalizer(),
        )
        self.assertFalse(result.accepted)
        self.assertIn("ACTIVE_ERA_BOUNDARY_REQUIRED",result.errors)
        self.assertEqual(store.all(),())

    def test_safe_intake_fails_if_boundary_registry_does_not_bind_store(self):
        store=CanonicalIdentityStore(registry_id="OTHER")
        result=safe_intake_built_identity(
            target_store=store,candidate=candidate(),era_boundary=boundary(),
            search_policy=policy(),normalizer=normalizer(),
        )
        self.assertFalse(result.accepted)
        self.assertEqual(store.all(),())

    def test_safe_intake_fails_if_store_active_era_differs(self):
        store=CanonicalIdentityStore(active_era_id="ERA_0")
        result=safe_intake_built_identity(
            target_store=store,candidate=candidate(),era_boundary=boundary(),
            search_policy=policy(),normalizer=normalizer(),
        )
        self.assertFalse(result.accepted)
        self.assertIn("STORE_ACTIVE_ERA_MISMATCH",result.errors)
        self.assertEqual(store.all(),())

    def test_candidate_cannot_supply_or_override_era(self):
        self.assertNotIn("era_id",BuiltIdentityCandidate.__dataclass_fields__)
        store=CanonicalIdentityStore()
        result=safe_intake_built_identity(
            target_store=store,candidate=candidate(),era_boundary=boundary(),
            search_policy=policy(),normalizer=normalizer(),
        )
        self.assertEqual(result.identity.era_id,boundary().era_id)

    def test_safe_intake_rejects_tampered_definition_hash(self):
        store=CanonicalIdentityStore()
        result=safe_intake_built_identity(
            target_store=store,candidate=candidate(definition_hash="0"*64),era_boundary=boundary(),
            search_policy=policy(),normalizer=normalizer(),
        )
        self.assertFalse(result.accepted)
        self.assertTrue(any(x.startswith("CATALOGUE_DEFINITION_HASH_MISMATCH") for x in result.errors))
        self.assertEqual(store.all(),())

    def test_safe_intake_rejects_tampered_graph_hash(self):
        store=CanonicalIdentityStore()
        result=safe_intake_built_identity(
            target_store=store,candidate=candidate(graph_hash="0"*64),era_boundary=boundary(),
            search_policy=policy(),normalizer=normalizer(),
        )
        self.assertFalse(result.accepted)
        self.assertTrue(any(x.startswith("CATALOGUE_GRAPH_HASH_MISMATCH") for x in result.errors))
        self.assertEqual(store.all(),())

    def test_stale_failure_does_not_mutate_store(self):
        existing=candidate(feature_id="same",feature_version="1")
        first=safe_intake_built_identity(
            target_store=CanonicalIdentityStore(),candidate=existing,era_boundary=boundary(),
            search_policy=policy(),normalizer=normalizer(),
        )
        self.assertTrue(first.accepted)
        store=CanonicalIdentityStore([first.identity])
        second=safe_intake_built_identity(
            target_store=store,candidate=candidate(feature_id="same",feature_version="2"),
            era_boundary=boundary(),search_policy=policy(),normalizer=normalizer(),
        )
        self.assertFalse(second.accepted)
        self.assertEqual(len(store.all()),1)

    def test_composer_boundary_never_receives_era1_absent_as_global_absent(self):
        self.assertEqual(
            composer_boundary_outcome(LookupOutcome.ABSENT_IN_ERA_1),
            LookupOutcome.INCOMPLETE_LOOKUP,
        )
        self.assertEqual(
            composer_boundary_outcome(LookupOutcome.EXACT_CANONICAL_IDENTITY),
            LookupOutcome.EXACT_CANONICAL_IDENTITY,
        )

if __name__=="__main__":
    unittest.main()
