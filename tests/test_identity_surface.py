import unittest
from datetime import datetime, timezone

from tracker_identity import (
    CanonicalIdentityStore,
    FeatureIdentity,
    LookupOutcome,
    NormalizerSpec,
    SearchPolicy,
    identity_lookup,
    stale_state_sweep,
)

REQUIRED_SCOPES = (
    "current_active",
    "active_on_demand",
    "validation",
    "experimental_unclassified",
    "quarantined",
    "dormant",
    "suppressed",
    "deprecated",
    "retired",
    "rejected_invalid",
    "historical_prior_version",
    "canonical_survivor_discarded",
    "pending_claimed_in_flight",
)

def complete_policy():
    return SearchPolicy(
        policy_id="tracker.identity.search",
        version="1",
        policy_hash="policyhash-v1",
        required_scopes=REQUIRED_SCOPES,
        searched_scopes=REQUIRED_SCOPES,
        scope_exclusions={},
    )

def normalizer():
    return NormalizerSpec(
        normalizer_id="tracker.identity.normalizer",
        version="1",
        normalizer_hash="normalizerhash-v1",
        equivalence_classes=("EXACT_STRUCTURAL_IDENTITY",),
    )

def subject(version="1", instrument="EURUSD"):
    return {
        "feature_id":"returns.1bar",
        "feature_version":version,
        "definition_hash":"abc",
        "graph_hash":"def",
        "instrument":instrument,
        "timeframe":"H1",
    }

def record(version="1", *, current=True, lifecycle="CURRENT", instrument="EURUSD", scope="current_active"):
    return FeatureIdentity(
        feature_id="returns.1bar",
        feature_version=version,
        definition_hash="abc",
        graph_hash="def",
        lifecycle_state=lifecycle,
        is_current=current,
        scope=scope,
        instrument=instrument,
        timeframe="H1",
    )

class IdentitySurfaceTests(unittest.TestCase):
    def test_empty_store_complete_lookup_returns_absent(self):
        result=identity_lookup(
            store=CanonicalIdentityStore(),
            subject=subject(),
            request_id="REQ-EMPTY",
            search_policy=complete_policy(),
            normalizer=normalizer(),
            now=datetime(2026,9,19,tzinfo=timezone.utc),
        )
        self.assertTrue(result.lookup_complete)
        self.assertEqual(result.outcome,LookupOutcome.ABSENT)
        self.assertIsNotNone(result.absent_claim_token)
        self.assertFalse(result.absent_claim_token.authorizes_construction)

    def test_exact_match(self):
        result=identity_lookup(
            store=CanonicalIdentityStore([record()]),
            subject=subject(),
            request_id="REQ-EXACT",
            search_policy=complete_policy(),
            normalizer=normalizer(),
        )
        self.assertTrue(result.lookup_complete)
        self.assertEqual(result.outcome,LookupOutcome.EXACT_CANONICAL_IDENTITY)

    def test_near_match_requires_review(self):
        result=identity_lookup(
            store=CanonicalIdentityStore([record(version="2")]),
            subject=subject(version="1"),
            request_id="REQ-NEAR",
            search_policy=complete_policy(),
            normalizer=normalizer(),
        )
        self.assertTrue(result.lookup_complete)
        self.assertEqual(result.outcome,LookupOutcome.NEAR_MATCH)
        self.assertEqual(result.pending_collision_result,"REVIEW_REQUIRED")

    def test_incomplete_scope_cannot_emit_absent(self):
        p=complete_policy()
        incomplete=SearchPolicy(
            policy_id=p.policy_id,
            version=p.version,
            policy_hash=p.policy_hash,
            required_scopes=p.required_scopes,
            searched_scopes=p.required_scopes[:-1],
            scope_exclusions={},
        )
        result=identity_lookup(
            store=CanonicalIdentityStore(),
            subject=subject(),
            request_id="REQ-INCOMPLETE",
            search_policy=incomplete,
            normalizer=normalizer(),
        )
        self.assertFalse(result.lookup_complete)
        self.assertEqual(result.outcome,LookupOutcome.INCOMPLETE_LOOKUP)
        self.assertIsNone(result.absent_claim_token)

    def test_gold_identity_is_not_eurusd_exact_match(self):
        result=identity_lookup(
            store=CanonicalIdentityStore([record(instrument="XAUUSD")]),
            subject=subject(instrument="EURUSD"),
            request_id="REQ-INSTRUMENT",
            search_policy=complete_policy(),
            normalizer=normalizer(),
        )
        self.assertTrue(result.lookup_complete)
        self.assertEqual(result.outcome,LookupOutcome.NEAR_MATCH)

    def test_stale_superseded_current_fails_sweep(self):
        sweep=stale_state_sweep(
            store=CanonicalIdentityStore([record(current=True,lifecycle="SUPERSEDED")]),
            search_policy=complete_policy(),
            normalizer=normalizer(),
        )
        self.assertFalse(sweep.clean)
        self.assertTrue(any("NONCURRENT_LIFECYCLE_MARKED_CURRENT" in x for x in sweep.defects))

    def test_dangling_dependency_fails_sweep(self):
        bad=FeatureIdentity(
            feature_id="feature.a",
            feature_version="1",
            definition_hash="1",
            graph_hash="1",
            lifecycle_state="CURRENT",
            is_current=True,
            scope="current_active",
            dependencies=("missing.feature",),
        )
        sweep=stale_state_sweep(
            store=CanonicalIdentityStore([bad]),
            search_policy=complete_policy(),
            normalizer=normalizer(),
        )
        self.assertFalse(sweep.clean)
        self.assertTrue(any("DANGLING_DEPENDENCY" in x for x in sweep.defects))

    def test_test_fixture_in_live_scope_fails_sweep(self):
        fixture=FeatureIdentity(
            feature_id="fixture.test.feature",
            feature_version="1",
            definition_hash="1",
            graph_hash="1",
            lifecycle_state="CURRENT",
            is_current=True,
            scope="current_active",
        )
        sweep=stale_state_sweep(
            store=CanonicalIdentityStore([fixture]),
            search_policy=complete_policy(),
            normalizer=normalizer(),
        )
        self.assertFalse(sweep.clean)
        self.assertTrue(any("TEST_OR_TEMP_IDENTITY_IN_LIVE_SCOPE" in x for x in sweep.defects))

    def test_alias_collision_fails_sweep(self):
        a=FeatureIdentity("feature.a","1","1","1","CURRENT",True,"current_active",aliases=("shared.alias",))
        b=FeatureIdentity("feature.b","1","2","2","CURRENT",True,"current_active",aliases=("shared.alias",))
        sweep=stale_state_sweep(
            store=CanonicalIdentityStore([a,b]),
            search_policy=complete_policy(),
            normalizer=normalizer(),
        )
        self.assertFalse(sweep.clean)
        self.assertTrue(any("CURRENT_ALIAS_COLLISION" in x for x in sweep.defects))

if __name__=="__main__":
    unittest.main()
