import unittest
from datetime import datetime, timedelta, timezone

from tracker_identity import (
    CanonicalIdentityStore, FeatureIdentity, LookupOutcome,
    NormalizerSpec, SearchPolicy, identity_lookup, stale_state_sweep,
)
from tracker_identity import (
    MANDATORY_DUPLICATE_CONTROL_SCOPES,
    BuiltIdentityCandidate, CanonicalEraBoundary, FeatureDefinitionRecord,
    build_content_identity_key, composer_boundary_outcome,
    governed_search_policy, resolve_governed_search_policy,
    safe_intake_built_identity,
)

REQUIRED_SCOPES=(
    "current_active","active_on_demand","validation","experimental_unclassified",
    "quarantined","dormant","suppressed","deprecated","retired","rejected_invalid",
    "historical_prior_version","canonical_survivor_discarded","pending_claimed_in_flight",
)

def complete_policy():
    provisional=SearchPolicy(
        policy_id="tracker.identity.search",version="1",policy_hash="",
        required_scopes=REQUIRED_SCOPES,searched_scopes=REQUIRED_SCOPES,scope_exclusions={},
    )
    return SearchPolicy(
        policy_id=provisional.policy_id,version=provisional.version,
        policy_hash=provisional.computed_hash(),
        required_scopes=provisional.required_scopes,
        searched_scopes=provisional.searched_scopes,
        scope_exclusions=provisional.scope_exclusions,
    )

def normalizer(classes=("EXACT_STRUCTURAL_IDENTITY",)):
    provisional=NormalizerSpec(
        normalizer_id="tracker.identity.normalizer",version="1",
        normalizer_hash="",equivalence_classes=classes,
    )
    return NormalizerSpec(
        normalizer_id=provisional.normalizer_id,version=provisional.version,
        normalizer_hash=provisional.computed_hash(),
        equivalence_classes=provisional.equivalence_classes,
    )

def subject(version="1",instrument="EURUSD"):
    return {
        "feature_id":"returns.1bar","feature_version":version,
        "definition_hash":"abc","graph_hash":"def",
        "instrument":instrument,"timeframe":"H1","lookup_era_scope":"ERA_1_ONLY",
    }

def record(version="1",*,current=True,lifecycle="CURRENT",instrument="EURUSD",scope="current_active",survivor=None):
    return FeatureIdentity(
        feature_id="returns.1bar",feature_version=version,
        definition_hash="abc",graph_hash="def",
        lifecycle_state=lifecycle,is_current=current,scope=scope,
        canonical_survivor=survivor,instrument=instrument,timeframe="H1",
    )

