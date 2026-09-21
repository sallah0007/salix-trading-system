import unittest

from tracker_identity import (
    BuiltIdentityCandidate, CanonicalEraBoundary, CanonicalIdentityStore,
    LookupOutcome, MANDATORY_DUPLICATE_CONTROL_SCOPES, NormalizerSpec, SearchPolicy,
    composer_boundary_outcome, governed_normalizer, governed_search_policy, identity_lookup,
    safe_intake_built_identity,
)

def policy():
    p=SearchPolicy("safe-intake","1","",("current_active",),("current_active",),{})
    return SearchPolicy(p.policy_id,p.version,p.computed_hash(),p.required_scopes,p.searched_scopes,p.scope_exclusions)

def normalizer():
    # Governed normalizer: identity_lookup resolves normalizer authority
    # against the Tracker-owned registry.
    return governed_normalizer()

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
        creation_reason_ref="decision:approved-definition",
        created_by="SALIX_MANAGER",authority_ref="owner:era1-intake",
        creation_evidence_ref="evidence:definition-review",
        # Governed content dimensions. Required because ordinary registration is
        # claim-gated and a claim is validated against the candidate's
        # recomputed CONTENT_IDENTITY_KEY: a candidate whose content key cannot
        # be derived can no longer be registered at all. None of these feed
        # computed_definition_hash/computed_graph_hash, so the hash fixtures
        # below are unaffected.
        declared_normalization="NONE",
        causal_time_semantics="SALIX-XAUUSD-BROKER-UTC-TRANSITION-V1",
        completion_semantics="LAST_COMPLETED_BEFORE_T",
        availability_class="RECONSTRUCTED_NOT_OBSERVED",
        price_basis="BID",data_vintage_mode="CURRENT_RECOMPUTED",
        scope_universe="XAUUSD/ERA_1",parameters={"lookback_bars":2},
        fitted_state="NONE",proxy_status="NOT_PROXY",
    )
    vals.update(changes)
    probe=BuiltIdentityCandidate(**vals)
    from tracker_identity import FeatureDefinitionRecord
    d=FeatureDefinitionRecord(probe.feature_id,probe.feature_version,probe.semantic_definition,probe.formula,probe.dependencies,"ERA_1","","",probe.instrument,probe.timeframe)
    if not vals["definition_hash"]: vals["definition_hash"]=d.computed_definition_hash()
    if not vals["graph_hash"]: vals["graph_hash"]=d.computed_graph_hash()
    return BuiltIdentityCandidate(**vals)

def claim_for(store,cand,request_id="REQ-INTAKE"):
    """Obtain the governed claim that registration now requires.

    Must go through identity_lookup: reserve_claim() no longer mints
    registration authority on demand (C-1R), so the claim is issued by a real
    PRE_ID lookup over the candidate's own declared content.
    """
    from tracker_identity import FeatureDefinitionRecord
    d=FeatureDefinitionRecord(
        cand.feature_id,cand.feature_version,cand.semantic_definition,cand.formula,
        cand.dependencies,"ERA_1",cand.definition_hash,cand.graph_hash,
        cand.instrument,cand.timeframe,
        declared_normalization=cand.declared_normalization,
        causal_time_semantics=cand.causal_time_semantics,
        completion_semantics=cand.completion_semantics,
        availability_class=cand.availability_class,
        source_provider=cand.source_provider,
        price_basis=cand.price_basis,
        data_vintage_mode=cand.data_vintage_mode,
        scope_universe=cand.scope_universe,
        parameters=cand.parameters,
        fitted_state=cand.fitted_state,
    )
    for sc in MANDATORY_DUPLICATE_CONTROL_SCOPES:
        store.declare_scope(sc,"EMPTY_VERIFIED")
    result=identity_lookup(
        store=store,
        subject={"subject_mode":"PRE_ID","feature_id":"","feature_version":"",
                 "definition_hash":"","graph_hash":"",
                 "instrument":cand.instrument,"timeframe":cand.timeframe,
                 "lookup_era_scope":"ERA_1_ONLY",
                 "candidate_content":d.declared_content()},
        request_id=request_id,search_policy=governed_search_policy(),
        normalizer=normalizer())
    assert result.absent_claim_token is not None,result.errors
    return request_id

