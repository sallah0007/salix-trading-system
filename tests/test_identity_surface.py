import unittest
from datetime import datetime, timedelta, timezone

from tracker_identity import (
    CanonicalIdentityStore, FeatureIdentity, LookupOutcome,
    NormalizerSpec, SearchPolicy, identity_lookup, stale_state_sweep,
)
from tracker_identity import (
    MANDATORY_DUPLICATE_CONTROL_SCOPES,
    BuiltIdentityCandidate, CanonicalEraBoundary, ClaimRecord,
    FeatureDefinitionRecord,
    build_content_identity_key, composer_boundary_outcome,
    governed_normalizer, governed_search_policy,
    resolve_governed_normalizer, resolve_governed_normalizer_binding,
    resolve_governed_search_policy,
    safe_intake_built_identity,
)

import importlib as _importlib
from unittest import mock as _fixture_mock
_store_module=_importlib.import_module("tracker_identity.store")

def seed_fixture(store,rows,replace_all=False):
    """TEST / FIXTURE ONLY (A14). Canonical records have no public writer;
    this enables the fixture seeder by code replacement for one call."""
    with _fixture_mock.patch.object(_store_module,"_fixture_seeding_permitted",
                                    return_value=True):
        _store_module._fixture_write_records(store,list(rows),replace_all=replace_all)
    return store

def fixture_store(rows=(),**kw):
    return seed_fixture(CanonicalIdentityStore(**kw),rows)



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
        result=identity_lookup(store=fixture_store([legacy]),subject=subject(),request_id="REQ-ERA1-ONLY",search_policy=complete_policy(),normalizer=normalizer())
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
            store=fixture_store([record()]),subject=subject(),request_id="REQ-EXACT",
            search_policy=complete_policy(),normalizer=normalizer(),
        )
        self.assertTrue(result.lookup_complete)
        self.assertEqual(result.outcome,LookupOutcome.EXACT_CANONICAL_IDENTITY)

    def test_near_match_requires_review(self):
        result=identity_lookup(
            store=fixture_store([record(version="2")]),subject=subject(version="1"),
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
            store=fixture_store([hidden]),subject=subject(),request_id="REQ-D1",
            search_policy=complete_policy(),normalizer=normalizer(),
        )
        self.assertFalse(result.lookup_complete)
        self.assertEqual(result.outcome,LookupOutcome.INCOMPLETE_LOOKUP)
        self.assertTrue(any("UNENUMERATED_STORE_SCOPE:X" in e for e in result.errors))
        self.assertIsNone(result.absent_claim_token)

    def test_d2_superseded_exact_does_not_resolve_exact(self):
        stale=record(current=False,lifecycle="SUPERSEDED")
        result=identity_lookup(
            store=fixture_store([stale]),subject=subject(),request_id="REQ-D2",
            search_policy=complete_policy(),normalizer=normalizer(),
        )
        self.assertTrue(result.lookup_complete)
        self.assertEqual(result.outcome,LookupOutcome.NEAR_MATCH)
        self.assertIsNone(result.exact_match)

    def test_d2_current_and_superseded_same_key_is_not_false_ambiguity(self):
        current=record(current=True,lifecycle="CURRENT")
        stale=record(current=False,lifecycle="SUPERSEDED")
        result=identity_lookup(
            store=fixture_store([current,stale]),subject=subject(),request_id="REQ-D2B",
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
            store=fixture_store([stale,survivor]),subject=subject(),request_id="REQ-SURVIVOR",
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
            store=fixture_store([record(instrument="XAUUSD")]),
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
            store=fixture_store([validation]),subject=subject(),request_id="REQ-VALID-HIDDEN",
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
            store=fixture_store([validation]),subject=s,request_id="REQ-VALID-EXPLICIT",
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
        store=fixture_store([v1,v2])
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
            store=fixture_store([bad]),search_policy=complete_policy(),normalizer=normalizer(),
        )
        self.assertFalse(sweep.clean)
        self.assertTrue(any("VALIDATION_SCOPE_NONCURRENT_LIFECYCLE" in d for d in sweep.defects))

    def test_validation_scope_noncurrent_identity_fails_sweep(self):
        bad=FeatureIdentity(
            feature_id="validation.bad",feature_version="1",definition_hash="1",graph_hash="1",
            lifecycle_state="CURRENT",is_current=False,scope="validation",era_id="ERA_1",
        )
        sweep=stale_state_sweep(
            store=fixture_store([bad]),search_policy=complete_policy(),normalizer=normalizer(),
        )
        self.assertFalse(sweep.clean)
        self.assertTrue(any("VALIDATION_SCOPE_NONCURRENT_IDENTITY" in d for d in sweep.defects))

    def test_stale_superseded_current_fails_sweep(self):
        sweep=stale_state_sweep(
            store=fixture_store([record(current=True,lifecycle="SUPERSEDED")]),
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
            store=fixture_store([bad]),search_policy=complete_policy(),normalizer=normalizer(),
        )
        self.assertFalse(sweep.clean)

    def test_test_fixture_in_live_scope_fails_sweep(self):
        fixture=FeatureIdentity(
            feature_id="fixture.test.feature",feature_version="1",definition_hash="1",graph_hash="1",
            lifecycle_state="CURRENT",is_current=True,scope="current_active",
        )
        sweep=stale_state_sweep(
            store=fixture_store([fixture]),search_policy=complete_policy(),normalizer=normalizer(),
        )
        self.assertFalse(sweep.clean)

    def test_alias_collision_fails_sweep(self):
        a=FeatureIdentity("feature.a","1","1","1","CURRENT",True,"current_active",aliases=("shared.alias",))
        b=FeatureIdentity("feature.b","1","2","2","CURRENT",True,"current_active",aliases=("shared.alias",))
        sweep=stale_state_sweep(
            store=fixture_store([a,b]),search_policy=complete_policy(),normalizer=normalizer(),
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
    "instrument_applicability":"INSTRUMENT_SPECIFIC",
}

class _Clock:
    def __init__(self,at): self.at=at
    def __call__(self): return self.at
    def advance(self,seconds): self.at=self.at+timedelta(seconds=seconds)

def install_test_clock(testcase,clock):
    """TEST-ONLY time control by code replacement: patches the store module's
    internal wall-clock source for one test. Production has no clock surface."""
    from unittest import mock
    from tracker_identity import store as store_module
    patcher=mock.patch.object(store_module,"_wall_now",clock)
    patcher.start()
    testcase.addCleanup(patcher.stop)

def patch_store_source(testcase,name,value):
    """TEST-ONLY: replace one store-owned source function for this test."""
    from unittest import mock
    from tracker_identity import store as store_module
    patcher=mock.patch.object(store_module,name,value)
    patcher.start()
    testcase.addCleanup(patcher.stop)
    return patcher

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
        instrument_applicability="INSTRUMENT_SPECIFIC",
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
    store=fixture_store(list(records))
    for sc in MANDATORY_DUPLICATE_CONTROL_SCOPES:
        store.declare_scope(sc,"EMPTY_VERIFIED")
    return store

def governed_claim(store,request_id,content_overrides=None):
    """Obtain a claim the ONLY legitimate way: a completed governed lookup.

    reserve_claim() no longer mints registration authority on demand, so a test
    that needs a real claim must go through identity_lookup exactly as a real
    caller does. Returns the lookup result.
    """
    for sc in MANDATORY_DUPLICATE_CONTROL_SCOPES:
        store.declare_scope(sc,"EMPTY_VERIFIED")
    content=dict(GATE_CONTENT)
    if content_overrides: content.update(content_overrides)
    result=identity_lookup(store=store,subject=pre_id_subject(content=content),
                           request_id=request_id,
                           search_policy=governed_search_policy(),normalizer=normalizer())
    assert result.absent_claim_token is not None,result.errors
    return result