class IdentitySurfaceTests(unittest.TestCase):
    def test_unspecified_era_scope_defaults_all_eras_and_never_absent(self):
        s=subject(); s.pop("lookup_era_scope")
        result=identity_lookup(store=CanonicalIdentityStore(),subject=s,request_id="REQ-ALL-ERAS",search_policy=complete_policy(),normalizer=normalizer())
        self.assertFalse(result.lookup_complete)
        self.assertEqual(result.outcome,LookupOutcome.INCOMPLETE_LOOKUP)
        self.assertTrue(any("ALL_ERAS_COVERAGE_INCOMPLETE" in e for e in result.errors))
        self.assertIsNone(result.absent_claim_token)

    def test_era1_lookup_ignores_era0_rows(self):
        legacy=record(); legacy=FeatureIdentity(**{**legacy.__dict__,"era_id":"ERA_0"})
        result=identity_lookup(store=CanonicalIdentityStore([legacy]),subject=subject(),request_id="REQ-ERA1-ONLY",search_policy=complete_policy(),normalizer=normalizer())
        self.assertEqual(result.outcome,LookupOutcome.ABSENT_IN_ERA_1)
        self.assertTrue(result.lookup_complete)

    def test_empty_store_complete_lookup_returns_absent(self):
        result=identity_lookup(
            store=CanonicalIdentityStore(),subject=subject(),request_id="REQ-EMPTY",
            search_policy=complete_policy(),normalizer=normalizer(),
            now=datetime(2026,9,19,tzinfo=timezone.utc),
        )
        self.assertTrue(result.lookup_complete)
        self.assertEqual(result.outcome,LookupOutcome.ABSENT_IN_ERA_1)
        self.assertIsNotNone(result.absent_claim_token)
        self.assertFalse(result.absent_claim_token.authorizes_construction)

    def test_exact_match(self):
        result=identity_lookup(
            store=CanonicalIdentityStore([record()]),subject=subject(),request_id="REQ-EXACT",
            search_policy=complete_policy(),normalizer=normalizer(),
        )
        self.assertTrue(result.lookup_complete)
        self.assertEqual(result.outcome,LookupOutcome.EXACT_CANONICAL_IDENTITY)

    def test_near_match_requires_review(self):
        result=identity_lookup(
            store=CanonicalIdentityStore([record(version="2")]),subject=subject(version="1"),
            request_id="REQ-NEAR",search_policy=complete_policy(),normalizer=normalizer(),
        )
        self.assertTrue(result.lookup_complete)
        self.assertEqual(result.outcome,LookupOutcome.NEAR_MATCH)

    def test_incomplete_scope_cannot_emit_absent(self):
        p=complete_policy()
        provisional=SearchPolicy(
            policy_id=p.policy_id,version=p.version,policy_hash="",
            required_scopes=p.required_scopes,searched_scopes=p.required_scopes[:-1],scope_exclusions={},
        )
        incomplete=SearchPolicy(
            policy_id=provisional.policy_id,version=provisional.version,
            policy_hash=provisional.computed_hash(),
            required_scopes=provisional.required_scopes,
            searched_scopes=provisional.searched_scopes,
            scope_exclusions=provisional.scope_exclusions,
        )
        result=identity_lookup(
            store=CanonicalIdentityStore(),subject=subject(),request_id="REQ-INCOMPLETE",
            search_policy=incomplete,normalizer=normalizer(),
        )
        self.assertFalse(result.lookup_complete)
        self.assertEqual(result.outcome,LookupOutcome.INCOMPLETE_LOOKUP)
        self.assertIsNone(result.absent_claim_token)

    def test_d1_store_scope_not_declared_cannot_complete(self):
        hidden=record(scope="X")
        result=identity_lookup(
            store=CanonicalIdentityStore([hidden]),subject=subject(),request_id="REQ-D1",
            search_policy=complete_policy(),normalizer=normalizer(),
        )
        self.assertFalse(result.lookup_complete)
        self.assertEqual(result.outcome,LookupOutcome.INCOMPLETE_LOOKUP)
        self.assertTrue(any("UNENUMERATED_STORE_SCOPE:X" in e for e in result.errors))
        self.assertIsNone(result.absent_claim_token)

    def test_d2_superseded_exact_does_not_resolve_exact(self):
        stale=record(current=False,lifecycle="SUPERSEDED")
        result=identity_lookup(
            store=CanonicalIdentityStore([stale]),subject=subject(),request_id="REQ-D2",
            search_policy=complete_policy(),normalizer=normalizer(),
        )
        self.assertTrue(result.lookup_complete)
        self.assertEqual(result.outcome,LookupOutcome.NEAR_MATCH)
        self.assertIsNone(result.exact_match)

    def test_d2_current_and_superseded_same_key_is_not_false_ambiguity(self):
        current=record(current=True,lifecycle="CURRENT")
        stale=record(current=False,lifecycle="SUPERSEDED")
        result=identity_lookup(
            store=CanonicalIdentityStore([current,stale]),subject=subject(),request_id="REQ-D2B",
            search_policy=complete_policy(),normalizer=normalizer(),
        )
        self.assertTrue(result.lookup_complete)
        self.assertEqual(result.outcome,LookupOutcome.EXACT_CANONICAL_IDENTITY)
        self.assertEqual(result.exact_match,current)

    def test_d2_noncurrent_survivor_is_review_not_exact(self):
        stale=record(current=False,lifecycle="SUPERSEDED",survivor="returns.current")
        survivor=FeatureIdentity(
            feature_id="returns.current",feature_version="2",definition_hash="xyz",graph_hash="uvw",
            lifecycle_state="CURRENT",is_current=True,scope="current_active",
            instrument="EURUSD",timeframe="H1",
        )
        result=identity_lookup(
            store=CanonicalIdentityStore([stale,survivor]),subject=subject(),request_id="REQ-SURVIVOR",
            search_policy=complete_policy(),normalizer=normalizer(),
        )
        self.assertTrue(result.lookup_complete)
        self.assertEqual(result.outcome,LookupOutcome.NEAR_MATCH)
        self.assertEqual(result.pending_collision_result,"CANONICAL_SURVIVOR_REVIEW_REQUIRED")

    def test_d3_unsupported_normalizer_class_fails_closed(self):
        n=normalizer(classes=("UNDECLARED_FUZZY_EQUIVALENCE",))
        result=identity_lookup(
            store=CanonicalIdentityStore(),subject=subject(),request_id="REQ-D3",
            search_policy=complete_policy(),normalizer=n,
        )
        self.assertFalse(result.lookup_complete)
        self.assertEqual(result.outcome,LookupOutcome.INCOMPLETE_LOOKUP)
        self.assertTrue(any("UNSUPPORTED_EQUIVALENCE_CLASS" in e for e in result.errors))

    def test_d3_normalizer_hash_mismatch_fails_closed(self):
        n=NormalizerSpec(
            normalizer_id="tracker.identity.normalizer",version="1",
            normalizer_hash="wrong",equivalence_classes=("EXACT_STRUCTURAL_IDENTITY",),
        )
        result=identity_lookup(
            store=CanonicalIdentityStore(),subject=subject(),request_id="REQ-D3HASH",
            search_policy=complete_policy(),normalizer=n,
        )
        self.assertFalse(result.lookup_complete)
        self.assertTrue(any("NORMALIZER_HASH_MISMATCH" in e for e in result.errors))

    def test_policy_hash_mismatch_fails_closed(self):
        p=complete_policy()
        bad=SearchPolicy(
            policy_id=p.policy_id,version=p.version,policy_hash="wrong",
            required_scopes=p.required_scopes,searched_scopes=p.searched_scopes,scope_exclusions={},
        )
        result=identity_lookup(
            store=CanonicalIdentityStore(),subject=subject(),request_id="REQ-POLICYHASH",
            search_policy=bad,normalizer=normalizer(),
        )
        self.assertFalse(result.lookup_complete)
        self.assertTrue(any("SEARCH_POLICY_HASH_MISMATCH" in e for e in result.errors))

    def test_gold_identity_is_not_eurusd_exact_match(self):
        result=identity_lookup(
            store=CanonicalIdentityStore([record(instrument="XAUUSD")]),
            subject=subject(instrument="EURUSD"),request_id="REQ-INSTRUMENT",
            search_policy=complete_policy(),normalizer=normalizer(),
        )
        self.assertEqual(result.outcome,LookupOutcome.NEAR_MATCH)

    def test_validation_scope_record_is_hidden_from_ordinary_lookup(self):
        validation=FeatureIdentity(
            feature_id="returns.1bar",feature_version="1",definition_hash="abc",graph_hash="def",
            lifecycle_state="CURRENT",is_current=True,scope="validation",era_id="ERA_1",
            instrument="EURUSD",timeframe="H1",
        )
        result=identity_lookup(
            store=CanonicalIdentityStore([validation]),subject=subject(),request_id="REQ-VALID-HIDDEN",
            search_policy=complete_policy(),normalizer=normalizer(),
        )
        self.assertEqual(result.outcome,LookupOutcome.ABSENT_IN_ERA_1)

    def test_validation_scope_record_requires_explicit_validation_access(self):
        validation=FeatureIdentity(
            feature_id="returns.1bar",feature_version="1",definition_hash="abc",graph_hash="def",
            lifecycle_state="CURRENT",is_current=True,scope="validation",era_id="ERA_1",
            instrument="EURUSD",timeframe="H1",
        )
        s=subject(); s["include_validation_scope"]=True
        result=identity_lookup(
            store=CanonicalIdentityStore([validation]),subject=s,request_id="REQ-VALID-EXPLICIT",
            search_policy=complete_policy(),normalizer=normalizer(),
        )
        self.assertEqual(result.outcome,LookupOutcome.EXACT_CANONICAL_IDENTITY)

    def test_v1_to_v2_successor_preserves_version_history(self):
        v1=FeatureIdentity(
            feature_id="returns.1bar",feature_version="1",definition_hash="abc",graph_hash="def",
            lifecycle_state="SUPERSEDED",is_current=False,scope="historical_prior_version",era_id="ERA_1",
            canonical_survivor="returns.1bar",instrument="EURUSD",timeframe="H1",
        )
        v2=FeatureIdentity(
            feature_id="returns.1bar",feature_version="2",definition_hash="xyz",graph_hash="uvw",
            lifecycle_state="CURRENT",is_current=True,scope="current_active",era_id="ERA_1",
            instrument="EURUSD",timeframe="H1",
        )
        store=CanonicalIdentityStore([v1,v2])
        sweep=stale_state_sweep(store=store,search_policy=complete_policy(),normalizer=normalizer())
        self.assertTrue(sweep.clean)
        old=identity_lookup(store=store,subject=subject(version="1"),request_id="REQ-V1",search_policy=complete_policy(),normalizer=normalizer())
        new_subject={"feature_id":"returns.1bar","feature_version":"2","definition_hash":"xyz","graph_hash":"uvw","instrument":"EURUSD","timeframe":"H1","lookup_era_scope":"ERA_1_ONLY"}
        new=identity_lookup(store=store,subject=new_subject,request_id="REQ-V2",search_policy=complete_policy(),normalizer=normalizer())
        self.assertEqual(old.outcome,LookupOutcome.NEAR_MATCH)
        self.assertEqual(new.outcome,LookupOutcome.EXACT_CANONICAL_IDENTITY)

    def test_validation_scope_with_unknown_lifecycle_fails_sweep(self):
        bad=FeatureIdentity(
            feature_id="validation.bad",feature_version="1",definition_hash="1",graph_hash="1",
            lifecycle_state="VALIDATION_ONLY",is_current=True,scope="validation",era_id="ERA_1",
        )
        sweep=stale_state_sweep(
            store=CanonicalIdentityStore([bad]),search_policy=complete_policy(),normalizer=normalizer(),
        )
        self.assertFalse(sweep.clean)
        self.assertTrue(any("VALIDATION_SCOPE_NONCURRENT_LIFECYCLE" in d for d in sweep.defects))

    def test_validation_scope_noncurrent_identity_fails_sweep(self):
        bad=FeatureIdentity(
            feature_id="validation.bad",feature_version="1",definition_hash="1",graph_hash="1",
            lifecycle_state="CURRENT",is_current=False,scope="validation",era_id="ERA_1",
        )
        sweep=stale_state_sweep(
            store=CanonicalIdentityStore([bad]),search_policy=complete_policy(),normalizer=normalizer(),
        )
        self.assertFalse(sweep.clean)
        self.assertTrue(any("VALIDATION_SCOPE_NONCURRENT_IDENTITY" in d for d in sweep.defects))

    def test_stale_superseded_current_fails_sweep(self):
        sweep=stale_state_sweep(
            store=CanonicalIdentityStore([record(current=True,lifecycle="SUPERSEDED")]),
            search_policy=complete_policy(),normalizer=normalizer(),
        )
        self.assertFalse(sweep.clean)

    def test_dangling_dependency_fails_sweep(self):
        bad=FeatureIdentity(
            feature_id="feature.a",feature_version="1",definition_hash="1",graph_hash="1",
            lifecycle_state="CURRENT",is_current=True,scope="current_active",
            dependencies=("missing.feature",),
        )
        sweep=stale_state_sweep(
            store=CanonicalIdentityStore([bad]),search_policy=complete_policy(),normalizer=normalizer(),
        )
        self.assertFalse(sweep.clean)

    def test_test_fixture_in_live_scope_fails_sweep(self):
        fixture=FeatureIdentity(
            feature_id="fixture.test.feature",feature_version="1",definition_hash="1",graph_hash="1",
            lifecycle_state="CURRENT",is_current=True,scope="current_active",
        )
        sweep=stale_state_sweep(
            store=CanonicalIdentityStore([fixture]),search_policy=complete_policy(),normalizer=normalizer(),
        )
        self.assertFalse(sweep.clean)

    def test_alias_collision_fails_sweep(self):
        a=FeatureIdentity("feature.a","1","1","1","CURRENT",True,"current_active",aliases=("shared.alias",))
        b=FeatureIdentity("feature.b","1","2","2","CURRENT",True,"current_active",aliases=("shared.alias",))
        sweep=stale_state_sweep(
            store=CanonicalIdentityStore([a,b]),search_policy=complete_policy(),normalizer=normalizer(),
        )
        self.assertFalse(sweep.clean)