class SafeIntakeEraTests(unittest.TestCase):
    def test_safe_intake_assigns_era_only_from_active_boundary(self):
        store=CanonicalIdentityStore()
        rid=claim_for(store,candidate())
        result=safe_intake_built_identity(
            target_store=store,candidate=candidate(claim_request_id=rid),era_boundary=boundary(),
            search_policy=policy(),normalizer=normalizer(),
        )
        # Registration is fail-closed (C-1R), so the era assignment is proven
        # from assigned_era_id rather than from a written row. Reaching the
        # terminal authority gate proves era binding, definition hashes,
        # content key and claim validation all passed.
        self.assertFalse(result.accepted)
        self.assertTrue(any("CLAIM_NOT_CONSTRUCTION_AUTHORIZED" in e for e in result.errors),
                        result.errors)
        self.assertEqual(result.assigned_era_id,"ERA_1")
        self.assertEqual(store.all(),())
        self.assertEqual(store.all_creation_records(),())

    def test_safe_intake_requires_initial_state_justification(self):
        store=CanonicalIdentityStore()
        result=safe_intake_built_identity(
            target_store=store,candidate=candidate(creation_reason_ref=None),era_boundary=boundary(),
            search_policy=policy(),normalizer=normalizer(),
        )
        self.assertFalse(result.accepted)
        self.assertIn("CREATION_REASON_REF_REQUIRED",result.errors)
        self.assertEqual(store.all(),())
        self.assertEqual(store.all_creation_records(),())

    def test_safe_intake_requires_creation_actor_and_authority(self):
        store=CanonicalIdentityStore()
        result=safe_intake_built_identity(
            target_store=store,candidate=candidate(created_by=None,authority_ref=None),era_boundary=boundary(),
            search_policy=policy(),normalizer=normalizer(),
        )
        self.assertFalse(result.accepted)
        self.assertIn("CREATED_BY_REQUIRED",result.errors)
        self.assertIn("CREATION_AUTHORITY_REF_REQUIRED",result.errors)

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
        rid=claim_for(store,candidate())
        result=safe_intake_built_identity(
            target_store=store,candidate=candidate(claim_request_id=rid),era_boundary=boundary(),
            search_policy=policy(),normalizer=normalizer(),
        )
        # Era comes from the boundary, never from the candidate. Asserted via
        # assigned_era_id because no row is written while registration is
        # fail-closed.
        self.assertEqual(result.assigned_era_id,boundary().era_id)

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

    def test_validation_scope_requires_current_lifecycle(self):
        bad=candidate(scope="validation",lifecycle_state="VALIDATION_ONLY")
        store=CanonicalIdentityStore()
        result=safe_intake_built_identity(
            target_store=store,candidate=bad,era_boundary=boundary(),
            search_policy=policy(),normalizer=normalizer(),
        )
        self.assertFalse(result.accepted)
        self.assertIn("VALIDATION_SCOPE_REQUIRES_CURRENT_LIFECYCLE",result.errors)
        self.assertEqual(store.all(),())

    def test_validation_scope_requires_current_identity(self):
        bad=candidate(scope="validation",lifecycle_state="CURRENT",is_current=False)
        store=CanonicalIdentityStore()
        result=safe_intake_built_identity(
            target_store=store,candidate=bad,era_boundary=boundary(),
            search_policy=policy(),normalizer=normalizer(),
        )
        self.assertFalse(result.accepted)
        self.assertIn("VALIDATION_SCOPE_REQUIRES_CURRENT_IDENTITY",result.errors)
        self.assertEqual(store.all(),())

    def test_refused_intake_does_not_mutate_store(self):
        """Was: test_stale_failure_does_not_mutate_store.

        A STALE failure downstream of a successful first registration is
        unreachable while registration is fail-closed (C-1R). The non-mutation
        proposition is kept and proven at the authority gate instead: a fully
        valid candidate holding a real governed claim writes nothing.
        """
        store=CanonicalIdentityStore()
        rid=claim_for(store,candidate(feature_id="same",feature_version="1"),"REQ-S1")
        result=safe_intake_built_identity(
            target_store=store,
            candidate=candidate(feature_id="same",feature_version="1",claim_request_id=rid),
            era_boundary=boundary(),search_policy=policy(),normalizer=normalizer(),
        )
        self.assertFalse(result.accepted)
        self.assertTrue(any("CLAIM_NOT_CONSTRUCTION_AUTHORIZED" in e for e in result.errors),
                        result.errors)
        self.assertEqual(store.all(),())
        self.assertEqual(store.all_creation_records(),())
        # The claim is not consumed by a refused registration.
        self.assertEqual([c.state for c in store.claims],["ACTIVE"])

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
