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
    FeatureIdentity,
    MANDATORY_DUPLICATE_CONTROL_SCOPES,
    NormalizerSpec,
    SearchPolicy,
    build_content_identity_key,
    governed_normalizer,
    governed_search_policy,
    identity_lookup,
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
    # Normalizer authority is governed now: identity_lookup resolves it against
    # the Tracker-owned registry, so an invented id no longer binds.
    return governed_normalizer()


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


def content_key(**overrides):
    payload = dict(CONTENT)
    payload.update(overrides)
    key, errors = build_content_identity_key(payload)
    assert not errors, errors
    return key


def governed_lookup(store, request_id, **content_overrides):
    """Run the governed lookup. reserve_claim() no longer mints authority on
    demand, so this is the only way a test can obtain a real claim."""
    for sc in MANDATORY_DUPLICATE_CONTROL_SCOPES:
        store.declare_scope(sc, "EMPTY_VERIFIED")
    payload = dict(CONTENT)
    payload.update(content_overrides)
    subject = {"subject_mode": "PRE_ID", "feature_id": "", "feature_version": "",
               "definition_hash": "", "graph_hash": "", "instrument": "XAUUSD",
               "timeframe": "H1", "lookup_era_scope": "ERA_1_ONLY",
               "candidate_content": payload}
    return identity_lookup(store=store, subject=subject, request_id=request_id,
                           search_policy=governed_search_policy(),
                           normalizer=normalizer())


def governed_claim(store, request_id, **content_overrides):
    result = governed_lookup(store, request_id, **content_overrides)
    assert result.absent_claim_token is not None, result.errors
    return result


def imported_row(key, feature_id="gold.logret.other"):
    """A content identity introduced by the governed IMPORT path.

    import_identity_content() writes through store.extend(), not through
    commit_registration(), so it is a legitimate way for an identity to appear
    between a claim being issued and that claim being presented.
    """
    return FeatureIdentity(
        feature_id=feature_id, feature_version="1",
        definition_hash="imported-d", graph_hash="imported-g",
        lifecycle_state="CURRENT", is_current=True, scope="current_active",
        era_id="ERA_1",
        content_key_composite=key.composite,
        content_key_definition=key.definition_semantics,
        content_key_causal_time=key.causal_time,
        content_key_provenance=key.provenance_source,
        content_key_scope=key.scope_eligibility,
        content_key_fitted=key.fitted_learned_state,
        content_key_algorithm_id=key.algorithm_id,
    )