def governed_lookup_raw(store,request_id,content_overrides=None):
    """Like governed_claim, but returns the result even when no claim issues."""
    for sc in MANDATORY_DUPLICATE_CONTROL_SCOPES:
        store.declare_scope(sc,"EMPTY_VERIFIED")
    content=dict(GATE_CONTENT)
    if content_overrides: content.update(content_overrides)
    return identity_lookup(store=store,subject=pre_id_subject(content=content),
                           request_id=request_id,
                           search_policy=governed_search_policy(),normalizer=normalizer())

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
        clock=_Clock(datetime.now(timezone.utc)); install_test_clock(self,clock)
        governed_claim(store,"REQ-EXP")
        clock.advance(10_000)
        r=gate_intake(store,gate_candidate(claim_request_id="REQ-EXP"))
        self.assertFalse(r.accepted)
        self.assertTrue(any("CLAIM_NOT_ACTIVE" in e for e in r.errors),r.errors)
        self.assertEqual(store.all(),())

    def test_NC06_released_claim_fails(self):
        store=CanonicalIdentityStore()
        result=governed_claim(store,"REQ-REL")
        self.assertTrue(store.release_claim(
            claim_id=result.absent_claim_token.claim_id,reason="ABANDONED"))
        r=gate_intake(store,gate_candidate(claim_request_id="REQ-REL"))
        self.assertFalse(r.accepted)
        self.assertTrue(any("CLAIM_NOT_ACTIVE" in e for e in r.errors),r.errors)
        self.assertEqual(store.all(),())

    def test_NC07_claim_bound_to_a_different_request_fails(self):
        store=CanonicalIdentityStore()
        governed_claim(store,"REQ-OWNER")
        r=gate_intake(store,gate_candidate(claim_request_id="REQ-IMPOSTOR"))
        self.assertFalse(r.accepted)
        self.assertTrue(any("CLAIM_NOT_FOUND" in e for e in r.errors),r.errors)
        self.assertEqual(store.all(),())
        self.assertEqual(store.claims[0].state,"ACTIVE")

    def test_NC08_claim_bound_to_a_different_content_key_fails(self):
        store=CanonicalIdentityStore()
        # Claim issued for ASK content; candidate declares BID content.
        governed_claim(store,"REQ-ASK",{"price_basis":"ASK"})
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
        """A's expired claim must die on EXPIRY, not merely on the terminal
        authority gate. B reaches the authority gate; A does not get that far."""
        store=CanonicalIdentityStore()
        clock=_Clock(datetime.now(timezone.utc)); install_test_clock(self,clock)
        governed_claim(store,"REQ-A")
        clock.advance(10_000)                       # A's claim expires
        governed_claim(store,"REQ-B")
        b=gate_intake(store,gate_candidate("gold.logret.b",claim_request_id="REQ-B"))
        a=gate_intake(store,gate_candidate("gold.logret.a",claim_request_id="REQ-A"))
        self.assertFalse(b.accepted)
        self.assertFalse(a.accepted)
        self.assertTrue(any("CLAIM_NOT_CONSTRUCTION_AUTHORIZED" in e for e in b.errors),b.errors)
        self.assertTrue(any("CLAIM_NOT_ACTIVE" in e for e in a.errors),a.errors)
        self.assertEqual(store.all(),())

    def test_NC23_identity_appearing_after_claim_blocks_stale_registration(self):
        """The duplicate check must fire BEFORE the terminal authority gate,
        so it stays independently observable."""
        store=CanonicalIdentityStore()
        key=gate_key()
        governed_claim(store,"REQ-STALE")
        seed_fixture(store,[keyed_row(key)])   # stands in for a governed import (fixture seeder)
        r=gate_intake(store,gate_candidate("gold.logret.stale",claim_request_id="REQ-STALE"))
        self.assertFalse(r.accepted)
        self.assertTrue(any("IDENTITY_APPEARED_SINCE_CLAIM" in e for e in r.errors),r.errors)
        self.assertEqual(len([x for x in store.all() if x.is_current]),1)

    def test_NC24_canonical_survivor_handling_remains_fail_closed(self):
        orphan=record(version="1",current=False,lifecycle="SUPERSEDED",survivor="missing.feature")
        result=identity_lookup(store=fixture_store([orphan]),subject=subject(),
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

class ManagerReAttackC1R(unittest.TestCase):
    """C-1R / DC-AUTHORITY-ISSUANCE: authority is ISSUED by its owner.

    REVIEW_CODER demonstrated that a caller could hand-build a ClaimProvenance,
    copy the PUBLIC governed policy binding, invent normalizer values, have
    reserve_claim accept it, then self-bind fabricated evidence strings and end
    up with a claim that looked fully provenance-bound. The flow is now
    inverted: the store establishes every fact itself and constructs the
    provenance, and no public entry point accepts one.
    """

    def test_P1_caller_cannot_reserve_with_hand_built_provenance(self):
        """reserve_claim no longer has a provenance parameter at all."""
        import inspect
        params=inspect.signature(CanonicalIdentityStore.reserve_claim).parameters
        self.assertNotIn("provenance",params)
        store=CanonicalIdentityStore()
        with self.assertRaises(TypeError):
            store.reserve_claim(content_key_composite=gate_key().composite,
                                request_id="REQ-P1",provenance=object())

    def test_P2_copying_the_public_policy_binding_confers_nothing(self):
        """The governed binding is public. Presenting it is not authority."""
        gov=governed_search_policy()
        self.assertEqual(resolve_governed_search_policy(gov),())
        store=CanonicalIdentityStore()          # scopes NOT proven reachable
        rec,err=store.reserve_claim(content_key_composite=gate_key().composite,
                                    request_id="REQ-P2",search_policy=gov,
                                    normalizer=governed_normalizer())
        self.assertIsNone(rec)
        self.assertTrue(err.startswith("CLAIM_SCOPE_NOT_PROVEN_REACHABLE"),err)
        self.assertEqual(store.claims,[])

    def test_P3_P4_caller_cannot_supply_result_id_or_evidence_hash(self):
        """Both identifiers are store-generated; no entry point accepts them."""
        import inspect
        params=inspect.signature(CanonicalIdentityStore.reserve_claim).parameters
        for forbidden in ("lookup_result_id","issuance_evidence_hash",
                          "lookup_evidence_hash","lookup_complete","lookup_outcome",
                          "semantic_uniqueness","authorizes_construction"):
            self.assertNotIn(forbidden,params,forbidden)
        store=CanonicalIdentityStore()
        result=governed_claim(store,"REQ-P34")
        prov=store.claims[0].provenance
        self.assertTrue(prov.store_issued)
        self.assertEqual(prov.lookup_result_id,result.lookup_result_id)
        self.assertEqual(len(prov.issuance_evidence_hash),64)

    def test_P5_no_public_evidence_binder_exists(self):
        """bind_lookup_evidence was removed, not merely tightened."""
        self.assertFalse(hasattr(CanonicalIdentityStore,"bind_lookup_evidence"))
        import inspect
        from tracker_identity import store as store_module
        self.assertNotIn("def bind_lookup_evidence",inspect.getsource(store_module))

    def test_P6_P7_real_governed_lookup_issues_a_genuine_claim(self):
        store=CanonicalIdentityStore()
        result=governed_claim(store,"REQ-P6")
        self.assertEqual(result.outcome,LookupOutcome.ABSENT_EXACT_STRUCTURAL_IN_ERA_1)
        claim=store.claims[0]
        self.assertEqual(store.claim_authenticity(claim),(True,None))
        prov=claim.provenance
        self.assertIsNotNone(prov)
        self.assertTrue(prov.lookup_complete)
        self.assertEqual(prov.completeness_errors(),())
        self.assertFalse(prov.authorizes_construction)
        self.assertFalse(result.absent_claim_token.authorizes_construction)
        self.assertEqual(prov.semantic_uniqueness,"UNRESOLVED_NOT_CERTIFIED")

    def test_P8_genuine_claim_fails_registration_at_authority_gate(self):
        store=CanonicalIdentityStore()
        governed_claim(store,"REQ-P8")
        r=gate_intake(store,gate_candidate(claim_request_id="REQ-P8"))
        self.assertFalse(r.accepted)
        self.assertTrue(any("CLAIM_NOT_CONSTRUCTION_AUTHORIZED" in e for e in r.errors),
                        r.errors)
        self.assertEqual(store.all(),())

    def test_P9_lookalike_claim_cannot_become_equivalent_to_a_genuine_one(self):
        """A structurally perfect forgery, injected by the most direct public
        route available, is still refused: it is not in the issuance ledger."""
        from tracker_identity import ClaimProvenance
        gov=governed_search_policy(); n=governed_normalizer()
        genuine_store=CanonicalIdentityStore()
        governed_claim(genuine_store,"REQ-GEN")
        genuine=genuine_store.claims[0]

        forged_prov=ClaimProvenance(
            request_id="REQ-FAKE",content_key_composite=gate_key().composite,
            lookup_outcome=genuine.provenance.lookup_outcome,lookup_complete=True,
            search_policy_id=gov.policy_id,search_policy_version=gov.version,
            search_policy_hash=gov.policy_hash,
            normalizer_id=n.normalizer_id,normalizer_version=n.version,
            normalizer_hash=n.normalizer_hash,
            semantic_uniqueness="UNRESOLVED_NOT_CERTIFIED",
            authorizes_construction=False,
            lookup_result_id="FABRICATED-RESULT",
            issuance_evidence_hash="FABRICATED-HASH")
        self.assertEqual(forged_prov.completeness_errors(),())
        fake=ClaimRecord("claim-FAKE",gate_key().composite,"REQ-FAKE","TRACKER",
                         genuine.issued_ts,genuine.expires_ts,"ACTIVE",None,forged_prov)
        store=CanonicalIdentityStore()
        store.claims.append(fake)
        ok,error=store.commit_registration(
            identity=keyed_row(gate_key()),creation=object(),
            content_key_composite=gate_key().composite,request_id="REQ-FAKE")
        self.assertFalse(ok)
        self.assertEqual(error,"CLAIM_NOT_ISSUED_BY_THIS_STORE")
        self.assertEqual(store.all(),())

    def test_R1_direct_reserve_without_governed_inputs_fails(self):
        store=CanonicalIdentityStore()
        rec,err=store.reserve_claim(content_key_composite=gate_key().composite,
                                    request_id="REQ-DIRECT")
        self.assertIsNone(rec)
        self.assertTrue(err.startswith("CLAIM_SEARCH_POLICY_NOT_GOVERNED"),err)
        r=gate_intake(store,gate_candidate(claim_request_id="REQ-DIRECT"))
        self.assertFalse(r.accepted)
        self.assertEqual(store.all(),())
        self.assertEqual(store.claims,[])

    def test_R2_direct_reserve_then_direct_commit_fails(self):
        store=CanonicalIdentityStore()
        store.reserve_claim(content_key_composite=gate_key().composite,
                            request_id="REQ-D2")
        ok,error=store.commit_registration(
            identity=keyed_row(gate_key()),creation=object(),
            content_key_composite=gate_key().composite,request_id="REQ-D2")
        self.assertFalse(ok)
        self.assertEqual(error,"CLAIM_NOT_FOUND")
        self.assertEqual(store.all(),())

    def test_R3_claim_from_incomplete_lookup_is_never_issued(self):
        store=verified_store()
        result=identity_lookup(store=store,subject=pre_id_subject(),
                               request_id="REQ-INC",
                               search_policy=ungoverned_policy(),normalizer=normalizer())
        self.assertEqual(result.outcome,LookupOutcome.INCOMPLETE_LOOKUP)
        self.assertIsNone(result.absent_claim_token)
        self.assertEqual(store.claims,[])
        r=gate_intake(store,gate_candidate(claim_request_id="REQ-INC"))
        self.assertFalse(r.accepted)
        self.assertEqual(store.all(),())

    def test_R4_store_rederives_absence_rather_than_accepting_it(self):
        """The store refuses to issue when its OWN records contradict absence."""
        store=verified_store([keyed_row(gate_key())])
        rec,err=store.reserve_claim(content_key_composite=gate_key().composite,
                                    request_id="REQ-R4",
                                    search_policy=governed_search_policy(),
                                    normalizer=governed_normalizer())
        self.assertIsNone(rec)
        self.assertTrue(err.startswith("CLAIM_CONTENT_IDENTITY_ALREADY_PRESENT"),err)
        self.assertEqual(store.claims,[])

    def test_N1_fake_normalizer_binding_fails(self):
        fake=NormalizerSpec("totally.made.up","99","deadbeef",
                            ("EXACT_STRUCTURAL_IDENTITY",))
        self.assertTrue(any("NORMALIZER_NOT_GOVERNED" in e
                            for e in resolve_governed_normalizer(fake)))
        result=identity_lookup(store=verified_store(),subject=pre_id_subject(),
                               request_id="REQ-N1",
                               search_policy=governed_search_policy(),normalizer=fake)
        self.assertEqual(result.outcome,LookupOutcome.INCOMPLETE_LOOKUP)
        self.assertIsNone(result.absent_claim_token)

    def test_N2_self_consistent_but_ungoverned_normalizer_fails(self):
        p=NormalizerSpec("attacker.normalizer","1","",("EXACT_STRUCTURAL_IDENTITY",))
        spoof=NormalizerSpec(p.normalizer_id,p.version,p.computed_hash(),
                             p.equivalence_classes)
        self.assertEqual(spoof.completeness_errors(),())
        self.assertIn("NORMALIZER_NOT_GOVERNED:attacker.normalizer@1",
                      resolve_governed_normalizer(spoof))
        store=verified_store()
        result=identity_lookup(store=store,subject=pre_id_subject(),request_id="REQ-N2",
                               search_policy=governed_search_policy(),normalizer=spoof)
        self.assertEqual(result.outcome,LookupOutcome.INCOMPLETE_LOOKUP)
        self.assertEqual(store.claims,[])

    def test_N2b_ungoverned_normalizer_is_refused_at_the_LOOKUP_layer(self):
        """Pins WHICH layer refuses it.

        The store also re-resolves the normalizer, so removing the lookup-layer
        check alone still produced INCOMPLETE_LOOKUP via the issuance refusal —
        the two guards masked each other under mutation. Asserting the specific
        lookup-layer error code distinguishes them.
        """
        p=NormalizerSpec("attacker.normalizer","1","",("EXACT_STRUCTURAL_IDENTITY",))
        spoof=NormalizerSpec(p.normalizer_id,p.version,p.computed_hash(),
                             p.equivalence_classes)
        result=identity_lookup(store=verified_store(),subject=pre_id_subject(),
                               request_id="REQ-N2B",
                               search_policy=governed_search_policy(),normalizer=spoof)
        self.assertTrue(any(e.startswith("NORMALIZER_NOT_GOVERNED") for e in result.errors),
                        result.errors)

    def test_N2c_ungoverned_normalizer_is_refused_at_the_ISSUANCE_layer(self):
        """The store re-resolves independently of whatever the lookup decided."""
        p=NormalizerSpec("attacker.normalizer","1","",("EXACT_STRUCTURAL_IDENTITY",))
        spoof=NormalizerSpec(p.normalizer_id,p.version,p.computed_hash(),
                             p.equivalence_classes)
        store=verified_store()
        rec,err=store.reserve_claim(content_key_composite=gate_key().composite,
                                    request_id="REQ-N2C",
                                    search_policy=governed_search_policy(),
                                    normalizer=spoof)
        self.assertIsNone(rec)
        self.assertTrue(err.startswith("CLAIM_NORMALIZER_NOT_GOVERNED"),err)
        self.assertEqual(store.claims,[])

    def test_N5_normalizer_entry_integrity_recheck_defeats_gc_route(self):
        """Same defence-in-depth proof as A6, for the normalizer registry."""
        import gc
        from tracker_identity import normalizer_registry as nr
        backing=[r for r in gc.get_referents(nr.GOVERNED_NORMALIZERS) if isinstance(r,dict)]
        if not backing:
            self.skipTest("no gc-reachable backing map on this interpreter")
        backing=backing[0]
        key=("tracker.identity.normalizer","1")
        saved=backing[key]
        rogue=nr.GovernedNormalizerEntry("tracker.identity.normalizer","1",
                                         ("ALGEBRAIC_EQUIVALENCE",))
        try:
            backing[key]=rogue
            self.assertIs(nr.GOVERNED_NORMALIZERS[key],rogue)
            widened=NormalizerSpec("tracker.identity.normalizer","1",
                                   rogue.normalizer_hash,("ALGEBRAIC_EQUIVALENCE",))
            errors=resolve_governed_normalizer(widened)
            self.assertTrue(any("ENTRY_INTEGRITY_FAILED" in e for e in errors),errors)
            self.assertTrue(any("ENTRY_INTEGRITY_FAILED" in e
                                for e in resolve_governed_normalizer_binding(
                                    "tracker.identity.normalizer","1",
                                    rogue.normalizer_hash)))
        finally:
            backing[key]=saved
        self.assertIs(nr.GOVERNED_NORMALIZERS[key],saved)

    def test_N3_governed_normalizer_binding_succeeds(self):
        gov=governed_normalizer()
        self.assertEqual(resolve_governed_normalizer(gov),())
        self.assertEqual(gov.normalizer_hash,gov.computed_hash())
        self.assertEqual(resolve_governed_normalizer_binding(
            gov.normalizer_id,gov.version,gov.normalizer_hash),())

    def test_N4_changed_equivalence_class_or_hash_fails(self):
        gov=governed_normalizer()
        widened=NormalizerSpec(gov.normalizer_id,gov.version,gov.normalizer_hash,
                               gov.equivalence_classes+("ALGEBRAIC_EQUIVALENCE",))
        self.assertTrue(any("EQUIVALENCE_CLASSES_NOT_GOVERNED" in e
                            for e in resolve_governed_normalizer(widened)),
                        resolve_governed_normalizer(widened))
        wrong_hash=NormalizerSpec(gov.normalizer_id,gov.version,"0"*64,
                                  gov.equivalence_classes)
        self.assertIn("NORMALIZER_HASH_NOT_GOVERNED",
                      resolve_governed_normalizer(wrong_hash))
        self.assertIn("NORMALIZER_HASH_NOT_GOVERNED",
                      resolve_governed_normalizer_binding(
                          gov.normalizer_id,gov.version,"0"*64))

    def test_R6_no_construction_authorized_path_exists_yet(self):
        """R6 = NOT YET AVAILABLE, asserted rather than assumed."""
        import inspect, pathlib
        import tracker_identity
        pkg=pathlib.Path(inspect.getfile(tracker_identity)).parent
        offenders=[]
        for path in sorted(pkg.glob("*.py")):
            src=path.read_text(encoding="utf-8")
            for lineno,line in enumerate(src.splitlines(),1):
                stripped=line.strip()
                if stripped.startswith("#"):
                    continue
                if "authorizes_construction=True" in stripped.replace(" ",""):
                    offenders.append(path.name+":"+str(lineno))
        self.assertEqual(offenders,[],
            "a construction-authorized path now exists: "+str(offenders))
        from tracker_identity import AbsentClaimToken, ClaimProvenance
        self.assertFalse(AbsentClaimToken("c","o","r").authorizes_construction)
        self.assertFalse(ClaimProvenance(
            "r","k","o",True,"a","b","c","d","e","f","g").authorizes_construction)

class IssuanceAuthenticityCR1CR2(unittest.TestCase):
    """DC-ISSUANCE-AUTHENTICITY-BINDING-003 — mandatory controls 1-14.

    CR-1: issuance was proved by membership in `store._issued_claim_ids`, an
    ordinary set — adding a fabricated id made a synthetic claim "issued".
    CR-2: a genuinely issued claim could have its provenance replaced in the
    public `claims` list; its id stayed "issued" while authorizes_construction
    became caller-selected. Both reproduced as full canonical row writes.

    Authenticity is now equality with an exact snapshot held by a closure-owned
    per-store ledger that no ordinary caller API or data container reaches.
    Closure reflection, gc and ctypes are out of boundary (declared residual).
    """

    def _genuine(self,store=None,request_id="REQ-GEN"):
        store=store or CanonicalIdentityStore()
        governed_claim(store,request_id)
        return store,store.claims[0]

    def _commit(self,store,request_id,key=None):
        key=key or gate_key()
        return store.commit_registration(
            identity=keyed_row(key),creation=object(),
            content_key_composite=key.composite,request_id=request_id)

    def _forged_provenance(self,request_id,authorizes=False):
        from tracker_identity import ClaimProvenance
        gov=governed_search_policy(); n=governed_normalizer()
        return ClaimProvenance(
            request_id=request_id,content_key_composite=gate_key().composite,
            lookup_outcome=LookupOutcome.ABSENT_EXACT_STRUCTURAL_IN_ERA_1.value,
            lookup_complete=True,search_policy_id=gov.policy_id,
            search_policy_version=gov.version,search_policy_hash=gov.policy_hash,
            normalizer_id=n.normalizer_id,normalizer_version=n.version,
            normalizer_hash=n.normalizer_hash,
            semantic_uniqueness="UNRESOLVED_NOT_CERTIFIED",
            authorizes_construction=authorizes,
            lookup_result_id="forged-result",issuance_evidence_hash="f"*64)

    # 1 -----------------------------------------------------------------
    def test_C01_synthetic_provenance_and_record_cannot_register(self):
        store=CanonicalIdentityStore()
        fake=ClaimRecord("claim-SYN",gate_key().composite,"REQ-SYN","TRACKER",
                         "2026-01-01T00:00:00+00:00","2099-01-01T00:00:00+00:00",
                         "ACTIVE",None,self._forged_provenance("REQ-SYN",True))
        store.claims.append(fake)
        ok,error=self._commit(store,"REQ-SYN")
        self.assertFalse(ok)
        self.assertEqual(error,"CLAIM_NOT_ISSUED_BY_THIS_STORE")
        self.assertEqual(store.all(),())

    # 2 -----------------------------------------------------------------
    def test_C02_synthetic_claim_plus_every_caller_mutable_container(self):
        """CR-1 exactly: plant the synthetic claim AND add its id to every
        set/dict/list reachable on the store. None of them is issuance proof."""
        store=CanonicalIdentityStore()
        fake=ClaimRecord("claim-SYN2",gate_key().composite,"REQ-S2","TRACKER",
                         "2026-01-01T00:00:00+00:00","2099-01-01T00:00:00+00:00",
                         "ACTIVE",None,self._forged_provenance("REQ-S2",True))
        store.claims.append(fake)
        for value in list(vars(store).values()):
            if isinstance(value,set):
                value.add("claim-SYN2")
            elif isinstance(value,dict):
                value["claim-SYN2"]="ISSUED"
        # The removed set must stay removed: its presence would be a regression.
        self.assertFalse(hasattr(store,"_issued_claim_ids"))
        ok,error=self._commit(store,"REQ-S2")
        self.assertFalse(ok)
        self.assertEqual(error,"CLAIM_NOT_ISSUED_BY_THIS_STORE")
        self.assertEqual(store.all(),())

    # 3 -----------------------------------------------------------------
    def test_C03_genuine_claim_with_provenance_replaced_cannot_register(self):
        """CR-2 exactly. The claim id stays genuinely issued; the authority
        bit is caller-selected. It must not register."""
        from dataclasses import replace
        store,genuine=self._genuine()
        tampered=replace(genuine,provenance=replace(
            genuine.provenance,authorizes_construction=True))
        store.claims[0]=tampered
        self.assertEqual(store.claim_authenticity(tampered),
                         (False,"CLAIM_CONTENT_ALTERED_SINCE_ISSUANCE"))
        ok,error=self._commit(store,"REQ-GEN")
        self.assertFalse(ok)
        self.assertEqual(error,"CLAIM_CONTENT_ALTERED_SINCE_ISSUANCE")
        self.assertEqual(store.all(),())

    # 4 -----------------------------------------------------------------
    def test_C04_every_bound_field_is_covered_by_authenticity(self):
        from dataclasses import replace
        other=gate_key(price_basis="ASK").composite
        record_edits={
            "request_id":{"request_id":"REQ-OTHER"},
            "content_key":{"content_key_composite":other},
            "issuer":{"issuer":"ATTACKER"},
            "issued_ts":{"issued_ts":"2000-01-01T00:00:00+00:00"},
            "expires_ts":{"expires_ts":"2999-01-01T00:00:00+00:00"},
            "lifecycle_state":{"state":"RELEASED"},
            "release_reason":{"release_reason":"FORGED"},
        }
        provenance_edits={
            "authority_bit":{"authorizes_construction":True},
            "policy_binding":{"search_policy_hash":"0"*64},
            "normalizer_binding":{"normalizer_hash":"0"*64},
            "lookup_result_id":{"lookup_result_id":"forged-result"},
            "evidence_binding":{"issuance_evidence_hash":"0"*64},
            "provenance_request_id":{"request_id":"REQ-OTHER"},
            "provenance_content_key":{"content_key_composite":other},
            "semantic_uniqueness":{"semantic_uniqueness":"CERTIFIED_UNIQUE"},
            "lookup_outcome":{"lookup_outcome":"EXACT_CANONICAL_IDENTITY"},
            "lookup_complete":{"lookup_complete":False},
        }
        for name,edit in record_edits.items():
            store,genuine=self._genuine()
            ok,_=store.claim_authenticity(replace(genuine,**edit))
            self.assertFalse(ok,name)
        for name,edit in provenance_edits.items():
            store,genuine=self._genuine()
            forged=replace(genuine,provenance=replace(genuine.provenance,**edit))
            ok,error=store.claim_authenticity(forged)
            self.assertFalse(ok,name)
            self.assertEqual(error,"CLAIM_CONTENT_ALTERED_SINCE_ISSUANCE",name)

    def test_C04b_frozen_record_mutated_in_place_is_detected(self):
        """object.__setattr__ bypasses a frozen dataclass. The ledger holds a
        serialized snapshot, not a shared object reference, so the in-place
        edit is still detected."""
        store,genuine=self._genuine()
        object.__setattr__(genuine.provenance,"authorizes_construction",True)
        self.assertEqual(store.claim_authenticity(genuine),
                         (False,"CLAIM_CONTENT_ALTERED_SINCE_ISSUANCE"))
        ok,error=self._commit(store,"REQ-GEN")
        self.assertFalse(ok)
        self.assertEqual(store.all(),())

    def test_C04c_subclassed_record_or_provenance_is_refused(self):
        from dataclasses import replace
        from tracker_identity import ClaimProvenance
        class LookalikeRecord(ClaimRecord):
            pass
        class LookalikeProvenance(ClaimProvenance):
            pass
        store,genuine=self._genuine()
        rec=LookalikeRecord(*[getattr(genuine,f) for f in genuine.__dataclass_fields__])
        self.assertEqual(store.claim_authenticity(rec),
                         (False,"CLAIM_RECORD_TYPE_NOT_AUTHENTIC"))
        prov=LookalikeProvenance(*[getattr(genuine.provenance,f)
                                   for f in genuine.provenance.__dataclass_fields__])
        self.assertEqual(store.claim_authenticity(replace(genuine,provenance=prov)),
                         (False,"CLAIM_PROVENANCE_TYPE_NOT_AUTHENTIC"))

    # 5 -----------------------------------------------------------------
    def test_C05_copies_gain_nothing_beyond_the_exact_issued_state(self):
        """An exact copy/deepcopy/reconstruction IS the issued state and is
        allowed by the design — and it gains no extra authority: it fails at
        the construction gate like the original, and it is single-use through
        the ledger, not through the object."""
        import copy
        store,genuine=self._genuine()
        for clone in (copy.copy(genuine),copy.deepcopy(genuine),
                      ClaimRecord(*[getattr(genuine,f)
                                    for f in genuine.__dataclass_fields__])):
            self.assertEqual(store.claim_authenticity(clone),(True,None))
            self.assertFalse(clone.provenance.authorizes_construction)
        store.claims.append(copy.deepcopy(genuine))
        ok,error=self._commit(store,"REQ-GEN")
        self.assertFalse(ok)
        self.assertEqual(error,"CLAIM_NOT_CONSTRUCTION_AUTHORIZED")
        self.assertEqual(store.all(),())

    # 6 -----------------------------------------------------------------
    def test_C06_store_A_claim_replay_into_store_B_fails(self):
        store_a,genuine=self._genuine()
        self.assertEqual(store_a.claim_authenticity(genuine),(True,None))
        store_b=CanonicalIdentityStore()
        self.assertEqual(store_b.claim_authenticity(genuine),
                         (False,"CLAIM_NOT_ISSUED_BY_THIS_STORE"))
        store_b.claims.append(genuine)
        ok,error=self._commit(store_b,"REQ-GEN")
        self.assertFalse(ok)
        self.assertEqual(error,"CLAIM_NOT_ISSUED_BY_THIS_STORE")
        self.assertEqual(store_b.all(),())

    def test_C06b_copying_or_replacing_the_store_does_not_transfer_authority(self):
        import copy
        from dataclasses import replace
        store_a,genuine=self._genuine()
        for clone in (copy.copy(store_a),replace(store_a)):
            self.assertIsNot(clone,store_a)
            self.assertEqual(clone.claim_authenticity(genuine),
                             (False,"CLAIM_NOT_ISSUED_BY_THIS_STORE"))

    # 7 -----------------------------------------------------------------
    def test_C07_expired_released_and_consumed_claims_stay_unusable(self):
        # expired
        store=CanonicalIdentityStore()
        clock=_Clock(datetime.now(timezone.utc)); install_test_clock(self,clock)
        governed_claim(store,"REQ-E")
        clock.advance(10_000)
        ok,error=self._commit(store,"REQ-E")
        self.assertFalse(ok)
        self.assertEqual(error,"CLAIM_NOT_ACTIVE:EXPIRED")
        # released
        store,genuine=self._genuine(request_id="REQ-R")
        self.assertTrue(store.release_claim(claim_id=genuine.claim_id,reason="DONE"))
        ok,error=self._commit(store,"REQ-R")
        self.assertFalse(ok)
        self.assertEqual(error,"CLAIM_NOT_ACTIVE:RELEASED")
        # mirror revived to ACTIVE by the caller: lifecycle tamper, still dead
        from dataclasses import replace
        store.claims[0]=replace(store.claims[0],state="ACTIVE",release_reason=None)
        ok,error=self._commit(store,"REQ-R")
        self.assertFalse(ok)
        self.assertEqual(error,"CLAIM_LIFECYCLE_ALTERED_SINCE_ISSUANCE")
        self.assertEqual(store.all(),())

    def test_C07b_release_cannot_be_revived_through_the_public_api(self):
        store,genuine=self._genuine(request_id="REQ-RV")
        self.assertTrue(store.release_claim(claim_id=genuine.claim_id,reason="DONE"))
        self.assertFalse(store.release_claim(claim_id=genuine.claim_id,reason="AGAIN"))
        self.assertIsNone(store.active_claim(gate_key().composite))

    def test_C07c_editing_expiry_cannot_extend_a_claim(self):
        from dataclasses import replace
        store=CanonicalIdentityStore()
        clock=_Clock(datetime.now(timezone.utc)); install_test_clock(self,clock)
        governed_claim(store,"REQ-X")
        store.claims[0]=replace(store.claims[0],expires_ts="2999-01-01T00:00:00+00:00")
        clock.advance(10_000)
        self.assertIsNone(store.active_claim(gate_key().composite))
        ok,error=self._commit(store,"REQ-X")
        self.assertFalse(ok)

    # 8 -----------------------------------------------------------------
    def test_C08_one_active_claim_per_content_key_survives_mirror_tampering(self):
        """Hiding a pending claim by flipping its MIRROR to RELEASED must not
        let a second active claim be issued on the same content key."""
        from dataclasses import replace
        store,genuine=self._genuine(request_id="REQ-1")
        store.claims[0]=replace(genuine,state="RELEASED",release_reason="HIDDEN")
        second=governed_lookup_raw(store,"REQ-2")
        self.assertIsNone(second.absent_claim_token)
        self.assertTrue(any("PENDING_CLAIM_EXISTS" in e for e in second.errors),
                        second.errors)

    def test_C08c_public_active_claim_reports_the_ledger_not_the_mirror(self):
        """Pins the reserve_claim pre-check layer on its own (mutant A8).

        Under mutation this layer and the writer's own ledger check masked each
        other, so each is asserted independently."""
        from dataclasses import replace
        store,genuine=self._genuine(request_id="REQ-A8")
        store.claims[0]=replace(genuine,state="RELEASED",release_reason="HIDE")
        self.assertIsNotNone(store.active_claim(gate_key().composite))

    def test_C08d_the_single_writer_enforces_one_active_claim_by_itself(self):
        """Pins the writer's own ledger check (mutant A11): called directly,
        bypassing reserve_claim's pre-check, it still refuses a second claim."""
        from dataclasses import replace
        from tracker_identity import store as store_module
        store,genuine=self._genuine(request_id="REQ-A11")
        store.claims[0]=replace(genuine,state="RELEASED",release_reason="HIDE")
        rec,error=store_module._issue_claim(
            store,content_key_composite=gate_key().composite,request_id="REQ-A11B",
            search_policy=governed_search_policy(),normalizer=governed_normalizer(),
            include_validation_scope=False,issuer="TRACKER")
        self.assertIsNone(rec)
        self.assertTrue(error.startswith("PENDING_CLAIM_EXISTS"),error)

    def test_C08b_same_claim_cannot_register_twice(self):
        """Registration never succeeds today, so double-registration is proven
        at the claim layer: a claim is consumed at most once, in the ledger,
        and no copy of it can be presented after that."""
        import copy
        store,genuine=self._genuine(request_id="REQ-TWICE")
        dup=copy.deepcopy(genuine)
        store.claims.append(dup)
        self.assertTrue(store.release_claim(claim_id=genuine.claim_id,reason="USED"))
        for c in list(store.claims):
            ok,_=store.claim_authenticity(c)
            if ok:
                self.assertNotEqual(c.state,"ACTIVE")
        ok,error=self._commit(store,"REQ-TWICE")
        self.assertFalse(ok)
        self.assertEqual(error,"CLAIM_NOT_ACTIVE:RELEASED")

    # 9 -----------------------------------------------------------------
    def test_C09_direct_commit_without_authentic_issued_claim_fails(self):
        store=CanonicalIdentityStore()
        ok,error=self._commit(store,"REQ-NONE")
        self.assertFalse(ok)
        self.assertEqual(error,"CLAIM_NOT_FOUND")
        ok,error=store.commit_registration(identity=keyed_row(gate_key()),
            creation=object(),content_key_composite=None,request_id=None)
        self.assertFalse(ok)
        self.assertEqual(error,"CLAIM_REQUIRED_FOR_REGISTRATION")
        self.assertEqual(store.all(),())

    def test_C09b_a_planted_lookalike_cannot_shadow_a_genuine_claim(self):
        """Scanning stops only at an AUTHENTIC match, so a record planted ahead
        of the genuine one neither authorises nor denies it."""
        store,genuine=self._genuine(request_id="REQ-SH")
        fake=ClaimRecord("claim-SHADOW",genuine.content_key_composite,"REQ-SH",
                         "TRACKER",genuine.issued_ts,genuine.expires_ts,"ACTIVE",None,
                         self._forged_provenance("REQ-SH",True))
        store.claims.insert(0,fake)
        claim,error=store.validate_claim_for_registration(
            content_key_composite=genuine.content_key_composite,request_id="REQ-SH")
        self.assertIsNotNone(claim,error)
        self.assertEqual(claim.claim_id,genuine.claim_id)
        ok,error=self._commit(store,"REQ-SH")
        self.assertFalse(ok)
        self.assertEqual(error,"CLAIM_NOT_CONSTRUCTION_AUTHORIZED")

    # 10 ----------------------------------------------------------------
    def test_C10_policy_and_normalizer_integrity_remain_pass(self):
        self.assertEqual(resolve_governed_search_policy(governed_search_policy()),())
        self.assertEqual(resolve_governed_normalizer(governed_normalizer()),())
        store,genuine=self._genuine(request_id="REQ-INT")
        self.assertEqual(genuine.provenance.completeness_errors(),())

    # 11 ----------------------------------------------------------------
    def test_C11_no_issuance_path_accepts_a_record_provenance_or_authority(self):
        """There is no sealer. The only writer takes raw lookup inputs."""
        import inspect
        from tracker_identity import store as store_module
        params=inspect.signature(CanonicalIdentityStore.reserve_claim).parameters
        for forbidden in ("provenance","record","claim","authorizes_construction",
                          "lookup_result_id","issuance_evidence_hash","claim_id",
                          "issued_ts","expires_ts","snapshot","tag"):
            self.assertNotIn(forbidden,params,forbidden)
        issue_params=inspect.signature(store_module._issue_claim).parameters
        for forbidden in ("provenance","record","claim","authorizes_construction",
                          "lookup_result_id","issuance_evidence_hash","claim_id"):
            self.assertNotIn(forbidden,issue_params,forbidden)
        # No module-level container holds issuance state.
        leaked=[n for n,v in vars(store_module).items()
                if isinstance(v,(dict,set,list)) and not n.startswith("__")]
        self.assertEqual(leaked,[],leaked)

    def test_C11b_invoking_the_issuer_directly_grants_no_authority(self):
        """Calling the single writer directly is a legitimate issuance: it
        re-derives every fact and cannot emit construction authority."""
        from tracker_identity import store as store_module
        store=verified_store()
        rec,error=store_module._issue_claim(
            store,content_key_composite=gate_key().composite,request_id="REQ-DIRECT",
            search_policy=governed_search_policy(),normalizer=governed_normalizer(),
            include_validation_scope=False,issuer="ATTACKER")
        self.assertIsNotNone(rec,error)
        self.assertFalse(rec.provenance.authorizes_construction)
        r=gate_intake(store,gate_candidate(claim_request_id="REQ-DIRECT"))
        self.assertFalse(r.accepted)
        self.assertTrue(any("CLAIM_NOT_CONSTRUCTION_AUTHORIZED" in e for e in r.errors),
                        r.errors)
        # And it refuses to issue where the store's own records contradict it.
        dup_store=verified_store([keyed_row(gate_key())])
        rec2,error2=store_module._issue_claim(
            dup_store,content_key_composite=gate_key().composite,request_id="REQ-D2",
            search_policy=governed_search_policy(),normalizer=governed_normalizer(),
            include_validation_scope=False,issuer="ATTACKER")
        self.assertIsNone(rec2)
        self.assertTrue(error2.startswith("CLAIM_CONTENT_IDENTITY_ALREADY_PRESENT"),error2)

    # 12 ----------------------------------------------------------------
    def test_C12_claimless_ordinary_writers_are_closed(self):
        """DC-006 inverted this pin: store.add()/extend() no longer exist and the
        records view is read-only (A14 ordinary claimless paths CLOSED)."""
        store=CanonicalIdentityStore()
        self.assertFalse(hasattr(store,"add"))
        self.assertFalse(hasattr(store,"extend"))
        with self.assertRaises(AttributeError):
            store.records.append(keyed_row(gate_key()))
        self.assertEqual(store.all(),())

class WeakrefAndStoreOwnedTime004(unittest.TestCase):
    """DC-004 controls, migrated in DC-005 to the test-only time mechanism.

    Every proposition is preserved. What changed is HOW tests steer time: the
    production `_clock` field is gone, so tests now replace the store module's
    internal clock/lifetime SOURCE functions with unittest.mock.
    """

    TIME_PARAM_NAMES=("now","now_iso","now_ts","at","when","timestamp",
                      "transaction_time","clock_time","as_of")

    def _genuine(self,request_id="REQ-W"):
        store=CanonicalIdentityStore()
        governed_claim(store,request_id)
        return store,store.claims[0]

    def _reserve(self,store,request_id="REQ-TTL"):
        return store.reserve_claim(
            content_key_composite=gate_key().composite,request_id=request_id,
            search_policy=governed_search_policy(),normalizer=governed_normalizer())

    # NC-W1 (private-registry view; the governed PUBLIC route is DC005 NC-1)
    def test_W01_finalize_registry_does_not_expose_the_ledger(self):
        import weakref
        store,_=self._genuine()
        mine=[f for f in list(weakref.finalize._registry)
              if f.peek() and f.peek()[0] is store]
        self.assertEqual(len(mine),1,"exactly one cleanup finalizer per store")
        _,func,args,kwargs=mine[0].peek()
        self.assertIsNone(getattr(func,"__self__",None))
        for value in (*args,*(kwargs or {}).values()):
            self.assertNotIsInstance(value,(dict,list,set),value)
        self.assertEqual(args,(id(store),))

    def test_W02_W03_W04_authenticity_protections_are_preserved(self):
        from dataclasses import replace
        store=CanonicalIdentityStore()
        fake=ClaimRecord("claim-W2",gate_key().composite,"REQ-W2","TRACKER",
                         "2026-01-01T00:00:00+00:00","2099-01-01T00:00:00+00:00",
                         "ACTIVE",None,None)
        store.claims.append(fake)
        for value in list(vars(store).values()):
            if isinstance(value,set): value.add("claim-W2")
            elif isinstance(value,dict): value["claim-W2"]="ISSUED"
        self.assertEqual(store.claim_authenticity(fake),
                         (False,"CLAIM_NOT_ISSUED_BY_THIS_STORE"))
        store,genuine=self._genuine(request_id="REQ-W3")
        forged=replace(genuine,provenance=replace(genuine.provenance,
                                                  authorizes_construction=True))
        self.assertEqual(store.claim_authenticity(forged),
                         (False,"CLAIM_CONTENT_ALTERED_SINCE_ISSUANCE"))
        self.assertEqual(CanonicalIdentityStore().claim_authenticity(genuine),
                         (False,"CLAIM_NOT_ISSUED_BY_THIS_STORE"))

    def test_W05_no_store_or_module_callable_accepts_caller_time(self):
        import inspect
        from tracker_identity import store as store_module
        offenders=[]
        for name,obj in list(vars(store_module).items())+[
                ("store."+n,o) for n,o in vars(CanonicalIdentityStore).items()]:
            if callable(obj) and not isinstance(obj,type):
                try: params=inspect.signature(obj).parameters
                except (TypeError,ValueError): continue
                offenders+=[name+"("+p+")" for p in params if p in self.TIME_PARAM_NAMES]
        self.assertEqual(offenders,[],offenders)

    def test_W05b_module_expiry_helper_refuses_caller_time(self):
        from tracker_identity import store as store_module
        store,_=self._genuine(request_id="REQ-W5B")
        with self.assertRaises(TypeError):
            store_module._expire_due_claims(store,"2999-01-01T00:00:00+00:00")
        self.assertIsNotNone(store.active_claim(gate_key().composite))

    def test_W06b_wall_clock_step_back_cannot_extend_a_claim(self):
        """MR-TIME-2 proposition, measured with REAL elapsed time. The wall
        source is driven to 2999 (instrumentation), a 1-second claim issued,
        then the real wall source restored — a large step BACKWARDS. Store
        time keeps advancing from its last value at real rate, so the claim
        still dies after ~1 real second instead of living until 2999."""
        import time as _time
        from datetime import datetime as _dt, timezone as _tz
        store=verified_store()
        wall=patch_store_source(self,"_wall_now",lambda: _dt(2999,1,1,tzinfo=_tz.utc))
        ttl=patch_store_source(self,"_governed_claim_ttl_seconds",lambda: 1)
        rec,error=self._reserve(store,"REQ-W6B")
        self.assertIsNotNone(rec,error)
        wall.stop()
        self.assertIsNotNone(store.active_claim(gate_key().composite))
        _time.sleep(1.25)
        self.assertIsNone(store.active_claim(gate_key().composite))
        self.assertEqual(store.claims[0].state,"EXPIRED")

    def test_W07_W08_malformed_governed_lifetime_is_a_structured_failure(self):
        """Defence in depth on the STORE'S OWN lifetime source. No caller
        supplies a lifetime; if the policy source is ever wrong, issuance
        refuses with a structured error instead of issuing or raising."""
        cases={-5:"CLAIM_TTL_NOT_POSITIVE",0:"CLAIM_TTL_NOT_POSITIVE",
               901:"CLAIM_TTL_EXCEEDS_GOVERNED_MAXIMUM",
               10**12:"CLAIM_TTL_EXCEEDS_GOVERNED_MAXIMUM",
               True:"CLAIM_TTL_INVALID_TYPE",1.5:"CLAIM_TTL_INVALID_TYPE",
               "60":"CLAIM_TTL_INVALID_TYPE",None:"CLAIM_TTL_INVALID_TYPE"}
        for value,expected in cases.items():
            store=verified_store()
            p=patch_store_source(self,"_governed_claim_ttl_seconds",lambda v=value: v)
            rec,error=self._reserve(store)
            p.stop()
            self.assertIsNone(rec,repr(value))
            self.assertEqual(error,expected,repr(value))
            self.assertEqual(store.claims,[],repr(value))

    def test_W08b_expiry_overflow_near_datetime_max_is_structured(self):
        from datetime import datetime as _dt, timedelta as _td, timezone as _tz
        store=verified_store()
        patch_store_source(self,"_wall_now",
                           lambda: _dt.max.replace(tzinfo=_tz.utc)-_td(seconds=10))
        rec,error=self._reserve(store)
        self.assertIsNone(rec)
        self.assertEqual(error,"CLAIM_EXPIRY_OVERFLOW")

    def test_W08c_store_time_saturates_at_datetime_max_without_raising(self):
        from datetime import datetime as _dt, timezone as _tz
        from tracker_identity import store as store_module
        store=verified_store()
        top=_dt.max.replace(tzinfo=_tz.utc)
        mono=patch_store_source(self,"_monotonic_now",lambda: 1.0)
        wall=patch_store_source(self,"_wall_now",lambda: top)
        store_module._transaction_time(store)
        wall.stop(); mono.stop()
        patch_store_source(self,"_monotonic_now",lambda: 60.0)
        self.assertEqual(store_module._transaction_time(store),top)
        rec,error=self._reserve(store)
        self.assertIsNone(rec)
        self.assertEqual(error,"CLAIM_EXPIRY_OVERFLOW")

    def test_W09c_store_time_survives_a_monotonic_clock_regression(self):
        from datetime import datetime as _dt, timezone as _tz
        from tracker_identity import store as store_module
        store=CanonicalIdentityStore()
        mono=patch_store_source(self,"_monotonic_now",lambda: 5_000.0)
        wall=patch_store_source(self,"_wall_now",lambda: _dt(2500,1,1,tzinfo=_tz.utc))
        jumped=store_module._transaction_time(store)
        wall.stop(); mono.stop()
        patch_store_source(self,"_monotonic_now",lambda: 4_000.0)
        self.assertGreaterEqual(store_module._transaction_time(store),jumped)

    def test_W09b_instrumented_time_grants_no_construction_authority(self):
        store=CanonicalIdentityStore()
        clock=_Clock(datetime.now(timezone.utc)); install_test_clock(self,clock)
        governed_claim(store,"REQ-W9B")
        r=gate_intake(store,gate_candidate(claim_request_id="REQ-W9B"))
        self.assertFalse(r.accepted)
        self.assertTrue(any("CLAIM_NOT_CONSTRUCTION_AUTHORIZED" in e for e in r.errors),
                        r.errors)
        self.assertEqual(store.all(),())

    def test_W10_clock_rewind_cannot_revive_expired_or_released_claims(self):
        store=CanonicalIdentityStore()
        clock=_Clock(datetime.now(timezone.utc)); install_test_clock(self,clock)
        governed_claim(store,"REQ-W10")
        clock.advance(10_000)
        self.assertIsNone(store.active_claim(gate_key().composite))
        clock.advance(-20_000)
        self.assertIsNone(store.active_claim(gate_key().composite))
        self.assertEqual(store.claims[0].state,"EXPIRED")
        ok,error=store.commit_registration(
            identity=keyed_row(gate_key()),creation=object(),
            content_key_composite=gate_key().composite,request_id="REQ-W10")
        self.assertFalse(ok)
        self.assertEqual(error,"CLAIM_NOT_ACTIVE:EXPIRED")
        store2,genuine=self._genuine(request_id="REQ-W10R")
        self.assertTrue(store2.release_claim(claim_id=genuine.claim_id,reason="DONE"))
        clock.advance(-50_000)
        self.assertIsNone(store2.active_claim(gate_key().composite))

    def test_W11_one_active_claim_per_key_remains_intact(self):
        store=verified_store()
        first=governed_lookup_raw(store,"REQ-W11A")
        second=governed_lookup_raw(store,"REQ-W11B")
        self.assertIsNotNone(first.absent_claim_token)
        self.assertIsNone(second.absent_claim_token)
        self.assertTrue(any("PENDING_CLAIM_EXISTS" in e for e in second.errors))
        self.assertEqual(len([c for c in store.claims if c.state=="ACTIVE"]),1)

    def test_W12_W13_W14_fences_hold(self):
        store,genuine=self._genuine(request_id="REQ-W12")
        self.assertFalse(genuine.provenance.authorizes_construction)
        self.assertEqual(resolve_governed_search_policy(governed_search_policy()),())
        self.assertEqual(resolve_governed_normalizer(governed_normalizer()),())
        closed=CanonicalIdentityStore()
        self.assertFalse(hasattr(closed,"add"))         # A14 closed in DC-006
        self.assertEqual(closed.all(),())


class ClockIsolationPublicWeakref005(unittest.TestCase):
    """DC-CLOCK-ISOLATION-WEAKREF-TEST-005 — mandatory controls NC-1..NC-17."""

    CLOCK_ATTRS=("_clock","clock","_now","now","_wall_now","wall_now",
                 "_monotonic_now","_time","time","last_effective","_ttl","ttl",
                 "_governed_claim_ttl_seconds","now_iso","_caller_now")
    FORBIDDEN_ISSUANCE_PARAMS=("ttl","ttl_seconds","lifetime","expires_ts",
                               "issued_ts","expires_at","issued_at","now",
                               "now_iso","clock","transaction_time","timestamp")

    def _genuine(self,request_id="REQ-5"):
        store=CanonicalIdentityStore()
        governed_claim(store,request_id)
        return store,store.claims[0]

    # NC-1 / NC-2 -------------------------------------------------------
    def test_NC01_NC02_exact_public_weakref_route(self):
        """The governed route, using documented public APIs ONLY:
            weakref.getweakrefs(store)  -> ref
            ref.__callback__            -> weakref.finalize
            finalize.peek()             -> (obj, func, args, kwargs)
            func.__self__               -> must NOT be the ledger
        At aaec2c4 this route returned `dict.pop` bound to the ledger and a
        forged claim written through it committed a row. weakref.finalize.
        _registry is deliberately NOT used anywhere in this test.

        BOUNDARY (DC-006 Correction D). This closes the PUBLIC weakref route
        only. Type-1 in-process authority = integrity-against-accident, NOT
        security against adversarial same-process Python code: closure-cell
        reflection, gc traversal and ctypes can still reach the ledger. That is
        a declared out-of-boundary residual; this test makes no claim about it."""
        import weakref
        from dataclasses import replace
        store,genuine=self._genuine(request_id="REQ-PUB")
        refs=weakref.getweakrefs(store)
        self.assertGreaterEqual(len(refs),1)
        finalizers=[r.__callback__ for r in refs
                    if isinstance(r.__callback__,weakref.finalize)]
        self.assertEqual(len(finalizers),1,"one cleanup finalizer on the store")
        peeked=finalizers[0].peek()
        self.assertIsNotNone(peeked,"finalizer must be alive while store is")
        obj,func,args,kwargs=peeked
        self.assertIs(obj,store)
        # no bound-method owner of any kind
        self.assertIsNone(getattr(func,"__self__",None),
                          "callback is bound: its owner is publicly exposed")
        # nothing reachable from the public route is a mutable container
        for value in (func,*args,*(kwargs or {}).values()):
            self.assertNotIsInstance(value,(dict,list,set),repr(value))
        self.assertEqual(args,(id(store),))
        self.assertEqual(dict(kwargs or {}),{})
        # NC-2: the former forgery chain has nothing to rewrite
        store.claims[0]=replace(genuine,provenance=replace(
            genuine.provenance,authorizes_construction=True))
        ok,error=store.commit_registration(
            identity=keyed_row(gate_key()),creation=object(),
            content_key_composite=gate_key().composite,request_id="REQ-PUB")
        self.assertFalse(ok)
        self.assertEqual(error,"CLAIM_CONTENT_ALTERED_SINCE_ISSUANCE")
        self.assertEqual(store.all(),())

    # NC-3 --------------------------------------------------------------
    def test_NC03_constructor_has_no_clock_authority(self):
        import dataclasses, inspect
        names={f.name for f in dataclasses.fields(CanonicalIdentityStore)}
        self.assertEqual(names & set(self.CLOCK_ATTRS),set(),names)
        ctor=inspect.signature(CanonicalIdentityStore).parameters
        for bad in self.CLOCK_ATTRS:
            self.assertNotIn(bad,ctor,bad)
        with self.assertRaises(TypeError):
            CanonicalIdentityStore(_clock=lambda: datetime(2999,1,1,tzinfo=timezone.utc))

    def test_NC03b_store_time_advances_from_the_monotonic_source(self):
        """Pins that elapsed time comes from the DEDICATED monotonic source
        (mutant D3). Existing tests only asserted inequalities, which still
        held when the source was bypassed for time.monotonic(). With the wall
        source frozen, a 10,000 s advance of the monotonic source must advance
        store time by exactly 10,000 s."""
        from datetime import datetime as _dt, timezone as _tz, timedelta as _td
        from tracker_identity import store as store_module
        store=CanonicalIdentityStore()
        patch_store_source(self,"_wall_now",lambda: _dt(2400,1,1,tzinfo=_tz.utc))
        mono=patch_store_source(self,"_monotonic_now",lambda: 100.0)
        first=store_module._transaction_time(store)
        mono.stop()
        patch_store_source(self,"_monotonic_now",lambda: 10_100.0)
        second=store_module._transaction_time(store)
        self.assertEqual(second-first,_td(seconds=10_000))

    # NC-4 --------------------------------------------------------------
    def test_NC04_no_caller_mutable_store_field_controls_time(self):
        from datetime import datetime as _dt, timezone as _tz, timedelta as _td
        from tracker_identity import store as store_module
        future=_dt(2999,1,1,tzinfo=_tz.utc)
        store=CanonicalIdentityStore()
        for attr in self.CLOCK_ATTRS:
            setattr(store,attr,(lambda: future))
        store.last_effective=future
        before=_dt.now(_tz.utc)
        observed=store_module._transaction_time(store)
        after=_dt.now(_tz.utc)
        self.assertGreaterEqual(observed,before-_td(seconds=1))
        self.assertLessEqual(observed,after+_td(seconds=1))
        rec,error=governed_claim(store,"REQ-NC4"),None
        self.assertLess(_dt.fromisoformat(store.claims[0].issued_ts).year,2100)

    # NC-5 / NC-6 / NC-7 ------------------------------------------------
    def test_NC05_NC06_NC07_issuance_surfaces_take_no_time_or_lifetime(self):
        import inspect
        from tracker_identity import store as store_module
        for fn in (CanonicalIdentityStore.reserve_claim,store_module._issue_claim):
            params=inspect.signature(fn).parameters
            for bad in self.FORBIDDEN_ISSUANCE_PARAMS:
                self.assertNotIn(bad,params,fn.__name__+"."+bad)
        store=verified_store()
        for kw in ({"ttl_seconds":60},{"issued_ts":"2999-01-01T00:00:00+00:00"},
                   {"expires_ts":"2999-01-01T00:00:00+00:00"}):
            with self.assertRaises(TypeError):
                store.reserve_claim(content_key_composite=gate_key().composite,
                    request_id="REQ-K",search_policy=governed_search_policy(),
                    normalizer=governed_normalizer(),**kw)
            with self.assertRaises(TypeError):
                store_module._issue_claim(store,content_key_composite=gate_key().composite,
                    request_id="REQ-K",search_policy=governed_search_policy(),
                    normalizer=governed_normalizer(),include_validation_scope=False,
                    issuer="TRACKER",**kw)

    def test_NC06b_issued_and_expires_come_from_store_time_and_policy(self):
        from datetime import datetime as _dt, timezone as _tz, timedelta as _td
        from tracker_identity.store import CLAIM_TTL_MAX_SECONDS
        before=_dt.now(_tz.utc)
        store,genuine=self._genuine(request_id="REQ-NC6")
        after=_dt.now(_tz.utc)
        issued=_dt.fromisoformat(genuine.issued_ts)
        expires=_dt.fromisoformat(genuine.expires_ts)
        self.assertGreaterEqual(issued,before-_td(seconds=1))
        self.assertLessEqual(issued,after+_td(seconds=1))
        self.assertEqual((expires-issued).total_seconds(),CLAIM_TTL_MAX_SECONDS)

    # NC-8 --------------------------------------------------------------
    def test_NC08_test_time_mechanism_is_code_replacement_only(self):
        """The ONLY way to steer store time is replacing the store module's
        source functions. Demonstrated both ways: data does nothing, code
        replacement does something — so the hook is instrumentation, not an
        API or data surface."""
        from datetime import datetime as _dt, timezone as _tz
        from tracker_identity import store as store_module
        future=_dt(2999,1,1,tzinfo=_tz.utc)
        data_store=CanonicalIdentityStore()
        for attr in self.CLOCK_ATTRS:
            setattr(data_store,attr,(lambda: future))
        self.assertLess(store_module._transaction_time(data_store).year,2100)
        code_store=CanonicalIdentityStore()
        patch_store_source(self,"_wall_now",lambda: future)
        self.assertEqual(store_module._transaction_time(code_store),future)

    # NC-9 / NC-10 / NC-11 / NC-12 -------------------------------------
    def test_NC09_to_NC12_lifecycle_concurrency_isolation_content(self):
        from dataclasses import replace
        store=CanonicalIdentityStore()
        clock=_Clock(datetime.now(timezone.utc)); install_test_clock(self,clock)
        governed_claim(store,"REQ-N9")
        clock.advance(10_000)
        self.assertIsNone(store.active_claim(gate_key().composite))
        clock.advance(-30_000)
        self.assertIsNone(store.active_claim(gate_key().composite))      # NC-9
        s10=verified_store()
        self.assertIsNotNone(governed_lookup_raw(s10,"A").absent_claim_token)
        self.assertIsNone(governed_lookup_raw(s10,"B").absent_claim_token)  # NC-10
        s11,g=self._genuine(request_id="REQ-N11")
        self.assertEqual(CanonicalIdentityStore().claim_authenticity(g),
                         (False,"CLAIM_NOT_ISSUED_BY_THIS_STORE"))          # NC-11
        self.assertEqual(s11.claim_authenticity(replace(g,issued_ts="2999-01-01T00:00:00+00:00")),
                         (False,"CLAIM_CONTENT_ALTERED_SINCE_ISSUANCE"))    # NC-12

    # NC-13 -------------------------------------------------------------
    def test_NC13_lifecycle_helpers_cannot_exceed_the_public_boundary(self):
        from tracker_identity import store as store_module
        self.assertFalse(hasattr(store_module,"_terminate_claim"),
                         "free-form state/reason terminator must not exist")
        for reserved in ("TTL_EXPIRED","REGISTRATION_COMPLETED"," TTL_EXPIRED ",""," "):
            store,g=self._genuine(request_id="REQ-R"+str(abs(hash(reserved))))
            self.assertFalse(store.release_claim(claim_id=g.claim_id,reason=reserved),
                             repr(reserved))
            self.assertFalse(store_module._release_claim(store,g.claim_id,reserved),
                             repr(reserved))
            self.assertEqual(store_module._ledger_state(store,g.claim_id),"ACTIVE")
        store,g=self._genuine(request_id="REQ-OK")
        self.assertTrue(store_module._release_claim(store,g.claim_id,"DONE"))
        self.assertEqual(store_module._ledger_state(store,g.claim_id),"RELEASED")

    def test_NC13b_consume_cannot_falsify_a_registration(self):
        """Even with the identity planted in records by the test fixture seeder and a
        genuine ACTIVE claim, consumption is refused: there is no construction
        authority, so no registration happened."""
        from tracker_identity import store as store_module
        store,g=self._genuine(request_id="REQ-CON")
        planted=keyed_row(gate_key())
        seed_fixture(store,[planted])
        self.assertFalse(store_module._consume_claim(store,g.claim_id,planted))
        self.assertEqual(store_module._ledger_state(store,g.claim_id),"ACTIVE")
        self.assertEqual(store.claims[0].release_reason,None)

    def test_NC13c_no_exported_helper_can_expire_a_live_claim(self):
        """EXPIRED is assigned only by genuine store-time expiry."""
        import inspect
        from tracker_identity import store as store_module
        store,g=self._genuine(request_id="REQ-EXP")
        for name,fn in list(vars(store_module).items()):
            if not callable(fn) or isinstance(fn,type) or name.startswith("__"):
                continue
            params=list(inspect.signature(fn).parameters)
            if params[:1]!=["store"]:
                continue
            for args in ((g.claim_id,"EXPIRED","TTL_EXPIRED"),(g.claim_id,"TTL_EXPIRED"),
                         (g.claim_id,),()):
                try:
                    fn(store,*args)
                except (TypeError,PermissionError):
                    pass    # refused: wrong shape, or the fixture seeder is disabled
        self.assertNotEqual(store_module._ledger_state(store,g.claim_id),"EXPIRED")

    # NC-14 / NC-15 / NC-16 --------------------------------------------
    def test_NC14_NC15_NC16_fences_hold(self):
        store,g=self._genuine(request_id="REQ-F")
        self.assertFalse(g.provenance.authorizes_construction)
        r=gate_intake(store,gate_candidate(claim_request_id="REQ-F"))
        self.assertTrue(any("CLAIM_NOT_CONSTRUCTION_AUTHORIZED" in e for e in r.errors))
        self.assertEqual(resolve_governed_search_policy(governed_search_policy()),())
        self.assertEqual(resolve_governed_normalizer(governed_normalizer()),())
        closed=CanonicalIdentityStore()
        self.assertFalse(hasattr(closed,"extend"))      # A14 closed in DC-006
        self.assertEqual(closed.all(),())

class ConstructionConsumptionKillB006(unittest.TestCase):
    """DC-006 Correction B — permanent kills for D10/D11/D12/D13/A15.

    The construction-consumption path is unreachable in production:
    _governed_construction_authority() returns False. These tests reach it ONLY
    by replacing that FUNCTION under unittest.mock (code replacement = test
    instrumentation). No public construction-authority surface is added.
    """

    def _authorized(self,request_id="REQ-B6"):
        """A claim issued while the construction-authority SOURCE is replaced.
        The patch is scoped to issuance only and removed before returning."""
        from unittest import mock
        from tracker_identity import store as store_module
        store=CanonicalIdentityStore()
        with mock.patch.object(store_module,"_governed_construction_authority",
                               return_value=True):
            governed_claim(store,request_id)
        self.assertIs(store.claims[0].provenance.authorizes_construction,True)
        return store,store.claims[0]

    def test_B0_production_never_issues_construction_authority(self):
        from tracker_identity import store as store_module
        self.assertIs(store_module._governed_construction_authority({}),False)
        store=CanonicalIdentityStore()
        governed_claim(store,"REQ-B0")
        self.assertIs(store.claims[0].provenance.authorizes_construction,False)

    def test_B0b_truthy_non_true_source_is_not_authority(self):
        from unittest import mock
        from tracker_identity import store as store_module
        store=CanonicalIdentityStore()
        with mock.patch.object(store_module,"_governed_construction_authority",
                               return_value="YES"):
            governed_claim(store,"REQ-B0B")
        self.assertIs(store.claims[0].provenance.authorizes_construction,False)

    def test_A15_authorized_registration_consumes_the_claim(self):
        from tracker_identity import store as store_module
        store,claim=self._authorized("REQ-A15")
        r=gate_intake(store,gate_candidate(claim_request_id="REQ-A15"))
        self.assertTrue(r.accepted,r.errors)
        self.assertEqual(len(store.all()),1)
        self.assertEqual(store_module._ledger_state(store,claim.claim_id),"RELEASED")
        self.assertEqual(store.claims[0].state,"RELEASED")
        self.assertEqual(store.claims[0].release_reason,"REGISTRATION_COMPLETED")
        # A consumed claim is terminal: it cannot register a second identity.
        again=gate_intake(store,gate_candidate("gold.logret.2",claim_request_id="REQ-A15"))
        self.assertFalse(again.accepted)
        self.assertEqual(len(store.all()),1)

    def test_B_positive_control_direct_consume_succeeds_when_all_hold(self):
        """Proves D10-D13 below are not vacuous: with every precondition true,
        direct consumption DOES succeed."""
        from tracker_identity import store as store_module
        store,claim=self._authorized("REQ-POS")
        row=keyed_row(gate_key())
        seed_fixture(store,[row])
        self.assertTrue(store_module._consume_claim(store,claim.claim_id,row))
        self.assertEqual(store_module._ledger_state(store,claim.claim_id),"RELEASED")

    def test_D10_expired_authorized_claim_is_not_consumed(self):
        from tracker_identity import store as store_module
        clock=_Clock(datetime.now(timezone.utc))
        install_test_clock(self,clock)
        store,claim=self._authorized("REQ-D10")
        row=keyed_row(gate_key())
        seed_fixture(store,[row])
        clock.advance(10_000)
        store_module._expire_due_claims(store)
        self.assertEqual(store_module._ledger_state(store,claim.claim_id),"EXPIRED")
        self.assertFalse(store_module._consume_claim(store,claim.claim_id,row))
        self.assertEqual(store_module._ledger_state(store,claim.claim_id),"EXPIRED")

    def test_D11_tampered_mirror_is_not_consumed(self):
        from dataclasses import replace
        from tracker_identity import store as store_module
        store,claim=self._authorized("REQ-D11")
        row=keyed_row(gate_key())
        seed_fixture(store,[row])
        store.claims[0]=replace(claim,issuer="ATTACKER")
        self.assertFalse(store_module._consume_claim(store,claim.claim_id,row))
        self.assertEqual(store_module._ledger_state(store,claim.claim_id),"ACTIVE")

    def test_D12_identity_not_in_records_is_not_consumed(self):
        from tracker_identity import store as store_module
        store,claim=self._authorized("REQ-D12")
        row=keyed_row(gate_key())
        seed_fixture(store,[keyed_row(gate_key())])   # equal, but not the same object
        self.assertFalse(store_module._consume_claim(store,claim.claim_id,row))
        self.assertFalse(store_module._consume_claim(store,claim.claim_id,None))
        self.assertEqual(store_module._ledger_state(store,claim.claim_id),"ACTIVE")

    def test_D13_identity_with_other_content_key_is_not_consumed(self):
        from tracker_identity import store as store_module
        store,claim=self._authorized("REQ-D13")
        other=keyed_row(gate_key(timeframe="H4"),feature_id="gold.other")
        seed_fixture(store,[other])
        self.assertFalse(store_module._consume_claim(store,claim.claim_id,other))
        self.assertEqual(store_module._ledger_state(store,claim.claim_id),"ACTIVE")

    def test_B_construction_authorized_path_still_absent_in_source(self):
        """CONSTRUCTION_AUTHORIZED_PATH_EXISTS = NO: no production literal grant."""
        import inspect,pathlib,re
        src=pathlib.Path(__file__).resolve().parents[1]/"tracker_identity"
        for f in src.glob("*.py"):
            text=f.read_text(encoding="utf-8")
            self.assertIsNone(re.search(r"authorizes_construction\s*=\s*True",text),f.name)
        from tracker_identity import store as store_module
        body=inspect.getsource(store_module._governed_construction_authority)
        self.assertIn("return False",body)
        self.assertNotIn("return True",body)


class ReservedReasonLookalikesM2006(unittest.TestCase):
    """DC-006 non-blocking M-2: reserved-reason lookalikes are refused."""

    def test_M2_lookalikes_refused_ordinary_reasons_accepted(self):
        from tracker_identity import store as store_module
        for n,reason in enumerate(("ttl_expired","TTL-EXPIRED","Ttl Expired",
                                   "ＴＴＬ＿ＥＸＰＩＲＥＤ",
                                   "TTL_EXPIRED​","registration.completed",
                                   "REGISTRATION_COMPLETED	")):
            store=CanonicalIdentityStore()
            governed_claim(store,"REQ-M2-%d"%n)
            cid=store.claims[0].claim_id
            self.assertFalse(store.release_claim(claim_id=cid,reason=reason),repr(reason))
            self.assertEqual(store_module._ledger_state(store,cid),"ACTIVE",repr(reason))
        for n,reason in enumerate(("DONE","TTL expired early - withdrawn","WITHDRAWN")):
            store=CanonicalIdentityStore()
            governed_claim(store,"REQ-M2-OK-%d"%n)
            cid=store.claims[0].claim_id
            self.assertTrue(store.release_claim(claim_id=cid,reason=reason),repr(reason))


class ClaimlessWritePathsClosedA14006(unittest.TestCase):
    """DC-006 Correction C — A14. Canonical-identity write-path inventory:

      GOVERNED REGISTRATION    store.commit_registration -> store-owned txn
      GOVERNED IMPORT          import_identity_content -> store-owned import
                               commit that RE-RUNS the whole contract
      GOVERNED TRANSITION      transition_authority_state -> store-owned
                               transition commit (replacement, not creation)
      TEST / FIXTURE ONLY      _fixture_write_records, disabled unless
                               _fixture_seeding_permitted is code-replaced
      UNGOVERNED BYPASS        none reachable by ordinary calls; store.add,
                               store.extend, records=[...] seeding and public
                               list mutation were removed
    """

    def test_A14_1_ordinary_writers_do_not_exist(self):
        store=CanonicalIdentityStore()
        for name in ("add","extend","append","insert","set_records","load"):
            self.assertFalse(hasattr(store,name),name)
        self.assertIsInstance(store.records,tuple)
        with self.assertRaises(AttributeError):
            store.records=[keyed_row(gate_key())]
        with self.assertRaises(AttributeError):
            store.records.append(keyed_row(gate_key()))
        self.assertEqual(store.all(),())

    def test_A14_2_constructor_cannot_seed_records(self):
        with self.assertRaises(TypeError):
            CanonicalIdentityStore([keyed_row(gate_key())])
        with self.assertRaises(TypeError):
            CanonicalIdentityStore(records=[keyed_row(gate_key())])

    def test_A14_3_fixture_seeder_refuses_in_production(self):
        from tracker_identity import store as store_module
        store=CanonicalIdentityStore()
        self.assertIs(store_module._fixture_seeding_permitted(),False)
        with self.assertRaises(PermissionError):
            store_module._fixture_write_records(store,[keyed_row(gate_key())])
        with self.assertRaises(PermissionError):
            store_module._fixture_write_records(store,[keyed_row(gate_key())],replace_all=True)
        self.assertEqual(store.all(),())

    def test_A14_3b_truthy_non_true_permission_is_refused(self):
        from unittest import mock
        from tracker_identity import store as store_module
        store=CanonicalIdentityStore()
        with mock.patch.object(store_module,"_fixture_seeding_permitted",return_value="YES"):
            with self.assertRaises(PermissionError):
                store_module._fixture_write_records(store,[keyed_row(gate_key())])
        self.assertEqual(store.all(),())

    def test_A14_4_fixture_seeder_is_available_to_tests(self):
        from tracker_identity import store as store_module
        store=fixture_store([keyed_row(gate_key())])
        self.assertEqual(len(store.all()),1)
        self.assertIs(store_module._fixture_seeding_permitted(),False)  # patch scoped
        seed_fixture(store,[keyed_row(gate_key(timeframe="H4"),feature_id="r")],replace_all=True)
        self.assertEqual([r.feature_id for r in store.all()],["r"])

    def test_A14_5_records_view_is_a_snapshot(self):
        store=fixture_store([keyed_row(gate_key())])
        view=store.records
        seed_fixture(store,[keyed_row(gate_key(timeframe="H4"),feature_id="x")])
        self.assertEqual(len(view),1)
        self.assertEqual(len(store.records),2)

    def test_A14_6_staging_copy_refuses_every_authority_operation(self):
        from tracker_identity import store as store_module
        base=fixture_store([keyed_row(gate_key(timeframe="H4"),feature_id="b")])
        staged=store_module._staging_copy(base,extra_records=(keyed_row(gate_key()),))
        self.assertTrue(store_module._is_staged(staged))
        self.assertFalse(store_module._is_staged(base))
        self.assertEqual(len(staged.records),2)
        self.assertEqual(len(base.records),1)            # base untouched
        empty_staged=store_module._staging_copy(CanonicalIdentityStore())
        r=governed_lookup_raw(empty_staged,"REQ-STG")
        self.assertIsNone(r.absent_claim_token)
        self.assertTrue(any("STORE_IS_STAGING_COPY" in e for e in r.errors),r.errors)
        self.assertEqual(empty_staged.claims,[])
        ok,err=staged.commit_registration(identity=keyed_row(gate_key()),creation=None,
                                          content_key_composite=gate_key().composite,
                                          request_id="REQ-STG")
        self.assertFalse(ok); self.assertEqual(err,"STORE_IS_STAGING_COPY")
        ok,_,errs=store_module._commit_governed_transition(
            staged,key=("b","1","ERA_1"),from_state="CURRENT",transition=None)
        self.assertFalse(ok); self.assertIn("STORE_IS_STAGING_COPY",errs)
        self.assertEqual(len(staged.records),2)

    def test_A14_7_registration_commit_without_claim_is_refused(self):
        from tracker_identity import store as store_module
        store=CanonicalIdentityStore()
        row=keyed_row(gate_key())
        for rid,ck in (("",gate_key().composite),("REQ",""),("REQ-NONE",gate_key().composite)):
            ok,_=store_module._commit_governed_registration(
                store,identity=row,creation=None,content_key_composite=ck,request_id=rid)
            self.assertFalse(ok)
        # Genuine claim, but no construction authority: still refused.
        governed_claim(store,"REQ-GEN7")
        ok,err=store_module._commit_governed_registration(
            store,identity=row,creation=None,content_key_composite=gate_key().composite,
            request_id="REQ-GEN7")
        self.assertFalse(ok); self.assertEqual(err,"CLAIM_NOT_CONSTRUCTION_AUTHORIZED")
        self.assertEqual(store.all(),())

    def test_A14_8_transition_commit_cannot_inject_a_caller_record(self):
        """The transition commit takes a transition, never a replacement row,
        and re-checks the structural invariants on its own."""
        import inspect
        from tracker_identity import store as store_module
        from tracker_identity.transition import (GovernedStateTransitionRecord,
                                                 TransitionClass)
        params=set(inspect.signature(store_module._commit_governed_transition).parameters)
        self.assertEqual(params,{"store","key","from_state","transition"})
        store=fixture_store([keyed_row(gate_key(),feature_id="t")])
        def tr(**over):
            v=dict(transition_id="T1",segment_id="TRACKER",object_id="t",
                   object_version="1",era_id="ERA_1",from_state="CURRENT",
                   to_state="QUARANTINED",transition_class=TransitionClass.QUARANTINE,
                   reason_class="R",reason_ref="r",evidence_ref=None,changed_ts="x",
                   changed_by="M",authority_ref="a",record_version="1",
                   prior_transition_id="NO-CREATION")
            v.update(over); return GovernedStateTransitionRecord(**v)
        key=("t","1","ERA_1")
        cases=(("not-a-record","TRANSITION_RECORD_TYPE_INVALID"),
               (tr(object_id="u"),"TRANSITION_OBJECT_KEY_MISMATCH"),
               (tr(to_state="CURRENT"),"TRANSITION_FROM_TO_STATE_INVALID"),
               (tr(to_state="BOGUS"),"UNKNOWN_TO_STATE"),
               (tr(),"PRIOR_TRANSITION_ID_MISMATCH"))
        for t,code in cases:
            ok,_,errs=store_module._commit_governed_transition(
                store,key=key,from_state="CURRENT",transition=t)
            self.assertFalse(ok,code); self.assertIn(code,errs)
        ok,_,errs=store_module._commit_governed_transition(
            store,key=key,from_state="SUPERSEDED",
            transition=tr(from_state="SUPERSEDED"))
        self.assertFalse(ok); self.assertIn("FROM_STATE_MISMATCH",errs)
        self.assertEqual(store.records[0].lifecycle_state,"CURRENT")
        self.assertEqual(store.transitions,[])

    def test_A14_8b_transition_commit_rechecks_chain_duplicates_and_uniqueness(self):
        """Kills store-level transition mutants the public wrapper would mask:
        the store-owned commit re-checks prior chain, duplicate transition id
        and unique object match ON ITS OWN."""
        from tracker_identity import store as store_module
        from tracker_identity.transition import (CreationProvenanceRecord,
                                                 GovernedStateTransitionRecord,
                                                 TransitionClass)
        creation=CreationProvenanceRecord("C1","TRACKER","t","1","ERA_1","CURRENT",
                                          "r","x","M","a")
        def tr(**over):
            v=dict(transition_id="T1",segment_id="TRACKER",object_id="t",
                   object_version="1",era_id="ERA_1",from_state="CURRENT",
                   to_state="QUARANTINED",transition_class=TransitionClass.QUARANTINE,
                   reason_class="R",reason_ref="r",evidence_ref=None,changed_ts="x",
                   changed_by="M",authority_ref="a",record_version="1",
                   prior_transition_id="C1")
            v.update(over); return GovernedStateTransitionRecord(**v)
        key=("t","1","ERA_1")
        def fresh():
            store=fixture_store([keyed_row(gate_key(),feature_id="t")])
            store.add_creation(creation)
            return store
        store=fresh()
        ok,_,errs=store_module._commit_governed_transition(
            store,key=key,from_state="CURRENT",transition=tr(prior_transition_id="WRONG"))
        self.assertFalse(ok); self.assertIn("PRIOR_TRANSITION_ID_MISMATCH",errs)
        store=fresh()
        store.add_transition(tr(transition_id="T1",object_id="elsewhere"))
        ok,_,errs=store_module._commit_governed_transition(
            store,key=key,from_state="CURRENT",transition=tr())
        self.assertFalse(ok); self.assertIn("DUPLICATE_TRANSITION_ID",errs)
        store=fixture_store([keyed_row(gate_key(),feature_id="t"),
                             keyed_row(gate_key(),feature_id="t")])
        store.add_creation(creation)
        ok,_,errs=store_module._commit_governed_transition(
            store,key=key,from_state="CURRENT",transition=tr())
        self.assertFalse(ok); self.assertIn("TRACKED_OBJECT_NOT_UNIQUE_OR_NOT_FOUND",errs)
        self.assertTrue(all(r.lifecycle_state=="CURRENT" for r in store.records))
        # Positive control: the same commit succeeds when every invariant holds,
        # and the replacement row is DERIVED from the transition.
        store=fresh()
        ok,updated,errs=store_module._commit_governed_transition(
            store,key=key,from_state="CURRENT",transition=tr())
        self.assertTrue(ok,errs)
        self.assertEqual(updated.lifecycle_state,"QUARANTINED")
        self.assertFalse(updated.is_current)
        self.assertIs(store.records[0],updated)
        self.assertEqual(len(store.transitions),1)

    def test_A14_9_no_production_module_writes_records_outside_the_store(self):
        """Source inventory: canonical records are written only inside the
        store-owned closure writers."""
        import pathlib,re
        src=pathlib.Path(__file__).resolve().parents[1]/"tracker_identity"
        write=re.compile(r"records\s*(\[[^\]]*\]\s*=(?!=)|\.(append|extend|insert|pop|remove|clear)\(|\+=)")
        hits=0
        for f in src.glob("*.py"):
            for n,line in enumerate(f.read_text(encoding="utf-8").splitlines(),1):
                code=line.split("#",1)[0]
                if re.search(r"(errors|creation_records|searched_records)",code):
                    continue
                if write.search(code):
                    hits+=1
                    self.assertEqual(f.name,"store.py",f"{f.name}:{n}: {line.strip()}")
        self.assertGreater(hits,0)   # the scan is live, not vacuous

class InstrumentIdentityCorrectionA006(unittest.TestCase):
    """DC-006 Correction A — shared instrument-binding vs canonical-identity rule.

    Composer V9 §39.4 (line 2054, verified at source): "INSTRUMENT / UNIVERSE /
    SCOPE difference = PAYLOAD_BINDING unless semantics change; if semantics
    change or are unclear, REVIEW_REQUIRED." Frozen Tracker Core: SCOPE /
    ELIGIBILITY-DEFINITION holds instrument only "where encoded in the governed
    feature definition"; §7 cross-instrument access is DEFAULT DENY.
    """

    AGNOSTIC=dict(instrument_applicability="INSTRUMENT_AGNOSTIC",
                  scope_universe="FX_METALS/ERA_1")
    SPECIFIC=dict(instrument_applicability="INSTRUMENT_SPECIFIC")
    FITTED={"fitted_parameters":{"mu":0.1,"sigma":0.02},"fitting_window":"2020-2024"}

    def _content(self,**over):
        c=dict(GATE_CONTENT); c.update(over); return c

    def _key(self,**over):
        key,errors=build_content_identity_key(self._content(**over))
        return key,errors

    def _lookup(self,store,instrument,request_id="REQ-A6",**over):
        return identity_lookup(
            store=store,
            subject=pre_id_subject(instrument=instrument,
                                   content=dict(instrument=instrument,**over)),
            request_id=request_id,search_policy=governed_search_policy(),
            normalizer=governed_normalizer())

    def _row(self,key,instrument,feature_id="gold.shared"):
        from dataclasses import replace
        return replace(keyed_row(key,feature_id=feature_id),instrument=instrument)

    # I1 ----------------------------------------------------------------
    def test_I1_same_semantics_different_bound_instrument_does_not_split(self):
        kx,ex=self._key(instrument="XAUUSD",**self.AGNOSTIC)
        ke,ee=self._key(instrument="EURUSD",**self.AGNOSTIC)
        self.assertEqual((ex,ee),((),()))
        self.assertEqual(kx.composite,ke.composite)
        self.assertEqual(kx.scope_eligibility,ke.scope_eligibility)
        self.assertEqual(kx.definition_semantics,ke.definition_semantics)
        # End to end: an EURUSD-bound request resolves the SAME canonical
        # identity first registered under XAUUSD — no new identity is minted.
        store=verified_store([self._row(kx,"XAUUSD")])
        r=self._lookup(store,"EURUSD",**self.AGNOSTIC)
        self.assertEqual(r.outcome,LookupOutcome.EXACT_CANONICAL_IDENTITY)
        self.assertIsNone(r.absent_claim_token)
        self.assertEqual(store.claims,[])

    # I2 ----------------------------------------------------------------
    def test_I2_instrument_specific_semantics_remain_identity_content(self):
        kx,_=self._key(instrument="XAUUSD",**self.SPECIFIC)
        ke,_=self._key(instrument="EURUSD",**self.SPECIFIC)
        self.assertNotEqual(kx.composite,ke.composite)
        self.assertNotEqual(kx.scope_eligibility,ke.scope_eligibility)
        # Same definition body: this is a RELATED identity, routed to review —
        # never silently merged, never silently treated as unrelated.
        self.assertEqual(kx.definition_semantics,ke.definition_semantics)
        store=verified_store([self._row(kx,"XAUUSD")])
        r=self._lookup(store,"EURUSD",**self.SPECIFIC)
        self.assertEqual(r.outcome,LookupOutcome.NEAR_MATCH)
        self.assertEqual(r.pending_collision_result,
                         "RELATED_VERSION_CONTENT_REVIEW_REQUIRED")
        self.assertIsNone(r.absent_claim_token)

    def test_I2b_declared_applicability_is_itself_scope_content(self):
        ka,_=self._key(instrument="XAUUSD",instrument_applicability="INSTRUMENT_AGNOSTIC")
        ks,_=self._key(instrument="XAUUSD",instrument_applicability="INSTRUMENT_SPECIFIC")
        self.assertNotEqual(ka.scope_eligibility,ks.scope_eligibility)
        self.assertEqual(ka.definition_semantics,ks.definition_semantics)

    # I3 ----------------------------------------------------------------
    def test_I3_unclear_applicability_cannot_share_or_split_silently(self):
        missing=self._content(instrument="XAUUSD")
        missing.pop("instrument_applicability")
        key,errors=build_content_identity_key(missing)
        self.assertIsNone(key)
        self.assertIn("CONTENT_DIMENSION_MISSING:instrument_applicability",errors)
        for unclear in ("MAYBE","","  ",None,"instrument_agnostic",
                        "INSTRUMENT_AGNOSTIC ","AGNOSTIC","SPECIFIC",True,1):
            key,errors=self._key(instrument="XAUUSD",instrument_applicability=unclear)
            self.assertIsNone(key,repr(unclear))
            self.assertTrue(errors,repr(unclear))
        # End to end: unclear routes to review — incomplete, and no claim.
        store=verified_store()
        r=self._lookup(store,"XAUUSD",instrument_applicability="MAYBE")
        self.assertEqual(r.outcome,LookupOutcome.INCOMPLETE_LOOKUP)
        self.assertTrue(any("INSTRUMENT_APPLICABILITY_REVIEW_REQUIRED" in e
                            for e in r.errors),r.errors)
        self.assertIsNone(r.absent_claim_token)
        self.assertEqual(store.claims,[])

    # I4 ----------------------------------------------------------------
    def test_I4_fitted_state_never_crosses_instruments(self):
        """Reusable definition, but learned state is always instrument-qualified,
        even for an instrument-AGNOSTIC definition (frozen §7 default deny)."""
        kx,ex=self._key(instrument="XAUUSD",fitted_state=self.FITTED,**self.AGNOSTIC)
        ke,ee=self._key(instrument="EURUSD",fitted_state=self.FITTED,**self.AGNOSTIC)
        self.assertEqual((ex,ee),((),()))
        self.assertEqual(kx.definition_semantics,ke.definition_semantics)
        self.assertEqual(kx.scope_eligibility,ke.scope_eligibility)
        self.assertNotEqual(kx.fitted_learned_state,ke.fitted_learned_state)
        self.assertNotEqual(kx.composite,ke.composite)
        # The XAUUSD fitted artifact cannot be resolved as EXACT for EURUSD.
        store=verified_store([self._row(kx,"XAUUSD")])
        r=self._lookup(store,"EURUSD",fitted_state=self.FITTED,**self.AGNOSTIC)
        self.assertNotEqual(r.outcome,LookupOutcome.EXACT_CANONICAL_IDENTITY)
        self.assertIsNone(r.exact_match)
        # Control: with NO learned state, the fitted subkey is instrument-free.
        ux,_=self._key(instrument="XAUUSD",**self.AGNOSTIC)
        ue,_=self._key(instrument="EURUSD",**self.AGNOSTIC)
        self.assertEqual(ux.fitted_learned_state,ue.fitted_learned_state)

    def test_I4b_specific_definitions_are_fitted_qualified_too(self):
        kx,_=self._key(instrument="XAUUSD",fitted_state=self.FITTED,**self.SPECIFIC)
        ke,_=self._key(instrument="EURUSD",fitted_state=self.FITTED,**self.SPECIFIC)
        self.assertNotEqual(kx.fitted_learned_state,ke.fitted_learned_state)

    # I5 ----------------------------------------------------------------
    def test_I5_target_instrument_survives_a_shared_identity(self):
        kx,_=self._key(instrument="XAUUSD",**self.AGNOSTIC)
        store=verified_store([self._row(kx,"XAUUSD")])
        r=self._lookup(store,"EURUSD",**self.AGNOSTIC)
        self.assertEqual(r.outcome,LookupOutcome.EXACT_CANONICAL_IDENTITY)
        # The canonical row carries its first binding; the REQUEST's target is
        # reported separately and is never replaced by it.
        self.assertEqual(r.exact_match.instrument,"XAUUSD")
        self.assertEqual(r.bound_instrument,"EURUSD")

    def test_I5b_claim_lineage_retains_the_bound_instrument(self):
        store=verified_store()
        r=self._lookup(store,"EURUSD",request_id="REQ-EU",**self.AGNOSTIC)
        self.assertIsNotNone(r.absent_claim_token,r.errors)
        self.assertEqual(store.claims[0].provenance.bound_instrument,"EURUSD")
        self.assertEqual(r.bound_instrument,"EURUSD")
        # Shared identity => one construction at a time across bindings.
        r2=self._lookup(store,"XAUUSD",request_id="REQ-XAU",**self.AGNOSTIC)
        self.assertIsNone(r2.absent_claim_token)
        self.assertTrue(any("PENDING_CLAIM_EXISTS" in e for e in r2.errors),r2.errors)
        self.assertEqual(r2.bound_instrument,"XAUUSD")

    def test_I6_other_identity_controls_are_not_weakened(self):
        """Source/provider, timeframe, causal/time, normalization and definition
        still split identity for an instrument-AGNOSTIC definition."""
        base,_=self._key(instrument="XAUUSD",**self.AGNOSTIC)
        for field,value in (("source_provider","OTHER"),("timeframe","H4"),
                            ("causal_time_semantics","OTHER-CLOCK"),
                            ("declared_normalization","ZSCORE"),
                            ("normalized_definition_graph","SUB(C[t],C[t-1])"),
                            ("price_basis","ASK")):
            other,_=self._key(instrument="EURUSD",**dict(self.AGNOSTIC,**{field:value}))
            self.assertNotEqual(base.composite,other.composite,field)

    def test_I3b_bound_instrument_must_stay_declared(self):
        """Even when the instrument is NOT identity content (AGNOSTIC), the
        bound instrument is a required declared dimension: it is never dropped
        from the request just because it does not split identity."""
        for mode in (self.AGNOSTIC,self.SPECIFIC):
            payload=self._content(**mode)
            payload.pop("instrument")
            key,errors=build_content_identity_key(payload)
            self.assertIsNone(key)
            self.assertIn("CONTENT_DIMENSION_MISSING:instrument",errors)

    def test_I7_content_key_algorithm_version_was_bumped(self):
        from tracker_identity import CONTENT_KEY_ALGORITHM_ID
        self.assertEqual(CONTENT_KEY_ALGORITHM_ID,"SALIX-CONTENT-IDENTITY-KEY-V2")

class ManagerReAttackM1R(unittest.TestCase):
    """M-1R: the registry CONTAINER must be immutable, not only its entries."""

    def test_A1_former_backing_map_route_is_gone(self):
        """The exported registry was a VIEW over a module-level `_BUILT` dict,
        so mutating that dict was reflected straight through. REVIEW_CODER
        executed exactly that. No module-level backing dict now survives."""
        from tracker_identity import policy_registry, normalizer_registry
        for module in (policy_registry,normalizer_registry):
            self.assertFalse(hasattr(module,"_BUILT"),module.__name__)
            leaked=[name for name,value in vars(module).items()
                    if isinstance(value,dict) and not name.startswith("__")]
            self.assertEqual(leaked,[],
                module.__name__+" still exposes a mutable dict: "+str(leaked))

    def test_A2_A3_A4_normalizer_registry_is_equally_frozen(self):
        from tracker_identity.normalizer_registry import (
            GOVERNED_NORMALIZERS, GovernedNormalizerEntry,
        )
        rogue=GovernedNormalizerEntry("tracker.identity.normalizer","1",
                                      ("EXACT_STRUCTURAL_IDENTITY",))
        with self.assertRaises(TypeError):
            GOVERNED_NORMALIZERS[rogue.key]=rogue          # replacement
        with self.assertRaises(TypeError):
            GOVERNED_NORMALIZERS[("rogue","1")]=rogue      # insertion
        with self.assertRaises(TypeError):
            del GOVERNED_NORMALIZERS[("tracker.identity.normalizer","1")]

    def test_A5_entry_integrity_is_revalidated_not_assumed(self):
        """Membership is not trust: the resolver recomputes entry integrity, so
        an entry that reached the registry without satisfying the mandatory
        rules would still be refused at use time."""
        from tracker_identity import policy_registry as pr
        rogue=pr.GovernedSearchPolicyEntry(
            policy_id="tracker.identity.search",version="1",
            required_scopes=("current_active",),searched_scopes=("current_active",))
        self.assertTrue(any("MISSING_MANDATORY" in x for x in rogue.registry_errors()))
        # Simulate an entry having got in, via a private local map the resolver
        # consults; the integrity recheck must still refuse it.
        entry,errors=pr._entry_or_errors("tracker.identity.search","1")
        self.assertEqual(errors,())          # the real entry is sound
        self.assertEqual(entry.registry_errors(),())
        # A normalizer entry claiming an unsupported equivalence class is
        # refused by its own integrity rules, so it can never be registered.
        from tracker_identity.normalizer_registry import GovernedNormalizerEntry
        widened=GovernedNormalizerEntry("tracker.identity.normalizer","2",
                                        ("ALGEBRAIC_EQUIVALENCE",))
        self.assertTrue(any("UNSUPPORTED_EQUIVALENCE_CLASS" in x
                            for x in widened.registry_errors()),
                        widened.registry_errors())

    def test_A6_integrity_recheck_defeats_even_a_gc_route_mutation(self):
        """Defence in depth, measured rather than asserted by scope.

        A read-only mapping still holds a backing dict that gc can reach. That
        is outside the stated threat model, but the control must not DEPEND on
        it being unreachable: with the rogue entry installed by that route, the
        resolver's integrity recheck still refuses it and no claim is issued.
        """
        import gc
        from tracker_identity import policy_registry as pr
        registry=pr.GOVERNED_SEARCH_POLICIES
        backing=[r for r in gc.get_referents(registry) if isinstance(r,dict)]
        if not backing:
            self.skipTest("no gc-reachable backing map on this interpreter")
        backing=backing[0]
        key=("tracker.identity.search","1")
        saved=backing[key]
        rogue=pr.GovernedSearchPolicyEntry(
            policy_id="tracker.identity.search",version="1",
            required_scopes=("current_active",),searched_scopes=("current_active",))
        try:
            backing[key]=rogue
            self.assertIs(registry[key],rogue)     # the mutation did land
            narrow=ungoverned_policy(policy_id="tracker.identity.search",version="1",
                                     required=("current_active",),
                                     searched=("current_active",))
            errors=resolve_governed_search_policy(narrow)
            self.assertTrue(any("ENTRY_INTEGRITY_FAILED" in e for e in errors),errors)
            store=verified_store()
            result=identity_lookup(store=store,subject=pre_id_subject(),
                                   request_id="REQ-GC",search_policy=narrow,
                                   normalizer=governed_normalizer())
            self.assertEqual(result.outcome,LookupOutcome.INCOMPLETE_LOOKUP)
            self.assertIsNone(result.absent_claim_token)
            self.assertEqual(store.claims,[])
        finally:
            backing[key]=saved
        self.assertIs(registry[key],saved)

    def test_R7_assignment_to_registry_fails(self):
        from tracker_identity.policy_registry import (
            GOVERNED_SEARCH_POLICIES, GovernedSearchPolicyEntry,
        )
        rogue=GovernedSearchPolicyEntry(
            policy_id="tracker.identity.search",version="1",
            required_scopes=("current_active",),searched_scopes=("current_active",))
        with self.assertRaises(TypeError):
            GOVERNED_SEARCH_POLICIES[("tracker.identity.search","1")]=rogue

    def test_R8_deletion_from_registry_fails(self):
        from tracker_identity.policy_registry import GOVERNED_SEARCH_POLICIES
        with self.assertRaises(TypeError):
            del GOVERNED_SEARCH_POLICIES[("tracker.identity.search","1")]

    def test_R9_insertion_of_rogue_version_fails(self):
        from tracker_identity.policy_registry import (
            GOVERNED_SEARCH_POLICIES, GovernedSearchPolicyEntry,
        )
        rogue=GovernedSearchPolicyEntry(
            policy_id="tracker.identity.search",version="99",
            required_scopes=MANDATORY_DUPLICATE_CONTROL_SCOPES,
            searched_scopes=MANDATORY_DUPLICATE_CONTROL_SCOPES)
        with self.assertRaises(TypeError):
            GOVERNED_SEARCH_POLICIES[rogue.key]=rogue
        self.assertNotIn(("tracker.identity.search","99"),GOVERNED_SEARCH_POLICIES)
        spoof=ungoverned_policy(policy_id="tracker.identity.search",version="99")
        self.assertIn("SEARCH_POLICY_NOT_GOVERNED:tracker.identity.search@99",
                      resolve_governed_search_policy(spoof))

    def test_R10_governed_v1_remains_usable(self):
        gov=governed_search_policy()
        self.assertEqual(resolve_governed_search_policy(gov),())
        result=identity_lookup(store=verified_store(),subject=pre_id_subject(),
                               request_id="REQ-R10",search_policy=gov,
                               normalizer=normalizer())
        self.assertEqual(result.outcome,LookupOutcome.ABSENT_EXACT_STRUCTURAL_IN_ERA_1)
        self.assertTrue(result.lookup_complete)

    def test_R11_mandatory_scope_defence_survives_a_rogue_entry(self):
        """Even a rogue entry constructed before freezing cannot authorise
        dropping a mandatory scope: the check does not consult the entry."""
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
