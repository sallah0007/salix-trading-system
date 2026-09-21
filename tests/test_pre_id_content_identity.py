"""Negative controls for Type-1 pre-ID content identity and atomic claims.

Commission: SALIX CODER IMPLEMENTATION COMMISSION — TYPE-1 PRE-ID CONTENT
IDENTITY / ATOMIC CLAIMS (Drive 1sRkk6tuIWF52Uhx_gXbqd7ZTj9O1NY1M25rdbatuZOQ).

Every test here corresponds to a lettered negative control A-R. Each
load-bearing protection has been confirmed to fail when the protection is
removed; mutation evidence is reported in the Coder return.
"""

import unittest
from datetime import datetime, timedelta, timezone

from tracker_identity import (
    CONTENT_KEY_ALGORITHM_ID,
    CanonicalIdentityStore,
    FeatureDefinitionRecord,
    FeatureIdentity,
    LookupOutcome,
    NormalizerSpec,
    SearchPolicy,
    build_content_identity_key,
    composer_boundary_outcome,
    identity_lookup,
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



REQUIRED_SCOPES = (
    "current_active", "active_on_demand", "validation", "experimental_unclassified",
    "quarantined", "dormant", "suppressed", "deprecated", "retired", "rejected_invalid",
    "historical_prior_version", "canonical_survivor_discarded", "pending_claimed_in_flight",
)

GRAPH_A = "LN(DIV(H1_CLOSE[t],H1_CLOSE[PREV_VERIFIED_H1_ROW]))"
GRAPH_B = "SUB(LN(H1_CLOSE[t]),LN(H1_CLOSE[PREV_VERIFIED_H1_ROW]))"


def policy():
    p = SearchPolicy("tracker.identity.search", "1", "", REQUIRED_SCOPES, REQUIRED_SCOPES, {})
    return SearchPolicy(p.policy_id, p.version, p.computed_hash(),
                        p.required_scopes, p.searched_scopes, p.scope_exclusions)


def normalizer():
    n = NormalizerSpec("tracker.identity.normalizer", "1", "", ("EXACT_STRUCTURAL_IDENTITY",))
    return NormalizerSpec(n.normalizer_id, n.version, n.computed_hash(), n.equivalence_classes)


def content(graph=GRAPH_A, deps=("xauusd.h1.close",), instrument="XAUUSD",
            timeframe="H1", provider="ICMARKETSAU-LIVE-V1", price_basis="BID",
            vintage="CURRENT_RECOMPUTED", fitted="NONE", params=None):
    return {
        "normalized_definition_graph": graph,
        "dependency_closure": deps,
        "parameters": params if params is not None else {"lookback_bars": 2},
        "declared_normalization": "NONE",
        "causal_time_semantics": "SALIX-XAUUSD-BROKER-UTC-TRANSITION-V1",
        "completion_semantics": "LAST_COMPLETED_BEFORE_T",
        "availability_class": "RECONSTRUCTED_NOT_OBSERVED",
        "source_provider": provider,
        "price_basis": price_basis,
        "data_vintage_mode": vintage,
        "instrument": instrument,
        "timeframe": timeframe,
        "scope_universe": "XAUUSD/ERA_1",
        "fitted_state": fitted,
        "instrument_applicability": "INSTRUMENT_SPECIFIC",
    }


def verified_store(*rows):
    store = CanonicalIdentityStore()
    for sc in REQUIRED_SCOPES:
        store.declare_scope(sc, "EMPTY_VERIFIED")
    for r in rows:
        seed_fixture(store,[r])
    return store


def registered(feature_id, payload, *, is_current=True, scope="current_active",
               lifecycle="CURRENT", proxy=None, version="1"):
    key, errors = build_content_identity_key(payload)
    assert not errors, errors
    return FeatureIdentity(
        feature_id, version, "legacy-definition-hash", "legacy-graph-hash",
        lifecycle, is_current, scope, "ERA_1",
        instrument=payload["instrument"], timeframe=payload["timeframe"],
        proxy_status=proxy,
        content_key_composite=key.composite,
        content_key_definition=key.definition_semantics,
        content_key_causal_time=key.causal_time,
        content_key_provenance=key.provenance_source,
        content_key_scope=key.scope_eligibility,
        content_key_fitted=key.fitted_learned_state,
        content_key_algorithm_id=CONTENT_KEY_ALGORITHM_ID,
    )


def pre_id(payload=None, **extra):
    s = {
        "subject_mode": "PRE_ID",
        "feature_id": "", "feature_version": "",
        "definition_hash": "", "graph_hash": "",
        "instrument": "XAUUSD", "timeframe": "H1",
        "lookup_era_scope": "ERA_1_ONLY",
        "candidate_content": payload if payload is not None else content(),
    }
    s.update(extra)
    return s


class FrozenClock:
    """Store-owned injected clock. Production callers cannot supply time."""

    def __init__(self, at):
        self.at = at

    def __call__(self):
        return self.at

    def advance(self, seconds):
        self.at = self.at + timedelta(seconds=seconds)


def install_test_clock(testcase, clock):
    """TEST-ONLY time control, by code replacement.

    Replaces the store module's internal wall-clock SOURCE with `clock` for the
    duration of one test, using unittest.mock, and restores it afterwards.
    Production stores have no clock field, constructor argument, flag or
    environment variable: time can only be steered by instrumenting code, which
    is test-harness behaviour, not a production data or API surface.
    """
    from unittest import mock
    from tracker_identity import store as store_module
    patcher = mock.patch.object(store_module, "_wall_now", clock)
    patcher.start()
    testcase.addCleanup(patcher.stop)


def run(store, subject, request_id="REQ", now=None):
    return identity_lookup(store=store, subject=subject, request_id=request_id,
                           search_policy=policy(), normalizer=normalizer(), now=now)


class ContentKeyDerivation(unittest.TestCase):
    def test_H_partial_content_produces_no_key(self):
        payload = content()
        payload.pop("price_basis")
        key, errors = build_content_identity_key(payload)
        self.assertIsNone(key)
        self.assertIn("CONTENT_DIMENSION_MISSING:price_basis", errors)

    def test_missing_is_not_none_for_fitted_state(self):
        payload = content()
        payload.pop("fitted_state")
        key, errors = build_content_identity_key(payload)
        self.assertIsNone(key)
        self.assertIn("CONTENT_DIMENSION_MISSING:fitted_state", errors)

    def test_identity_fields_rejected_from_content(self):
        payload = content()
        payload["feature_id"] = "gold.fc.001"
        _, errors = build_content_identity_key(payload)
        self.assertIn("CONTENT_IDENTITY_CONTAMINATION:feature_id", errors)

    def test_L_attempt_id_only_difference_does_not_split_content(self):
        payload = content()
        payload["parameters"] = {"lookback_bars": 2, "research_attempt_id": "ATT-19"}
        _, errors = build_content_identity_key(payload)
        self.assertIn("CONTENT_PROCESS_PROVENANCE_REJECTED:research_attempt_id", errors)
        clean_a, _ = build_content_identity_key(content())
        clean_b, _ = build_content_identity_key(content())
        self.assertEqual(clean_a.composite, clean_b.composite)

    def test_typed_encoding_does_not_collapse_or_split(self):
        def k(params):
            key, errors = build_content_identity_key(content(params=params))
            self.assertFalse(errors)
            return key.composite
        self.assertNotEqual(k({"p": 1}), k({"p": "1"}))
        self.assertNotEqual(k({"p": True}), k({"p": "True"}))
        self.assertNotEqual(k({"p": 1.0}), k({"p": "1.0"}))
        self.assertEqual(k({"p": ["a", "b"]}), k({"p": ("a", "b")}))
        self.assertEqual(k({"p": {"a": 1, "b": 2}}), k({"p": {"b": 2, "a": 1}}))
        self.assertEqual(k({"p": -0.0}), k({"p": 0.0}))

    def test_typed_encoding_tags_each_scalar_type(self):
        """Pins the typed-encoding contract itself.

        Value-level tests alone cannot detect a tag regression that keeps
        values distinct by accident, so the tags are asserted directly.
        """
        from tracker_identity.content_identity import _encode
        self.assertEqual(_encode(True)["t"], "bool")
        self.assertEqual(_encode(1)["t"], "int")
        self.assertEqual(_encode(1.5)["t"], "float")
        self.assertEqual(_encode("1")["t"], "str")
        self.assertEqual(_encode(None)["t"], "null")
        self.assertEqual(_encode({"a": 1})["t"], "map")
        self.assertEqual(_encode([1, 2])["t"], "seq")
        self.assertEqual(_encode([1, 2], unordered=True)["t"], "set")

    def test_E1_E2_non_string_mapping_keys_are_rejected_not_stringified(self):
        """Governed rule: mapping keys are strings only.

        {1:"x"} and {"1":"x"} cannot collapse, because the int-keyed payload
        never produces a key at all. Same for True vs "True".
        """
        for bad_key in (1, True, 1.5, None, (1, 2)):
            _, errors = build_content_identity_key(content(params={bad_key: "x"}))
            self.assertTrue(any("NON_STRING_MAPPING_KEY_REJECTED" in e
                                for e in errors), (bad_key, errors))
        ok, errors = build_content_identity_key(content(params={"1": "x"}))
        self.assertFalse(errors)
        self.assertIsNotNone(ok)

    def test_encoding_errors_name_the_offending_dimension(self):
        """Diagnostics must identify WHICH dimension failed to encode.

        A bare encoding failure tells an operator nothing about where to look,
        so the dimension name is part of the contract, not a nicety.
        """
        _, errors = build_content_identity_key(content(params={1: "x"}))
        self.assertTrue(
            any(e.startswith("CONTENT_ENCODING_ERROR:parameters:") for e in errors),
            errors)
        _, dep_errors = build_content_identity_key(content(deps=("A", "A")))
        self.assertTrue(
            any(e.startswith("CONTENT_ENCODING_ERROR:dependency_closure:")
                for e in dep_errors), dep_errors)

    def test_E3_unicode_normalized_key_collision_is_rejected(self):
        """Two distinct source keys normalizing to one must not silently merge."""
        payload = content(params={"\u00e9": 1, "e\u0301": 2})
        _, errors = build_content_identity_key(payload)
        self.assertTrue(any("UNICODE_NORMALIZED_KEY_COLLISION" in e
                            for e in errors), errors)

    def test_E3b_equivalent_unicode_keys_alone_normalize_consistently(self):
        a, ea = build_content_identity_key(content(params={"\u00e9": 1}))
        b, eb = build_content_identity_key(content(params={"e\u0301": 1}))
        self.assertFalse(ea); self.assertFalse(eb)
        self.assertEqual(a.composite, b.composite)

    def test_E4_mapping_insertion_order_does_not_affect_identity(self):
        a, _ = build_content_identity_key(content(params={"a": 1, "b": 2}))
        b, _ = build_content_identity_key(content(params={"b": 2, "a": 1}))
        self.assertEqual(a.composite, b.composite)

    def test_E5_nested_mappings_obey_the_same_key_rule(self):
        _, errors = build_content_identity_key(
            content(params={"outer": {"inner": {2: "x"}}}))
        self.assertTrue(any("NON_STRING_MAPPING_KEY_REJECTED" in e
                            for e in errors), errors)
        nested_a, ea = build_content_identity_key(
            content(params={"outer": {"a": 1, "b": 2}}))
        nested_b, eb = build_content_identity_key(
            content(params={"outer": {"b": 2, "a": 1}}))
        self.assertFalse(ea); self.assertFalse(eb)
        self.assertEqual(nested_a.composite, nested_b.composite)

    def test_E6_duplicate_dependency_identities_are_rejected(self):
        """dependency_closure is a SET: duplicates are malformed, not merged."""
        _, errors = build_content_identity_key(content(deps=("A", "A")))
        self.assertTrue(any("DUPLICATE_ELEMENT_IN_UNORDERED_DIMENSION" in e
                            for e in errors), errors)
        ok, clean = build_content_identity_key(content(deps=("A",)))
        self.assertFalse(clean)
        self.assertIsNotNone(ok)

    def test_non_finite_numeric_rejected_not_stringified(self):
        _, errors = build_content_identity_key(content(params={"p": float("nan")}))
        self.assertTrue(any("NON_FINITE_NUMERIC_REJECTED" in e for e in errors))

    def test_dependency_closure_is_unordered(self):
        a, _ = build_content_identity_key(content(deps=("x", "y")))
        b, _ = build_content_identity_key(content(deps=("y", "x")))
        self.assertEqual(a.composite, b.composite)

    def test_N_migrated_and_new_row_derive_same_key(self):
        record = FeatureDefinitionRecord(
            "gold.logret", "1", "semantic", GRAPH_A, ("xauusd.h1.close",), "ERA_1",
            "dh", "gh", instrument="XAUUSD", timeframe="H1",
            declared_normalization="NONE",
            causal_time_semantics="SALIX-XAUUSD-BROKER-UTC-TRANSITION-V1",
            completion_semantics="LAST_COMPLETED_BEFORE_T",
            availability_class="RECONSTRUCTED_NOT_OBSERVED",
            source_provider="ICMARKETSAU-LIVE-V1", price_basis="BID",
            data_vintage_mode="CURRENT_RECOMPUTED", scope_universe="XAUUSD/ERA_1",
            parameters={"lookback_bars": 2}, fitted_state="NONE",
            instrument_applicability="INSTRUMENT_SPECIFIC",
        )
        from_record, errors = record.content_identity_key()
        self.assertFalse(errors)
        from_payload, _ = build_content_identity_key(content())
        self.assertEqual(from_record.composite, from_payload.composite)


class FittedStateBoundary(unittest.TestCase):
    def _k(self, fitted):
        key, errors = build_content_identity_key(content(fitted=fitted))
        self.assertFalse(errors, errors)
        return key.composite

    def test_I_unfitted_and_fitted_do_not_collapse(self):
        self.assertNotEqual(
            self._k("NONE"),
            self._k({"fitted_parameters": {"threshold": 1.3}, "fitting_window": "2017-2024"}),
        )

    def test_J_different_fitted_values_do_not_collapse(self):
        self.assertNotEqual(
            self._k({"fitted_parameters": {"threshold": 1.3}}),
            self._k({"fitted_parameters": {"threshold": 1.4}}),
        )

    def test_K_fitting_window_and_training_vintage_do_not_collapse(self):
        base = {"fitted_parameters": {"threshold": 1.3}}
        self.assertNotEqual(
            self._k({**base, "fitting_window": "2017-2024"}),
            self._k({**base, "fitting_window": "2018-2025"}),
        )
        self.assertNotEqual(
            self._k({**base, "training_vintage": "V1"}),
            self._k({**base, "training_vintage": "V2"}),
        )

    def test_fitted_state_token_must_be_exactly_none(self):
        for bad in ("none", "NOT_APPLICABLE", "", "None"):
            _, errors = build_content_identity_key(content(fitted=bad))
            self.assertTrue(errors, bad)

    def test_process_provenance_rejected_from_fitted_state(self):
        _, errors = build_content_identity_key(
            content(fitted={"fitted_parameters": {"t": 1}, "run_id": "RUN-7"}))
        self.assertTrue(any("FITTED_STATE_NON_CONTENT_FIELD" in e for e in errors))

    def test_fitting_changes_key_so_it_is_a_new_version_not_a_mutation(self):
        unfitted, _ = build_content_identity_key(content(fitted="NONE"))
        fitted, _ = build_content_identity_key(
            content(fitted={"fitted_parameters": {"threshold": 1.3}}))
        self.assertNotEqual(unfitted.composite, fitted.composite)
        self.assertEqual(unfitted.definition_semantics, fitted.definition_semantics)


class FalseAbsenceClosed(unittest.TestCase):
    def test_A_Q_content_identical_under_different_name_is_not_absent(self):
        store = verified_store(registered("some.other.name", content()))
        result = run(store, pre_id())
        self.assertNotIn(result.outcome, (LookupOutcome.ABSENT_IN_ERA_1,
                                          LookupOutcome.ABSENT_EXACT_STRUCTURAL_IN_ERA_1))
        self.assertEqual(result.outcome, LookupOutcome.EXACT_CANONICAL_IDENTITY)
        self.assertEqual(result.exact_match.feature_id, "some.other.name")

    def test_B_pre_id_matching_registered_content_is_not_absent(self):
        store = verified_store(registered("gold.hourly_logreturn", content()))
        result = run(store, pre_id())
        self.assertEqual(result.outcome, LookupOutcome.EXACT_CANONICAL_IDENTITY)
        self.assertIsNone(result.absent_claim_token)

    def test_C_algebraically_equivalent_gets_no_certified_semantic_absence(self):
        store = verified_store(registered("gold.logret", content(graph=GRAPH_A)))
        result = run(store, pre_id(content(graph=GRAPH_B)))
        self.assertEqual(result.outcome, LookupOutcome.ABSENT_EXACT_STRUCTURAL_IN_ERA_1)
        self.assertEqual(result.semantic_uniqueness, "UNRESOLVED_NOT_CERTIFIED")
        self.assertNotEqual(result.outcome, LookupOutcome.ABSENT)

    def test_related_version_content_routes_to_review(self):
        store = verified_store(registered("gold.logret.eurusd",
                                          content(instrument="EURUSD")))
        result = run(store, pre_id())
        self.assertEqual(result.outcome, LookupOutcome.NEAR_MATCH)
        self.assertEqual(result.pending_collision_result,
                         "RELATED_VERSION_CONTENT_REVIEW_REQUIRED")

    def test_F_price_basis_difference_is_identity_bearing(self):
        store = verified_store(registered("gold.logret.ask", content(price_basis="ASK")))
        result = run(store, pre_id())
        self.assertNotEqual(result.outcome, LookupOutcome.EXACT_CANONICAL_IDENTITY)
        self.assertEqual(result.outcome, LookupOutcome.NEAR_MATCH)

    def test_E_source_vintage_difference_is_identity_bearing(self):
        store = verified_store(registered("gold.logret.v0",
                                          content(vintage="ORIGINAL_AS_OBSERVED")))
        result = run(store, pre_id())
        self.assertEqual(result.outcome, LookupOutcome.NEAR_MATCH)

    def test_G_proxy_conflict_routes_to_review_not_split_or_merge(self):
        store = verified_store(registered("gold.logret", content(), proxy="PROXY"))
        result = run(store, pre_id(proxy_status="NOT_PROXY"))
        self.assertEqual(result.outcome, LookupOutcome.NEAR_MATCH)
        self.assertEqual(result.pending_collision_result,
                         "PROXY_STATUS_CONFLICT_REVIEW_REQUIRED")

    def test_O_legacy_row_without_content_key_blocks_clean_absence(self):
        store = verified_store(FeatureIdentity(
            "legacy.unmigrated", "1", "d", "g", "CURRENT", True, "current_active", "ERA_1"))
        result = run(store, pre_id())
        self.assertFalse(result.lookup_complete)
        self.assertEqual(result.outcome, LookupOutcome.INCOMPLETE_LOOKUP)
        self.assertTrue(any(e.startswith("CONTENT_KEY_UNRESOLVED_ROWS") for e in result.errors))


class ScopeReachability(unittest.TestCase):
    def test_E_unreachable_scope_blocks_complete_lookup(self):
        store = verified_store()
        store.declare_scope("quarantined", "UNREACHABLE")
        result = run(store, pre_id())
        self.assertFalse(result.lookup_complete)
        self.assertTrue(any("SCOPE_NOT_PROVEN_REACHABLE" in e for e in result.errors))

    def test_F_unknown_scope_blocks_complete_lookup(self):
        store = CanonicalIdentityStore()  # nothing declared at all
        result = run(store, pre_id())
        self.assertFalse(result.lookup_complete)
        self.assertTrue(any("SCOPE_NOT_PROVEN_REACHABLE" in e for e in result.errors))

    def test_G_empty_verified_scopes_permit_a_complete_empty_lookup(self):
        result = run(verified_store(), pre_id())
        self.assertTrue(result.lookup_complete)
        self.assertEqual(result.outcome, LookupOutcome.ABSENT_EXACT_STRUCTURAL_IN_ERA_1)

    def test_scope_status_reported_on_result(self):
        result = run(verified_store(), pre_id())
        statuses = dict(result.scope_status)
        self.assertEqual(statuses["current_active"], "EMPTY_VERIFIED")


class AtomicClaims(unittest.TestCase):
    def test_D_two_concurrent_identical_requests_yield_one_active_claim(self):
        store = verified_store()
        a = run(store, pre_id(), request_id="REQ-A")
        b = run(store, pre_id(), request_id="REQ-B")
        self.assertEqual(a.outcome, LookupOutcome.ABSENT_EXACT_STRUCTURAL_IN_ERA_1)
        self.assertIsNotNone(a.absent_claim_token)
        self.assertEqual(b.outcome, LookupOutcome.INCOMPLETE_LOOKUP)
        self.assertIsNone(b.absent_claim_token)
        self.assertTrue(any(e.startswith("PENDING_CLAIM_EXISTS") for e in b.errors))
        active = [c for c in store.claims if c.state == "ACTIVE"]
        self.assertEqual(len(active), 1)

    def test_claim_is_persisted_not_merely_returned(self):
        store = verified_store()
        run(store, pre_id(), request_id="REQ-P")
        self.assertEqual(len(store.claims), 1)
        self.assertEqual(store.claims[0].request_id, "REQ-P")
        self.assertTrue(store.claims[0].expires_ts > store.claims[0].issued_ts)

    def test_M_expired_claim_cannot_authorize_late_registration(self):
        store = verified_store()
        clock = FrozenClock(datetime.now(timezone.utc))
        install_test_clock(self, clock)
        run(store, pre_id(), request_id="REQ-STALLED")
        key, _ = build_content_identity_key(content())
        clock.advance(10_000)
        claim, error = store.validate_claim_for_registration(
            content_key_composite=key.composite, request_id="REQ-STALLED")
        self.assertIsNone(claim)
        self.assertTrue(error.startswith("CLAIM_NOT_ACTIVE"), error)

    def test_M_expiry_frees_the_key_for_a_new_claim(self):
        store = verified_store()
        clock = FrozenClock(datetime.now(timezone.utc))
        install_test_clock(self, clock)
        run(store, pre_id(), request_id="REQ-STALLED")
        clock.advance(10_000)
        fresh = run(store, pre_id(), request_id="REQ-NEW")
        self.assertEqual(fresh.outcome, LookupOutcome.ABSENT_EXACT_STRUCTURAL_IN_ERA_1)
        self.assertIsNotNone(fresh.absent_claim_token)

    def test_expired_claim_record_transitions_to_expired_state(self):
        """Expiry is a recorded state transition, not only a time comparison."""
        store = verified_store()
        clock = FrozenClock(datetime.now(timezone.utc))
        install_test_clock(self, clock)
        run(store, pre_id(), request_id="REQ-TTL")
        self.assertEqual(store.claims[0].state, "ACTIVE")
        clock.advance(10_000)
        key, _ = build_content_identity_key(content())
        store.active_claim(key.composite)
        self.assertEqual(store.claims[0].state, "EXPIRED")
        self.assertEqual(store.claims[0].release_reason, "TTL_EXPIRED")

    def test_C1_C4_no_public_method_accepts_caller_controlled_time(self):
        """Every public claim/registration entry point owns its own time.

        active_claim() is mutation-capable (_expire_due transitions due claims
        to EXPIRED), so a caller-supplied timestamp could prematurely kill a
        legitimately ACTIVE claim. No such parameter exists on any of them.
        """
        import inspect
        from tracker_identity.store import CanonicalIdentityStore as S
        for name in ("commit_registration", "reserve_claim",
                     "validate_claim_for_registration", "active_claim"):
            params = inspect.signature(getattr(S, name)).parameters
            for forbidden in ("now", "now_iso"):
                self.assertNotIn(forbidden, params, f"{name}.{forbidden}")

    def test_C2_active_claim_cannot_prematurely_expire_a_valid_claim(self):
        """A future timestamp cannot be injected to kill a live claim."""
        store = verified_store()
        clock = FrozenClock(datetime.now(timezone.utc))
        install_test_clock(self, clock)
        run(store, pre_id(), request_id="REQ-LIVE")
        key, _ = build_content_identity_key(content())
        self.assertEqual(store.claims[0].state, "ACTIVE")
        # No public parameter exists to pass a future time.
        with self.assertRaises(TypeError):
            store.active_claim(key.composite, "2099-01-01T00:00:00+00:00")
        self.assertIsNotNone(store.active_claim(key.composite))
        self.assertEqual(store.claims[0].state, "ACTIVE")

    def test_C2b_no_side_channel_time_on_active_claim(self):
        """Only the store clock decides. A stray attribute must be ignored."""
        store = verified_store()
        clock = FrozenClock(datetime.now(timezone.utc))
        install_test_clock(self, clock)
        run(store, pre_id(), request_id="REQ-SIDE")
        key, _ = build_content_identity_key(content())
        store._caller_now = "2099-01-01T00:00:00+00:00"   # plausible side channel
        self.assertIsNotNone(store.active_claim(key.composite))
        self.assertEqual(store.claims[0].state, "ACTIVE")

    def test_C4b_reserve_claim_uses_the_private_locked_helper(self):
        """Lock ownership and time ownership are explicit.

        reserve_claim must not re-enter a public, mutation-capable method
        while holding _claim_lock; it uses the private locked helper, which
        may only receive a timestamp already obtained from the store clock.
        """
        import inspect
        from tracker_identity.store import CanonicalIdentityStore as S
        body = inspect.getsource(S.reserve_claim)
        self.assertIn("_active_claim_at_locked", body)
        self.assertNotIn("self.active_claim(", body)

    def test_C3_injected_store_clock_still_drives_deterministic_expiry(self):
        store = verified_store()
        clock = FrozenClock(datetime.now(timezone.utc))
        install_test_clock(self, clock)
        run(store, pre_id(), request_id="REQ-TTL2")
        self.assertIsNotNone(store.active_claim(
            build_content_identity_key(content())[0].composite))
        clock.advance(10_000)
        self.assertIsNone(store.active_claim(
            build_content_identity_key(content())[0].composite))
        self.assertEqual(store.claims[0].state, "EXPIRED")

    def test_claim_bound_to_its_request_id(self):
        store = verified_store()
        run(store, pre_id(), request_id="REQ-OWNER")
        key, _ = build_content_identity_key(content())
        claim, error = store.validate_claim_for_registration(
            content_key_composite=key.composite, request_id="REQ-IMPOSTOR")
        self.assertIsNone(claim)
        self.assertEqual(error, "CLAIM_NOT_FOUND")

    def test_release_is_terminal(self):
        store = verified_store()
        run(store, pre_id(), request_id="REQ-R")
        claim_id = store.claims[0].claim_id
        self.assertTrue(store.release_claim(claim_id=claim_id, reason="DONE"))
        self.assertFalse(store.release_claim(claim_id=claim_id, reason="AGAIN"))


class PreservedBoundaries(unittest.TestCase):
    def test_R_existing_hash_semantics_unchanged(self):
        record = FeatureDefinitionRecord(
            "f", "1", "semantic", "FORMULA", ("dep",), "ERA_1", "", "",
            instrument="XAUUSD", timeframe="H1")
        self.assertEqual(
            record.computed_definition_hash(),
            FeatureDefinitionRecord("f", "1", "semantic", "FORMULA", ("dep",), "ERA_1",
                                    "", "", instrument="XAUUSD",
                                    timeframe="H1").computed_definition_hash())
        rebound = FeatureDefinitionRecord("OTHER", "1", "semantic", "FORMULA", ("dep",),
                                          "ERA_1", "", "", instrument="XAUUSD",
                                          timeframe="H1")
        self.assertNotEqual(record.computed_definition_hash(),
                            rebound.computed_definition_hash())

    def test_pre_id_subject_may_not_carry_canonical_identity(self):
        result = run(verified_store(), pre_id(feature_id="x", feature_version="1"))
        self.assertIn("PRE_ID_SUBJECT_MUST_NOT_CARRY_CANONICAL_IDENTITY", result.errors)

    def test_pre_id_subject_may_not_carry_id_contaminated_hashes(self):
        result = run(verified_store(), pre_id(definition_hash="d", graph_hash="g"))
        self.assertIn("PRE_ID_SUBJECT_MUST_NOT_CARRY_ID_CONTAMINATED_HASHES", result.errors)

    def test_supplied_content_key_is_refused(self):
        result = run(verified_store(), pre_id(content_key_composite="deadbeef"))
        self.assertIn("SUPPLIED_CONTENT_KEY_NOT_ACCEPTED_RECOMPUTED_FROM_CONTENT",
                      result.errors)

    def test_P_validation_scope_remains_isolated(self):
        store = verified_store(registered("validation.anchor", content(),
                                          scope="validation"))
        isolated = run(store, pre_id())
        self.assertEqual(isolated.outcome, LookupOutcome.ABSENT_EXACT_STRUCTURAL_IN_ERA_1)
        included = run(store, pre_id(include_validation_scope=True), request_id="REQ-V")
        self.assertEqual(included.outcome, LookupOutcome.EXACT_CANONICAL_IDENTITY)

    def test_V2_excluded_validation_row_without_key_does_not_block(self):
        """Validation excluded -> an unreconstructable validation row is inert."""
        store = verified_store(FeatureIdentity(
            "validation.unkeyed", "1", "d", "g", "CURRENT", True, "validation", "ERA_1"))
        result = run(store, pre_id())
        self.assertTrue(result.lookup_complete, result.errors)
        self.assertEqual(result.outcome, LookupOutcome.ABSENT_EXACT_STRUCTURAL_IN_ERA_1)

    def test_V3_included_validation_row_without_key_fails_closed(self):
        """Same store, validation INCLUDED -> never absence, always incomplete."""
        store = verified_store(FeatureIdentity(
            "validation.unkeyed", "1", "d", "g", "CURRENT", True, "validation", "ERA_1"))
        result = run(store, pre_id(include_validation_scope=True), request_id="REQ-V3")
        self.assertFalse(result.lookup_complete)
        self.assertEqual(result.outcome, LookupOutcome.INCOMPLETE_LOOKUP)
        self.assertTrue(any(e.startswith("CONTENT_KEY_UNRESOLVED_ROWS")
                            for e in result.errors), result.errors)
        self.assertIsNone(result.absent_claim_token)

    def test_V4_included_validation_row_with_key_resolves_normally(self):
        """Once the validation row carries a valid key, inclusion works."""
        store = verified_store(registered("validation.anchor", content(),
                                          scope="validation"))
        result = run(store, pre_id(include_validation_scope=True), request_id="REQ-V4")
        self.assertTrue(result.lookup_complete, result.errors)
        self.assertEqual(result.outcome, LookupOutcome.EXACT_CANONICAL_IDENTITY)
        self.assertEqual(result.exact_match.feature_id, "validation.anchor")

    def test_V3b_participation_is_not_decided_by_scope_name(self):
        """A non-validation unkeyed row blocks too — one rule, both scopes."""
        store = verified_store(FeatureIdentity(
            "live.unkeyed", "1", "d", "g", "CURRENT", True, "current_active", "ERA_1"))
        result = run(store, pre_id())
        self.assertFalse(result.lookup_complete)
        self.assertTrue(any(e.startswith("CONTENT_KEY_UNRESOLVED_ROWS")
                            for e in result.errors))

    def test_all_eras_still_cannot_emit_global_absent(self):
        result = run(verified_store(), pre_id(lookup_era_scope="ALL_ERAS"))
        self.assertEqual(result.outcome, LookupOutcome.INCOMPLETE_LOOKUP)
        self.assertIn("ALL_ERAS_COVERAGE_INCOMPLETE", result.errors)

    def test_structural_absence_maps_to_incomplete_at_composer_boundary(self):
        self.assertEqual(
            composer_boundary_outcome(LookupOutcome.ABSENT_EXACT_STRUCTURAL_IN_ERA_1),
            LookupOutcome.INCOMPLETE_LOOKUP)

    def test_no_equivalence_class_was_added(self):
        from tracker_identity.models import SUPPORTED_EQUIVALENCE_CLASSES
        self.assertEqual(SUPPORTED_EQUIVALENCE_CLASSES, ("EXACT_STRUCTURAL_IDENTITY",))

    def test_name_match_with_conflicting_content_is_not_exact(self):
        store = verified_store(registered("gold.logret", content()))
        subject = {
            "subject_mode": "CANONICAL_ID",
            "feature_id": "gold.logret", "feature_version": "1",
            "definition_hash": "legacy-definition-hash",
            "graph_hash": "legacy-graph-hash",
            "instrument": "XAUUSD", "timeframe": "H1",
            "lookup_era_scope": "ERA_1_ONLY",
            "candidate_content": content(deps=("xauusd.h4.close",)),
        }
        result = run(store, subject)
        self.assertNotEqual(result.outcome, LookupOutcome.EXACT_CANONICAL_IDENTITY)
        self.assertEqual(result.pending_collision_result,
                         "CONTENT_KEY_CONFLICT_REVIEW_REQUIRED")


if __name__ == "__main__":
    unittest.main()