# ---------------------------------------------------------------------------
# GOLD ID GATE HARDENING — MANDATORY NEGATIVE CONTROLS NC01-NC27
#
# C-1 claimless registration bypass
# H-1 mandatory-scope false absence
# M-1 caller-created search policy authority
# ---------------------------------------------------------------------------

GATE_CONTENT={
    "normalized_definition_graph":"LN(DIV(C[t],C[t-1]))",
    "dependency_closure":(),
    "parameters":{"lookback_bars":2},
    "declared_normalization":"NONE",
    "causal_time_semantics":"SALIX-XAUUSD-BROKER-UTC-TRANSITION-V1",
    "completion_semantics":"LAST_COMPLETED_BEFORE_T",
    "availability_class":"RECONSTRUCTED_NOT_OBSERVED",
    "source_provider":"COMPOSER",
    "price_basis":"BID",
    "data_vintage_mode":"CURRENT_RECOMPUTED",
    "instrument":"XAUUSD","timeframe":"H1",
    "scope_universe":"XAUUSD/ERA_1",
    "fitted_state":"NONE",
}

class _Clock:
    def __init__(self,at): self.at=at
    def __call__(self): return self.at
    def advance(self,seconds): self.at=self.at+timedelta(seconds=seconds)

def gate_key(**overrides):
    payload=dict(GATE_CONTENT); payload.update(overrides)
    key,errors=build_content_identity_key(payload)
    assert not errors,errors
    return key