class RegistrationAtomicity(unittest.TestCase):

    def test_A_stalled_worker_with_expired_claim_cannot_register(self):
        """A validates, stalls, claim expires, B registers, A resumes -> A FAILS."""
        store = CanonicalIdentityStore()
        key = content_key()
        clock = FrozenClock(datetime.now(timezone.utc))
        store._clock = clock
        governed_claim(store, "REQ-A")
        # A's claim expires; B takes the key.
        clock.advance(10_000)
        governed_claim(store, "REQ-B")
        b = intake(store, candidate("gold.logret.b", claim_request_id="REQ-B"))
        a = intake(store, candidate("gold.logret.a", claim_request_id="REQ-A"))

        # Neither registers: registration is fail-closed (C-1R). What this test
        # still proves is that they fail for DIFFERENT reasons — B reaches the
        # terminal authority gate, A dies earlier on its own expiry. The ABA
        # control is therefore still exercised, not masked.
        self.assertFalse(b.accepted)
        self.assertTrue(any("CLAIM_NOT_CONSTRUCTION_AUTHORIZED" in e for e in b.errors), b.errors)
        self.assertFalse(a.accepted)
        self.assertTrue(any("CLAIM_NOT_ACTIVE" in e for e in a.errors), a.errors)
        self.assertEqual(store.all(), ())

    def test_B_two_workers_same_content_key_cannot_both_register(self):
        store = CanonicalIdentityStore()
        first = governed_claim(store, "REQ-1")
        second = governed_lookup(store, "REQ-2")
        self.assertIsNotNone(first.absent_claim_token)
        # The second governed lookup on the same content key gets NO claim.
        self.assertIsNone(second.absent_claim_token)
        self.assertTrue(any("PENDING_CLAIM_EXISTS" in e for e in second.errors),
                        second.errors)
        self.assertEqual(len([c for c in store.claims if c.state == "ACTIVE"]), 1)

        one = intake(store, candidate("gold.logret.one", claim_request_id="REQ-1"))
        two = intake(store, candidate("gold.logret.two", claim_request_id="REQ-2"))
        self.assertFalse(one.accepted)
        self.assertTrue(any("CLAIM_NOT_CONSTRUCTION_AUTHORIZED" in e for e in one.errors),
                        one.errors)
        self.assertFalse(two.accepted)
        self.assertTrue(any("CLAIM_NOT_FOUND" in e for e in two.errors), two.errors)
        self.assertEqual(store.all(), ())

    def test_C_identity_appearing_after_claim_blocks_stale_claimant(self):
        """Content identity registered by another path between claim and intake."""
        store = CanonicalIdentityStore()
        key = content_key()
        governed_claim(store, "REQ-STALE")
        # The same content identity arrives by the governed import path while
        # this worker holds its claim. It cannot arrive by a second intake:
        # only one active claim per content key can exist, which is the point.
        store.add(imported_row(key))

        stale = intake(store, candidate("gold.logret.stale", claim_request_id="REQ-STALE"))
        self.assertFalse(stale.accepted)
        # Fires BEFORE the terminal authority gate, so the duplicate control
        # remains independently observable rather than masked by it.
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
        governed_claim(store, "REQ-OLD")
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
        governed_claim(store, "REQ-SC")
        issued_at = clock.at
        clock.advance(10_000)
        # A plausible side channel: an old timestamp parked on the store.
        store._injected_now = issued_at.isoformat()
        ok, error = store.commit_registration(
            identity=object(), creation=object(),
            content_key_composite=key.composite, request_id="REQ-SC")
        self.assertFalse(ok)
        self.assertTrue(error.startswith("CLAIM_NOT_ACTIVE"), error)

    def test_E_fail_closed_registration_consumes_no_claim(self):
        """Was: test_E_success_consumes_exactly_its_own_claim.

        Claim consumption ON SUCCESS is UNREACHABLE while registration is
        fail-closed (C-1R): no code path grants construction authority. What
        remains verifiable is the converse, and it is the safety-relevant half
        — a registration refused at the authority gate consumes NOTHING, and
        leaves an unrelated worker's claim untouched.
        """
        store = CanonicalIdentityStore()
        governed_claim(store, "REQ-MINE")
        governed_claim(store, "REQ-OTHER", price_basis="ASK")
        result = intake(store, candidate(claim_request_id="REQ-MINE"))
        self.assertFalse(result.accepted)
        self.assertTrue(any("CLAIM_NOT_CONSTRUCTION_AUTHORIZED" in e for e in result.errors),
                        result.errors)
        states = {c.request_id: c.state for c in store.claims}
        self.assertEqual(states["REQ-MINE"], "ACTIVE")
        self.assertEqual(states["REQ-OTHER"], "ACTIVE")
        self.assertEqual(store.all(), ())

    def test_F_failed_intake_does_not_consume_another_workers_claim(self):
        store = CanonicalIdentityStore()
        key = content_key()
        governed_claim(store, "REQ-HOLDER")
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
        # End-to-end double registration is UNREACHABLE while registration is
        # fail-closed, so the first identity is placed by the governed import
        # path instead. The canonical-key control itself is what this test is
        # about, and it remains fully exercisable.
        # Unrelated CONTENT (different definition graph), so it does not route
        # the claimant's lookup to related-version review — but the SAME
        # canonical key, which is what must refuse the write.
        existing = imported_row(
            content_key(normalized_definition_graph="SUB(LN(C[t]),LN(C[t-1]))"),
            feature_id="gold.logret.dup")
        store.add(existing)
        governed_claim(store, "REQ-DUP")

        # A VALID active, fully provenance-bound claim, presented against a
        # canonical key that already exists. The canonical-key check must be
        # what refuses this — it fires before the terminal authority gate.
        ok, error = store.commit_registration(
            identity=existing, creation=object(),
            content_key_composite=content_key().composite, request_id="REQ-DUP")
        self.assertFalse(ok)
        self.assertTrue(error.startswith("CANONICAL_KEY_ALREADY_REGISTERED"), error)
        self.assertEqual(len(store.all()), 1)

    def test_claim_without_derivable_content_key_is_refused(self):
        store = CanonicalIdentityStore()
        result = intake(store, candidate(claim_request_id="REQ-NOKEY",
                                         price_basis=None))
        self.assertFalse(result.accepted)
        self.assertIn("CLAIM_PRESENTED_WITHOUT_CONTENT_KEY", result.errors)

    def test_intake_without_a_claim_is_refused(self):
        """C-1: ordinary canonical registration REQUIRES a valid active claim.

        Replaces test_intake_without_a_claim_still_works, which asserted the
        defect: claimless intake reached canonical registration and bypassed
        the lookup/claim gate entirely.
        """
        store = CanonicalIdentityStore()
        result = intake(store, candidate())
        self.assertFalse(result.accepted)
        self.assertIn("CLAIM_REQUEST_ID_REQUIRED", result.errors)
        self.assertEqual(store.all(), ())
        self.assertEqual(store.all_creation_records(), ())

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
