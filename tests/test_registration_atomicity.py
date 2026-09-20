"""End-to-end registration atomicity controls through safe_intake_built_identity.

Raised by Manager re-attack of M-TYPE1-PREID-2c6be3a: claim validation and
registry mutation were separable, which permits the stale-worker duplicate.
Controls A-G below exercise the whole intake path, not the store method in
isolation.
"""

import unittest
from datetime import datetime, timedelta, timezone

from tracker_identity import (
    BuiltIdentityCandidate,
    CanonicalEraBoundary,
    CanonicalIdentityStore,
    FeatureDefinitionRecord,
    NormalizerSpec,
    SearchPolicy,
    build_content_identity_key,
    safe_intake_built_identity,
)

CONTENT = {
    "normalized_definition_graph": "LN(DIV(C[t],C[t-1]))",
    "dependency_closure": (),  # empty but DECLARED; dangling dep ids fail the sweep
    "parameters": {"lookback_bars": 2},
    "declared_normalization": "NONE",
    "causal_time_semantics": "SALIX-XAUUSD-BROKER-UTC-TRANSITION-V1",
    "completion_semantics": "LAST_COMPLETED_BEFORE_T",
    "availability_class": "RECONSTRUCTED_NOT_OBSERVED",
    "source_provider": "COMPOSER",
    "price_basis": "BID",
    "data_vintage_mode": "CURRENT_RECOMPUTED",
    "instrument": "XAUUSD",
    "timeframe": "H1",
    "scope_universe": "XAUUSD/ERA_1",
    "fitted_state": "NONE",
}


class FrozenClock:
    """Store-owned injected clock. Production callers cannot supply time."""

    def __init__(self, at):
        self.at = at

    def __call__(self):
        return self.at

    def advance(self, seconds):
        self.at = self.at + timedelta(seconds=seconds)


def policy():
    p = SearchPolicy("safe-intake", "1", "", ("current_active",), ("current_active",), {})
    return SearchPolicy(p.policy_id, p.version, p.computed_hash(),
                        p.required_scopes, p.searched_scopes, p.scope_exclusions)


def normalizer():
    n = NormalizerSpec("safe-intake", "1", "", ("EXACT_STRUCTURAL_IDENTITY",))
    return NormalizerSpec(n.normalizer_id, n.version, n.computed_hash(), n.equivalence_classes)


def boundary():
    vals = dict(
        era_id="ERA_1", version="1", boundary_hash="",
        effective_ts="2026-09-19T20:47:37+10:00", predecessor_era_id="ERA_0",
        registry_id="SALIX-ERA1-REGISTRY", catalogue_id="SALIX-ERA1-FEATURE-CATALOGUE",
        source_universe_id="SALIX-ERA1-SOURCE-UNIVERSE-001",
        pre_era_content_default="UNRESOLVED_NON_IMPORTABLE",
        historical_gap_status="UNRESOLVED", historical_gap_owner="MANAGER",
        revisit_trigger="IF_ERA0_ARTIFACT_LOCATED_REVIEW_BEFORE_IMPORT",
        absent_proven=False, created_by="SALIX_MANAGER", approval_authority="OWNER",
        created_ts="2026-09-19T20:47:37+10:00",
    )
    x = CanonicalEraBoundary(**vals)
    vals["boundary_hash"] = x.computed_hash()
    return CanonicalEraBoundary(**vals)


def candidate(feature_id="gold.logret", claim_request_id=None, **changes):
    vals = dict(
        feature_id=feature_id, feature_version="1",
        definition_hash="", graph_hash="",
        semantic_definition="h1 log return", formula=CONTENT["normalized_definition_graph"],
        lifecycle_state="CURRENT", is_current=True, scope="current_active",
        aliases=(), dependencies=CONTENT["dependency_closure"],
        canonical_survivor=None, instrument="XAUUSD", timeframe="H1",
        source_provider="COMPOSER", lineage_ref="build:logret",
        creation_reason_ref="decision:approved-definition",
        created_by="SALIX_MANAGER", authority_ref="owner:era1-intake",
        creation_evidence_ref="evidence:definition-review",
        declared_normalization="NONE",
        causal_time_semantics=CONTENT["causal_time_semantics"],
        completion_semantics=CONTENT["completion_semantics"],
        availability_class=CONTENT["availability_class"],
        price_basis="BID", data_vintage_mode="CURRENT_RECOMPUTED",
        scope_universe="XAUUSD/ERA_1", parameters={"lookback_bars": 2},
        fitted_state="NONE", proxy_status="NOT_PROXY",
        claim_request_id=claim_request_id,
    )
    vals.update(changes)
    probe = BuiltIdentityCandidate(**vals)
    d = FeatureDefinitionRecord(probe.feature_id, probe.feature_version,
                                probe.semantic_definition, probe.formula,
                                probe.dependencies, "ERA_1", "", "",
                                probe.instrument, probe.timeframe)
    if not vals["definition_hash"]:
        vals["definition_hash"] = d.computed_definition_hash()
    if not vals["graph_hash"]:
        vals["graph_hash"] = d.computed_graph_hash()
    return BuiltIdentityCandidate(**vals)