def gate_boundary():
    vals=dict(
        era_id="ERA_1",version="1",boundary_hash="",effective_ts="2026-09-19T20:47:37+10:00",
        predecessor_era_id="ERA_0",registry_id="SALIX-ERA1-REGISTRY",
        catalogue_id="SALIX-ERA1-FEATURE-CATALOGUE",
        source_universe_id="SALIX-ERA1-SOURCE-UNIVERSE-001",
        pre_era_content_default="UNRESOLVED_NON_IMPORTABLE",historical_gap_status="UNRESOLVED",
        historical_gap_owner="MANAGER",revisit_trigger="IF_ERA0_ARTIFACT_LOCATED_REVIEW_BEFORE_IMPORT",
        absent_proven=False,created_by="SALIX_MANAGER",approval_authority="OWNER",
        created_ts="2026-09-19T20:47:37+10:00",
    )
    x=CanonicalEraBoundary(**vals)
    vals["boundary_hash"]=x.computed_hash()
    return CanonicalEraBoundary(**vals)

def gate_candidate(feature_id="gold.logret",claim_request_id=None,**changes):
    vals=dict(
        feature_id=feature_id,feature_version="1",
        definition_hash="",graph_hash="",
        semantic_definition="h1 log return",
        formula=GATE_CONTENT["normalized_definition_graph"],
        lifecycle_state="CURRENT",is_current=True,scope="current_active",
        aliases=(),dependencies=GATE_CONTENT["dependency_closure"],
        canonical_survivor=None,instrument="XAUUSD",timeframe="H1",
        source_provider="COMPOSER",lineage_ref="build:logret",
        creation_reason_ref="decision:approved-definition",
        created_by="SALIX_MANAGER",authority_ref="owner:era1-intake",
        creation_evidence_ref="evidence:definition-review",
        declared_normalization="NONE",
        causal_time_semantics=GATE_CONTENT["causal_time_semantics"],
        completion_semantics=GATE_CONTENT["completion_semantics"],
        availability_class=GATE_CONTENT["availability_class"],
        price_basis="BID",data_vintage_mode="CURRENT_RECOMPUTED",
        scope_universe="XAUUSD/ERA_1",parameters={"lookback_bars":2},
        fitted_state="NONE",proxy_status="NOT_PROXY",
        claim_request_id=claim_request_id,
    )
    vals.update(changes)
    probe=BuiltIdentityCandidate(**vals)
    d=FeatureDefinitionRecord(probe.feature_id,probe.feature_version,
                              probe.semantic_definition,probe.formula,
                              probe.dependencies,"ERA_1","","",
                              probe.instrument,probe.timeframe)
    if not vals["definition_hash"]: vals["definition_hash"]=d.computed_definition_hash()
    if not vals["graph_hash"]: vals["graph_hash"]=d.computed_graph_hash()
    return BuiltIdentityCandidate(**vals)

def gate_intake(store,cand):
    return safe_intake_built_identity(
        target_store=store,candidate=cand,era_boundary=gate_boundary(),
        search_policy=complete_policy(),normalizer=normalizer())

def keyed_row(key,feature_id="gold.logret.imported",current=True,scope="current_active"):
    return FeatureIdentity(
        feature_id=feature_id,feature_version="1",
        definition_hash="imported-d",graph_hash="imported-g",
        lifecycle_state="CURRENT" if current else "SUPERSEDED",
        is_current=current,scope=scope,era_id="ERA_1",
        content_key_composite=key.composite,
        content_key_definition=key.definition_semantics,
        content_key_causal_time=key.causal_time,
        content_key_provenance=key.provenance_source,
        content_key_scope=key.scope_eligibility,
        content_key_fitted=key.fitted_learned_state,
        content_key_algorithm_id=key.algorithm_id,
    )

def verified_store(records=()):
    store=CanonicalIdentityStore(list(records))
    for sc in MANDATORY_DUPLICATE_CONTROL_SCOPES:
        store.declare_scope(sc,"EMPTY_VERIFIED")
    return store

def pre_id_subject(**overrides):
    content=dict(GATE_CONTENT); content.update(overrides.pop("content",{}))
    s={
        "subject_mode":"PRE_ID",
        "feature_id":"","feature_version":"","definition_hash":"","graph_hash":"",
        "instrument":"XAUUSD","timeframe":"H1","lookup_era_scope":"ERA_1_ONLY",
        "candidate_content":content,
    }
    s.update(overrides)
    return s