def intake(store, cand):
    return safe_intake_built_identity(
        target_store=store, candidate=cand, era_boundary=boundary(),
        search_policy=policy(), normalizer=normalizer())


def content_key():
    key, errors = build_content_identity_key(CONTENT)
    assert not errors, errors
    return key


class RegistrationAtomicity(unittest.TestCase):

    def test_A_stalled_worker_with_expired_claim_cannot_register(self):
        """A validates, stalls, claim expires, B registers, A resumes -> A FAILS."""
        store = CanonicalIdentityStore()
        key = content_key()
        clock = FrozenClock(datetime.now(timezone.utc))
        store._clock = clock
        store.reserve_claim(content_key_composite=key.composite, request_id="REQ-A")
        # A's claim expires; B takes the key and registers first.
        clock.advance(10_000)
        store.reserve_claim(content_key_composite=key.composite, request_id="REQ-B")
        b = intake(store, candidate("gold.logret.b", claim_request_id="REQ-B"))
        self.assertTrue(b.accepted, b.errors)

        a = intake(store, candidate("gold.logret.a", claim_request_id="REQ-A"))
        self.assertFalse(a.accepted)
        self.assertTrue(any(e.startswith("REGISTRATION_REFUSED") for e in a.errors), a.errors)
        self.assertEqual(len([r for r in store.all() if r.is_current]), 1)

    def test_B_two_workers_same_content_key_cannot_both_register(self):
        store = CanonicalIdentityStore()
        key = content_key()
        first, err1 = store.reserve_claim(content_key_composite=key.composite,
                                          request_id="REQ-1")
        second, err2 = store.reserve_claim(content_key_composite=key.composite,
                                           request_id="REQ-2")
        self.assertIsNotNone(first)
        self.assertIsNone(second)
        self.assertTrue(err2.startswith("PENDING_CLAIM_EXISTS"))

        one = intake(store, candidate("gold.logret.one", claim_request_id="REQ-1"))
        two = intake(store, candidate("gold.logret.two", claim_request_id="REQ-2"))
        self.assertTrue(one.accepted, one.errors)
        self.assertFalse(two.accepted)
        self.assertEqual(len(store.all()), 1)

    def test_C_identity_appearing_after_claim_blocks_stale_claimant(self):
        """Content identity registered by another path between claim and intake."""
        store = CanonicalIdentityStore()
        key = content_key()
        store.reserve_claim(content_key_composite=key.composite, request_id="REQ-STALE")
        # Another worker registers the same content under a different name.
        other = intake(store, candidate("gold.logret.other"))
        self.assertTrue(other.accepted, other.errors)

        stale = intake(store, candidate("gold.logret.stale", claim_request_id="REQ-STALE"))
        self.assertFalse(stale.accepted)
        self.assertTrue(any("IDENTITY_APPEARED_SINCE_CLAIM" in e for e in stale.errors),
                        stale.errors)

    def test_D_T1_T3_expired_claim_cannot_be_revived_by_a_supplied_time(self):
        """Claim stays stored ACTIVE, wall clock passes, registration refuses.

        The claim is NOT pre-transitioned to EXPIRED. Expiry is discovered by
        the store's own transaction time, and there is no public argument a
        caller could use to supply a past time instead.
        """
        store = CanonicalIdentityStore()
        key = content_key()
        clock = FrozenClock(datetime.now(timezone.utc))
        store._clock = clock
        store.reserve_claim(content_key_composite=key.composite, request_id="REQ-OLD")
        self.assertEqual(store.claims[0].state, "ACTIVE")

        clock.advance(10_000)   # real time passes; record still says ACTIVE
        self.assertEqual(store.claims[0].state, "ACTIVE")

        ok, error = store.commit_registration(
            identity=object(), creation=object(),
            content_key_composite=key.composite, request_id="REQ-OLD")
        self.assertFalse(ok)
        self.assertTrue(error.startswith("CLAIM_NOT_ACTIVE"), error)

        import inspect
        self.assertNotIn("now", inspect.signature(
            CanonicalIdentityStore.commit_registration).parameters)

    def test_T3_no_side_channel_can_override_the_store_transaction_time(self):
        """Only the store's own clock may decide expiry.

        A stray attribute on the store must not be consulted. This pins the
        rule that the transaction time has exactly one source, so a mutant
        that reintroduces any caller-reachable time input is detected.
        """
        store = CanonicalIdentityStore()
        key = content_key()
        clock = FrozenClock(datetime.now(timezone.utc))
        store._clock = clock
        store.reserve_claim(content_key_composite=key.composite, request_id="REQ-SC")
        issued_at = clock.at
        clock.advance(10_000)
        # A plausible side channel: an old timestamp parked on the store.
        store._injected_now = issued_at.isoformat()
        ok, error = store.commit_registration(
            identity=object(), creation=object(),
            content_key_composite=key.composite, request_id="REQ-SC")
        self.assertFalse(ok)
        self.assertTrue(error.startswith("CLAIM_NOT_ACTIVE"), error)

    def test_E_success_consumes_exactly_its_own_claim(self):
        store = CanonicalIdentityStore()
        key = content_key()
        store.reserve_claim(content_key_composite=key.composite, request_id="REQ-MINE")
        store.reserve_claim(content_key_composite="unrelated-key", request_id="REQ-OTHER")
        result = intake(store, candidate(claim_request_id="REQ-MINE"))
        self.assertTrue(result.accepted, result.errors)
        states = {c.request_id: c.state for c in store.claims}
        self.assertEqual(states["REQ-MINE"], "RELEASED")
        self.assertEqual(states["REQ-OTHER"], "ACTIVE")

    def test_F_failed_intake_does_not_consume_another_workers_claim(self):
        store = CanonicalIdentityStore()
        key = content_key()
        store.reserve_claim(content_key_composite=key.composite, request_id="REQ-HOLDER")
        # A different request presents no valid claim and must fail without
        # touching the holder's claim.
        result = intake(store, candidate("gold.logret.x", claim_request_id="REQ-GHOST"))
        self.assertFalse(result.accepted)
        self.assertEqual(store.claims[0].request_id, "REQ-HOLDER")
        self.assertEqual(store.claims[0].state, "ACTIVE")
        self.assertEqual(len(store.all()), 0)

    def test_same_canonical_key_cannot_be_registered_twice(self):
        """Refused end to end, and refused again at the atomic boundary.

        The stale-state sweep catches this first, so the canonical-key check
        inside commit_registration is defence in depth. Both are asserted: the
        end-to-end refusal, and the inner check in isolation.
        """
        store = CanonicalIdentityStore()
        first = intake(store, candidate("gold.logret.dup"))
        self.assertTrue(first.accepted, first.errors)

        second = intake(store, candidate("gold.logret.dup", price_basis="ASK"))
        self.assertFalse(second.accepted)
        self.assertEqual(len(store.all()), 1)

        # Inner check in isolation: same canonical key, no claim presented.
        ok, error = store.commit_registration(
            identity=first.identity, creation=object(),
            content_key_composite=None, request_id=None)
        self.assertFalse(ok)
        self.assertTrue(error.startswith("CANONICAL_KEY_ALREADY_REGISTERED"), error)

    def test_claim_without_derivable_content_key_is_refused(self):
        store = CanonicalIdentityStore()
        result = intake(store, candidate(claim_request_id="REQ-NOKEY",
                                         price_basis=None))
        self.assertFalse(result.accepted)
        self.assertIn("CLAIM_PRESENTED_WITHOUT_CONTENT_KEY", result.errors)

    def test_intake_without_a_claim_still_works(self):
        """Claim presentation is optional; governed legacy intake is unchanged."""
        store = CanonicalIdentityStore()
        result = intake(store, candidate())
        self.assertTrue(result.accepted, result.errors)

    def test_lock_order_is_total_no_claim_lock_then_transition_lock(self):
        """G: lock order proven by inspection — _transition_lock always outer.

        A deadlock needs two paths acquiring the pair in opposite orders. This
        asserts no source path acquires _claim_lock and then _transition_lock.
        """
        import inspect
        from tracker_identity import store as store_module
        src = inspect.getsource(store_module)
        claim_first = src.find("with self._claim_lock")
        while claim_first != -1:
            tail = src[claim_first:claim_first + 1200]
            self.assertNotIn("with self._transition_lock", tail,
                             "found _claim_lock acquired before _transition_lock")
            claim_first = src.find("with self._claim_lock", claim_first + 1)


if __name__ == "__main__":
    unittest.main()