def ungoverned_policy(policy_id="attacker.policy",version="1",
                      required=None,searched=None,exclusions=None,policy_hash=None):
    """Build a SELF-CONSISTENT policy. Its own hash always matches its own
    fields — which is exactly why self-consistency cannot be authority."""
    required=MANDATORY_DUPLICATE_CONTROL_SCOPES if required is None else required
    searched=required if searched is None else searched
    exclusions={} if exclusions is None else exclusions
    p=SearchPolicy(policy_id,version,"",tuple(required),tuple(searched),dict(exclusions))
    return SearchPolicy(p.policy_id,p.version,
                        p.computed_hash() if policy_hash is None else policy_hash,
                        p.required_scopes,p.searched_scopes,p.scope_exclusions)

class GateHardeningNegativeControls(unittest.TestCase):

    # ---- C-1: claim mandatory for ordinary canonical registration ----------

    def test_NC01_safe_intake_claim_request_id_none_fails(self):
        store=CanonicalIdentityStore()
        r=gate_intake(store,gate_candidate(claim_request_id=None))
        self.assertFalse(r.accepted)
        self.assertIn("CLAIM_REQUEST_ID_REQUIRED",r.errors)
        self.assertEqual(store.all(),())

    def test_NC02_safe_intake_empty_claim_request_id_fails(self):
        store=CanonicalIdentityStore()
        r=gate_intake(store,gate_candidate(claim_request_id=""))
        self.assertFalse(r.accepted)
        self.assertIn("CLAIM_REQUEST_ID_REQUIRED",r.errors)
        self.assertEqual(store.all(),())

    def test_NC03_safe_intake_whitespace_claim_request_id_fails(self):
        store=CanonicalIdentityStore()
        r=gate_intake(store,gate_candidate(claim_request_id="   \t "))
        self.assertFalse(r.accepted)
        self.assertIn("CLAIM_REQUEST_ID_REQUIRED",r.errors)
        self.assertEqual(store.all(),())

    def test_NC04_fabricated_claim_fails(self):
        store=CanonicalIdentityStore()
        r=gate_intake(store,gate_candidate(claim_request_id="REQ-NEVER-ISSUED"))
        self.assertFalse(r.accepted)
        self.assertTrue(any("CLAIM_NOT_FOUND" in e for e in r.errors),r.errors)
        self.assertEqual(store.all(),())

    def test_NC05_expired_claim_fails(self):
        store=CanonicalIdentityStore()
        clock=_Clock(datetime.now(timezone.utc)); store._clock=clock
        store.reserve_claim(content_key_composite=gate_key().composite,request_id="REQ-EXP")
        clock.advance(10_000)
        r=gate_intake(store,gate_candidate(claim_request_id="REQ-EXP"))
        self.assertFalse(r.accepted)
        self.assertTrue(any("CLAIM_NOT_ACTIVE" in e for e in r.errors),r.errors)
        self.assertEqual(store.all(),())

    def test_NC06_released_claim_fails(self):
        store=CanonicalIdentityStore()
        rec,_=store.reserve_claim(content_key_composite=gate_key().composite,
                                  request_id="REQ-REL")
        self.assertTrue(store.release_claim(claim_id=rec.claim_id,reason="ABANDONED"))
        r=gate_intake(store,gate_candidate(claim_request_id="REQ-REL"))
        self.assertFalse(r.accepted)
        self.assertTrue(any("CLAIM_NOT_ACTIVE" in e for e in r.errors),r.errors)
        self.assertEqual(store.all(),())

    def test_NC07_claim_bound_to_a_different_request_fails(self):
        store=CanonicalIdentityStore()
        store.reserve_claim(content_key_composite=gate_key().composite,request_id="REQ-OWNER")
        r=gate_intake(store,gate_candidate(claim_request_id="REQ-IMPOSTOR"))
        self.assertFalse(r.accepted)
        self.assertTrue(any("CLAIM_NOT_FOUND" in e for e in r.errors),r.errors)
        self.assertEqual(store.all(),())
        self.assertEqual(store.claims[0].state,"ACTIVE")

    def test_NC08_claim_bound_to_a_different_content_key_fails(self):
        store=CanonicalIdentityStore()
        # Claim issued for ASK content; candidate declares BID content.
        store.reserve_claim(content_key_composite=gate_key(price_basis="ASK").composite,
                            request_id="REQ-ASK")
        r=gate_intake(store,gate_candidate(claim_request_id="REQ-ASK"))
        self.assertFalse(r.accepted)
        self.assertTrue(any("CLAIM_NOT_FOUND" in e for e in r.errors),r.errors)
        self.assertEqual(store.all(),())

    def test_NC09_direct_commit_registration_without_claim_fails(self):
        """The gate is in the store, not only in safe_intake."""
        store=CanonicalIdentityStore()
        ok,error=store.commit_registration(
            identity=keyed_row(gate_key()),creation=object(),
            content_key_composite=None,request_id=None)
        self.assertFalse(ok)
        self.assertEqual(error,"CLAIM_REQUIRED_FOR_REGISTRATION")
        self.assertEqual(store.all(),())
        # A content key without a request id is still not a claim.
        ok2,error2=store.commit_registration(
            identity=keyed_row(gate_key()),creation=object(),
            content_key_composite=gate_key().composite,request_id="   ")
        self.assertFalse(ok2)
        self.assertEqual(error2,"CLAIM_REQUIRED_FOR_REGISTRATION")
        self.assertEqual(store.all(),())

    def test_NC10_incomplete_lookup_cannot_produce_successful_ordinary_intake(self):
        """An incomplete lookup issues no claim, and no claim means no registry."""
        store=verified_store()
        result=identity_lookup(store=store,subject=pre_id_subject(),
                               request_id="REQ-INCOMPLETE",
                               search_policy=ungoverned_policy(),normalizer=normalizer())
        self.assertEqual(result.outcome,LookupOutcome.INCOMPLETE_LOOKUP)
        self.assertIsNone(result.absent_claim_token)
        self.assertEqual(store.claims,[])
        r=gate_intake(store,gate_candidate(claim_request_id="REQ-INCOMPLETE"))
        self.assertFalse(r.accepted)
        self.assertEqual(store.all(),())

    def test_NC11_era1_structural_absence_does_not_authorize_global_feature_id(self):
        store=verified_store()
        result=identity_lookup(store=store,subject=pre_id_subject(),request_id="REQ-ABS",
                               search_policy=governed_search_policy(),normalizer=normalizer())
        self.assertEqual(result.outcome,LookupOutcome.ABSENT_EXACT_STRUCTURAL_IN_ERA_1)
        self.assertIsNotNone(result.absent_claim_token)
        self.assertFalse(result.absent_claim_token.authorizes_construction)
        self.assertEqual(result.semantic_uniqueness,"UNRESOLVED_NOT_CERTIFIED")
        # Composer has no era concept, so this may never cross as global ABSENT.
        self.assertEqual(composer_boundary_outcome(result.outcome),
                         LookupOutcome.INCOMPLETE_LOOKUP)

    # ---- H-1: mandatory scope false absence --------------------------------

    def test_NC12_excluding_a_mandatory_scope_holding_a_duplicate_is_incomplete(self):
        key=gate_key()
        store=verified_store([keyed_row(key)])
        excluded=ungoverned_policy(
            policy_id="tracker.identity.search",version="1",
            searched=tuple(s for s in MANDATORY_DUPLICATE_CONTROL_SCOPES if s!="current_active"),
            exclusions={"current_active":"OPERATOR_CHOICE"})
        result=identity_lookup(store=store,subject=pre_id_subject(),request_id="REQ-EXC",
                               search_policy=excluded,normalizer=normalizer())
        self.assertEqual(result.outcome,LookupOutcome.INCOMPLETE_LOOKUP)
        self.assertIsNone(result.absent_claim_token)
        self.assertEqual(store.claims,[])
        self.assertTrue(any("MANDATORY_SCOPE_EXCLUDED" in e for e in result.errors),
                        result.errors)

    def test_NC13_removing_current_active_from_required_scopes_fails(self):
        reduced=tuple(s for s in MANDATORY_DUPLICATE_CONTROL_SCOPES if s!="current_active")
        policy=ungoverned_policy(policy_id="tracker.identity.search",version="1",
                                 required=reduced,searched=reduced)
        result=identity_lookup(store=verified_store(),subject=pre_id_subject(),
                               request_id="REQ-NOCA",search_policy=policy,
                               normalizer=normalizer())
        self.assertEqual(result.outcome,LookupOutcome.INCOMPLETE_LOOKUP)
        self.assertIsNone(result.absent_claim_token)
        self.assertTrue(any("MANDATORY_SCOPE_NOT_SEARCHED" in e for e in result.errors),
                        result.errors)

    def test_NC14_removing_a_mandatory_historical_scope_fails(self):
        reduced=tuple(s for s in MANDATORY_DUPLICATE_CONTROL_SCOPES
                      if s!="historical_prior_version")
        policy=ungoverned_policy(policy_id="tracker.identity.search",version="1",
                                 required=reduced,searched=reduced)
        result=identity_lookup(store=verified_store(),subject=pre_id_subject(),
                               request_id="REQ-NOHIST",search_policy=policy,
                               normalizer=normalizer())
        self.assertEqual(result.outcome,LookupOutcome.INCOMPLETE_LOOKUP)
        self.assertIsNone(result.absent_claim_token)
        self.assertTrue(any("MANDATORY_SCOPE_NOT_SEARCHED" in e for e in result.errors),
                        result.errors)

    # ---- M-1: governed search policy authority -----------------------------

    def test_NC15_self_hashed_ungoverned_policy_fails(self):
        policy=ungoverned_policy(policy_id="attacker.policy",version="1")
        # The attacker's policy IS internally consistent. That is the point.
        self.assertEqual(policy.completeness_errors(),())
        result=identity_lookup(store=verified_store(),subject=pre_id_subject(),
                               request_id="REQ-UNGOV",search_policy=policy,
                               normalizer=normalizer())
        self.assertEqual(result.outcome,LookupOutcome.INCOMPLETE_LOOKUP)
        self.assertIsNone(result.absent_claim_token)
        self.assertTrue(any("SEARCH_POLICY_NOT_GOVERNED" in e for e in result.errors),
                        result.errors)

    def test_NC16_same_id_version_with_changed_scopes_fails(self):
        spoof=ungoverned_policy(policy_id="tracker.identity.search",version="1",
                                required=MANDATORY_DUPLICATE_CONTROL_SCOPES+("invented_scope",),
                                searched=MANDATORY_DUPLICATE_CONTROL_SCOPES+("invented_scope",))
        self.assertEqual(spoof.completeness_errors(),())
        errors=resolve_governed_search_policy(spoof)
        self.assertIn("SEARCH_POLICY_REQUIRED_SCOPES_NOT_GOVERNED",errors)
        self.assertIn("SEARCH_POLICY_HASH_NOT_GOVERNED",errors)
        result=identity_lookup(store=verified_store(),subject=pre_id_subject(),
                               request_id="REQ-SPOOF-SCOPE",search_policy=spoof,
                               normalizer=normalizer())
        self.assertEqual(result.outcome,LookupOutcome.INCOMPLETE_LOOKUP)
        self.assertIsNone(result.absent_claim_token)

    def test_NC17_same_id_version_with_changed_exclusions_fails(self):
        spoof=ungoverned_policy(
            policy_id="tracker.identity.search",version="1",
            searched=tuple(s for s in MANDATORY_DUPLICATE_CONTROL_SCOPES if s!="dormant"),
            exclusions={"dormant":"NOT_RELEVANT"})
        self.assertEqual(spoof.completeness_errors(),())
        errors=resolve_governed_search_policy(spoof)
        self.assertIn("SEARCH_POLICY_EXCLUSION_NOT_PERMITTED:dormant",errors)
        result=identity_lookup(store=verified_store(),subject=pre_id_subject(),
                               request_id="REQ-SPOOF-EXC",search_policy=spoof,
                               normalizer=normalizer())
        self.assertEqual(result.outcome,LookupOutcome.INCOMPLETE_LOOKUP)
        self.assertIsNone(result.absent_claim_token)

    def test_NC18_wrong_governed_policy_hash_fails(self):
        spoof=ungoverned_policy(policy_id="tracker.identity.search",version="1",
                                policy_hash="0"*64)
        result=identity_lookup(store=verified_store(),subject=pre_id_subject(),
                               request_id="REQ-BADHASH",search_policy=spoof,
                               normalizer=normalizer())
        self.assertEqual(result.outcome,LookupOutcome.INCOMPLETE_LOOKUP)
        self.assertIsNone(result.absent_claim_token)
        self.assertTrue(any("SEARCH_POLICY_HASH" in e for e in result.errors),result.errors)

    def test_NC19_governed_v1_retains_legitimate_exact_match(self):
        key=gate_key()
        store=verified_store([keyed_row(key)])
        result=identity_lookup(store=store,subject=pre_id_subject(),request_id="REQ-EXACT-GOV",
                               search_policy=governed_search_policy(),normalizer=normalizer())
        self.assertEqual(result.outcome,LookupOutcome.EXACT_CANONICAL_IDENTITY)
        self.assertTrue(result.lookup_complete)
        self.assertIsNotNone(result.exact_match)

    def test_NC20_governed_v1_retains_legitimate_near_match_review(self):
        # Same definition semantics, different governed dimension -> review.
        related=keyed_row(gate_key(price_basis="ASK"),feature_id="gold.logret.ask")
        store=verified_store([related])
        result=identity_lookup(store=store,subject=pre_id_subject(),request_id="REQ-NEAR-GOV",
                               search_policy=governed_search_policy(),normalizer=normalizer())
        self.assertEqual(result.outcome,LookupOutcome.NEAR_MATCH)
        self.assertEqual(result.pending_collision_result,
                         "RELATED_VERSION_CONTENT_REVIEW_REQUIRED")
        self.assertIsNone(result.absent_claim_token)

    # ---- preserved boundaries ---------------------------------------------

    def test_NC21_concurrent_identical_pre_id_requests_yield_one_active_claim(self):
        store=verified_store()
        first=identity_lookup(store=store,subject=pre_id_subject(),request_id="REQ-C1",
                              search_policy=governed_search_policy(),normalizer=normalizer())
        second=identity_lookup(store=store,subject=pre_id_subject(),request_id="REQ-C2",
                               search_policy=governed_search_policy(),normalizer=normalizer())
        self.assertEqual(first.outcome,LookupOutcome.ABSENT_EXACT_STRUCTURAL_IN_ERA_1)
        self.assertEqual(second.outcome,LookupOutcome.INCOMPLETE_LOOKUP)
        self.assertIsNone(second.absent_claim_token)
        self.assertEqual(len([c for c in store.claims if c.state=="ACTIVE"]),1)

    def test_NC22_expired_worker_aba_remains_blocked(self):
        store=CanonicalIdentityStore()
        clock=_Clock(datetime.now(timezone.utc)); store._clock=clock
        key=gate_key()
        store.reserve_claim(content_key_composite=key.composite,request_id="REQ-A")
        clock.advance(10_000)                       # A's claim expires
        store.reserve_claim(content_key_composite=key.composite,request_id="REQ-B")
        b=gate_intake(store,gate_candidate("gold.logret.b",claim_request_id="REQ-B"))
        self.assertTrue(b.accepted,b.errors)
        a=gate_intake(store,gate_candidate("gold.logret.a",claim_request_id="REQ-A"))
        self.assertFalse(a.accepted)
        self.assertEqual(len([r for r in store.all() if r.is_current]),1)

    def test_NC23_identity_appearing_after_claim_blocks_stale_registration(self):
        store=CanonicalIdentityStore()
        key=gate_key()
        store.reserve_claim(content_key_composite=key.composite,request_id="REQ-STALE")
        store.add(keyed_row(key))                   # arrives by the import path
        r=gate_intake(store,gate_candidate("gold.logret.stale",claim_request_id="REQ-STALE"))
        self.assertFalse(r.accepted)
        self.assertEqual(len([x for x in store.all() if x.is_current]),1)

    def test_NC24_canonical_survivor_handling_remains_fail_closed(self):
        orphan=record(version="1",current=False,lifecycle="SUPERSEDED",survivor="missing.feature")
        result=identity_lookup(store=CanonicalIdentityStore([orphan]),subject=subject(),
                               request_id="REQ-SURV",search_policy=complete_policy(),
                               normalizer=normalizer())
        self.assertEqual(result.outcome,LookupOutcome.INCOMPLETE_LOOKUP)
        self.assertIsNone(result.absent_claim_token)
        self.assertTrue(any("UNRESOLVED_CANONICAL_SURVIVOR" in e for e in result.errors),
                        result.errors)

    def test_NC25_unkeyed_searched_rows_still_block_pre_id_absence(self):
        bare=FeatureIdentity(
            feature_id="legacy.row",feature_version="1",
            definition_hash="d",graph_hash="g",lifecycle_state="CURRENT",
            is_current=True,scope="current_active",era_id="ERA_1")
        store=verified_store([bare])
        result=identity_lookup(store=store,subject=pre_id_subject(),request_id="REQ-UNKEYED",
                               search_policy=governed_search_policy(),normalizer=normalizer())
        self.assertEqual(result.outcome,LookupOutcome.INCOMPLETE_LOOKUP)
        self.assertIsNone(result.absent_claim_token)
        self.assertTrue(any("CONTENT_KEY_UNRESOLVED_ROWS" in e for e in result.errors),
                        result.errors)

    def test_NC26_validation_scope_protections_remain_intact(self):
        v=keyed_row(gate_key(),feature_id="gold.logret.validation",scope="validation")
        store=verified_store([v])
        hidden=identity_lookup(store=store,subject=pre_id_subject(),request_id="REQ-VAL-OUT",
                               search_policy=governed_search_policy(),normalizer=normalizer())
        self.assertEqual(hidden.outcome,LookupOutcome.ABSENT_EXACT_STRUCTURAL_IN_ERA_1)
        shown=identity_lookup(store=verified_store([v]),
                              subject=pre_id_subject(include_validation_scope=True),
                              request_id="REQ-VAL-IN",
                              search_policy=governed_search_policy(),normalizer=normalizer())
        self.assertEqual(shown.outcome,LookupOutcome.EXACT_CANONICAL_IDENTITY)

    def test_NC27_typed_content_key_encoding_protections_remain_intact(self):
        as_int=gate_key(parameters={"lookback_bars":2})
        as_str=gate_key(parameters={"lookback_bars":"2"})
        self.assertNotEqual(as_int.composite,as_str.composite)

class GovernedPolicyRegistryIntegrity(unittest.TestCase):

    def test_registry_entry_is_self_validating(self):
        from tracker_identity.policy_registry import (
            GOVERNED_SEARCH_POLICIES, GovernedSearchPolicyEntry,
        )
        for entry in GOVERNED_SEARCH_POLICIES.values():
            self.assertEqual(entry.registry_errors(),())
        # A governed entry that drops a mandatory scope is itself refused, so a
        # future version cannot quietly narrow duplicate control.
        bad=GovernedSearchPolicyEntry(
            policy_id="tracker.identity.search",version="99",
            required_scopes=("current_active",),searched_scopes=("current_active",))
        self.assertTrue(any("MISSING_MANDATORY" in x for x in bad.registry_errors()),
                        bad.registry_errors())
        # Nor may a governed entry declare a mandatory scope excludable.
        excludable=GovernedSearchPolicyEntry(
            policy_id="tracker.identity.search",version="98",
            required_scopes=MANDATORY_DUPLICATE_CONTROL_SCOPES,
            searched_scopes=MANDATORY_DUPLICATE_CONTROL_SCOPES,
            permitted_exclusions={"current_active":("ANY_REASON",)})
        self.assertTrue(any("MANDATORY_SCOPE_EXCLUDABLE" in x
                            for x in excludable.registry_errors()),
                        excludable.registry_errors())

    def test_governed_entry_is_not_mutable_in_place(self):
        """Second-pass A13: a live entry must not be editable at runtime."""
        from tracker_identity.policy_registry import GOVERNED_SEARCH_POLICIES
        entry=GOVERNED_SEARCH_POLICIES[("tracker.identity.search","1")]
        with self.assertRaises(TypeError):
            entry.permitted_exclusions["current_active"]=("ANY",)
        self.assertIsInstance(entry.required_scopes,tuple)
        self.assertIsInstance(entry.searched_scopes,tuple)

    def test_mandatory_scope_checks_survive_a_rogue_entry(self):
        """Second-pass A13b: defence in depth.

        The mandatory-scope checks are evaluated independently of the registry
        entry, so a wrong entry still cannot authorise excluding current_active.
        """
        from tracker_identity.policy_registry import GovernedSearchPolicyEntry
        rogue=GovernedSearchPolicyEntry(
            policy_id="tracker.identity.search",version="1",
            required_scopes=MANDATORY_DUPLICATE_CONTROL_SCOPES,
            searched_scopes=tuple(s for s in MANDATORY_DUPLICATE_CONTROL_SCOPES
                                  if s!="current_active"),
            permitted_exclusions={"current_active":("ANY",)})
        self.assertTrue(any("MANDATORY_SCOPE_EXCLUDABLE" in x
                            for x in rogue.registry_errors()),rogue.registry_errors())
        presented=ungoverned_policy(
            policy_id="tracker.identity.search",version="1",
            searched=rogue.searched_scopes,exclusions={"current_active":"ANY"})
        errors=resolve_governed_search_policy(presented)
        self.assertIn("MANDATORY_SCOPE_EXCLUDED:current_active",errors)
        self.assertIn("MANDATORY_SCOPE_NOT_SEARCHED:current_active",errors)

    def test_governed_hash_is_derived_not_accepted(self):
        governed=governed_search_policy()
        self.assertEqual(governed.policy_hash,governed.computed_hash())
        self.assertEqual(resolve_governed_search_policy(governed),())

    def test_unknown_version_is_not_governed(self):
        unknown=ungoverned_policy(policy_id="tracker.identity.search",version="2")
        self.assertIn("SEARCH_POLICY_NOT_GOVERNED:tracker.identity.search@2",
                      resolve_governed_search_policy(unknown))

    def test_missing_policy_is_not_governed(self):
        self.assertEqual(resolve_governed_search_policy(None),("SEARCH_POLICY_REQUIRED",))

if __name__=="__main__":
    unittest.main()
