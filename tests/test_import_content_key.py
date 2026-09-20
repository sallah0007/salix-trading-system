"""Import / migration content-key controls (I1-I9).

Raised by Manager re-attack B-1 on M-TYPE1-PREID-v2-4992504: importer and
stale_sweep did not participate in the single content-key derivation, so a
governed import could write rows without a key and self-disable PRE_ID with
CONTENT_KEY_UNRESOLVED_ROWS.
"""

import unittest
from dataclasses import replace

from tracker_identity import (
    CONTENT_KEY_ALGORITHM_ID,
    MANDATORY_DUPLICATE_CONTROL_SCOPES,
    CanonicalEraBoundary,
    CanonicalIdentityStore,
    FeatureDefinitionCatalogue,
    FeatureDefinitionRecord,
    FeatureIdentity,
    IdentityImportManifest,
    ImportSourceRef,
    LookupOutcome,
    NormalizerSpec,
    SearchPolicy,
    SourceUniverseAuthority,
    governed_search_policy,
    identity_lookup,
    import_identity_content,
    stale_state_sweep,
)

ERA = "ERA_1"
SCOPES = ("current_active",)

CONTENT_DIMS = dict(
    declared_normalization="NONE",
    causal_time_semantics="SALIX-XAUUSD-BROKER-UTC-TRANSITION-V1",
    completion_semantics="LAST_COMPLETED_BEFORE_T",
    availability_class="RECONSTRUCTED_NOT_OBSERVED",
    source_provider="ICMARKETSAU-LIVE-V1",
    price_basis="BID",
    data_vintage_mode="CURRENT_RECOMPUTED",
    scope_universe="XAUUSD/ERA_1",
    parameters={"lookback_bars": 2},
    fitted_state="NONE",
)


def policy(scopes=SCOPES):
    p = SearchPolicy("import-ctl", "1", "", scopes, scopes, {})
    return SearchPolicy(p.policy_id, p.version, p.computed_hash(),
                        p.required_scopes, p.searched_scopes, p.scope_exclusions)


def normalizer():
    n = NormalizerSpec("import-ctl", "1", "", ("EXACT_STRUCTURAL_IDENTITY",))
    return NormalizerSpec(n.normalizer_id, n.version, n.computed_hash(), n.equivalence_classes)


def boundary():
    vals = dict(
        era_id=ERA, version="1", boundary_hash="", effective_ts="2026-09-19T20:47:37+10:00",
        predecessor_era_id="ERA_0", registry_id="SALIX-ERA1-REGISTRY",
        catalogue_id="CAT", source_universe_id="U1",
        pre_era_content_default="UNRESOLVED_NON_IMPORTABLE",
        historical_gap_status="UNRESOLVED", historical_gap_owner="MANAGER",
        revisit_trigger="IF_ERA0_ARTIFACT_LOCATED_REVIEW_BEFORE_IMPORT",
        absent_proven=False, created_by="SALIX_MANAGER", approval_authority="OWNER",
        created_ts="2026-09-19T20:47:37+10:00",
    )
    x = CanonicalEraBoundary(**vals)
    vals["boundary_hash"] = x.computed_hash()
    return CanonicalEraBoundary(**vals)


def universe():
    vals = dict(source_universe_id="U1", version="1", source_universe_hash="",
                authority_source_id="boundary", expected_source_ids=("s",),
                universe_complete=True, era_id=ERA, unresolved_source_classes=())
    x = SourceUniverseAuthority(**vals)
    vals["source_universe_hash"] = x.computed_hash()
    return SourceUniverseAuthority(**vals)


def definition(fid="gold.logret", complete=True):
    dims = dict(CONTENT_DIMS) if complete else {
        k: v for k, v in CONTENT_DIMS.items() if k != "price_basis"}
    d = FeatureDefinitionRecord(fid, "1", "definition", "LN(DIV(C[t],C[t-1]))", (),
                                ERA, "", "", instrument="XAUUSD", timeframe="H1", **dims)
    return FeatureDefinitionRecord(fid, "1", "definition", "LN(DIV(C[t],C[t-1]))", (),
                                   ERA, d.computed_definition_hash(), d.computed_graph_hash(),
                                   instrument="XAUUSD", timeframe="H1", **dims)


def catalogue(fid="gold.logret", complete=True):
    return FeatureDefinitionCatalogue("CAT", ERA, (definition(fid, complete),))


def row(fid="gold.logret", **changes):
    d = definition(fid)
    vals = dict(
        feature_id=fid, feature_version="1",
        definition_hash=d.definition_hash, graph_hash=d.graph_hash,
        lifecycle_state="CURRENT", is_current=True, scope="current_active",
        era_id=ERA, instrument="XAUUSD", timeframe="H1",
        import_source_id="s", import_source_authority_class="CANONICAL",
    )
    vals.update(changes)
    return FeatureIdentity(**vals)


def do_import(rows, cat=None, store=None):
    store = store or CanonicalIdentityStore(active_era_id=ERA)
    result = import_identity_content(
        target_store=store, rows=tuple(rows),
        manifest=IdentityImportManifest("M", "1", ERA,
                                        (ImportSourceRef("s", "source", "CANONICAL",
                                                         True, len(rows), ERA),)),
        source_universe=universe(), era_boundary=boundary(),
        catalogue=cat or catalogue(), search_policy=policy(), normalizer=normalizer())
    return store, result


class ImportContentKey(unittest.TestCase):

    def test_I1_imported_row_key_equals_derivation_from_definition(self):
        store, result = do_import([row()])
        self.assertTrue(result.errors == (), result.errors)
        written = store.all()[0]
        expected, errors = definition().content_identity_key()
        self.assertFalse(errors)
        self.assertTrue(written.has_content_key)
        self.assertEqual(written.content_key_composite, expected.composite)
        self.assertEqual(written.content_key_definition, expected.definition_semantics)
        self.assertEqual(written.content_key_algorithm_id, CONTENT_KEY_ALGORITHM_ID)

    def test_I2_incomplete_authoritative_content_is_rejected_not_written_bare(self):
        store, result = do_import([row()], cat=catalogue(complete=False))
        self.assertTrue(any(e.startswith("ROW_CONTENT_KEY_UNRESOLVABLE")
                            for e in result.errors), result.errors)
        self.assertEqual(len(store.all()), 0)

    def test_I3_forged_caller_supplied_key_cannot_override_recomputation(self):
        store, result = do_import([row(content_key_composite="forged-key",
                                       content_key_definition="forged")])
        self.assertTrue(any(e.startswith("ROW_SUPPLIED_CONTENT_KEY_REJECTED")
                            for e in result.errors), result.errors)
        self.assertEqual(len(store.all()), 0)

    def test_I7_pre_id_remains_operational_after_import(self):
        store, result = do_import([row()])
        self.assertEqual(result.errors, ())
        self.assertEqual(store.rows_without_content_key(ERA), ())
        # A PRE_ID lookup now runs under the Tracker-owned governed policy, so
        # every mandatory duplicate-control scope must be proven reachable —
        # not just the one scope this import fixture happens to populate.
        for sc in MANDATORY_DUPLICATE_CONTROL_SCOPES:
            store.declare_scope(sc, "EMPTY_VERIFIED")
        subject = {
            "subject_mode": "PRE_ID",
            "feature_id": "", "feature_version": "",
            "definition_hash": "", "graph_hash": "",
            "instrument": "XAUUSD", "timeframe": "H1",
            "lookup_era_scope": "ERA_1_ONLY",
            "candidate_content": {
                "normalized_definition_graph": "LN(DIV(C[t],C[t-1]))",
                "dependency_closure": (),
                "instrument": "XAUUSD", "timeframe": "H1", **CONTENT_DIMS,
            },
        }
        result = identity_lookup(store=store, subject=subject, request_id="REQ-PI",
                                 search_policy=governed_search_policy(),
                                 normalizer=normalizer())
        self.assertNotIn("CONTENT_KEY_UNRESOLVED_ROWS",
                         " ".join(result.errors))
        self.assertEqual(result.outcome, LookupOutcome.EXACT_CANONICAL_IDENTITY)


class ValidationScopeParticipation(unittest.TestCase):

    def test_V1_validation_row_with_complete_content_gets_key_on_import(self):
        store, result = do_import([row(scope="validation")])
        self.assertEqual(result.errors, (), result.errors)
        written = store.all()[0]
        self.assertEqual(written.scope, "validation")
        self.assertTrue(written.has_content_key)
        expected, _ = definition().content_identity_key()
        self.assertEqual(written.content_key_composite, expected.composite)

    def test_V5_validation_row_with_corrupted_key_detected_by_sweep(self):
        store, _ = do_import([row(scope="validation")])
        bad = replace(store.all()[0], content_key_composite="corrupted")
        sweep = stale_state_sweep(
            store=CanonicalIdentityStore([bad], active_era_id=ERA),
            search_policy=policy(("validation",)), normalizer=normalizer(),
            catalogue=catalogue())
        self.assertFalse(sweep.clean)
        self.assertTrue(any("CONTENT_KEY_COMPOSITE_MISMATCH" in d
                            for d in sweep.defects), sweep.defects)

    def test_validation_row_missing_reconstructable_key_is_a_defect(self):
        """No blanket validation exemption in the sweep either."""
        sweep = stale_state_sweep(
            store=CanonicalIdentityStore([row(scope="validation")], active_era_id=ERA),
            search_policy=policy(("validation",)), normalizer=normalizer(),
            catalogue=catalogue())
        self.assertFalse(sweep.clean)
        self.assertTrue(any("CONTENT_KEY_MISSING_BUT_RECONSTRUCTABLE" in d
                            for d in sweep.defects), sweep.defects)


class StaleSweepContentKey(unittest.TestCase):

    def _sweep(self, record):
        store = CanonicalIdentityStore([record], active_era_id=ERA)
        return stale_state_sweep(store=store, search_policy=policy(),
                                 normalizer=normalizer(), catalogue=catalogue())

    def _good_row(self):
        store, _ = do_import([row()])
        return store.all()[0]

    def test_I4_corrupted_composite_detected(self):
        bad = replace(self._good_row(), content_key_composite="corrupted")
        sweep = self._sweep(bad)
        self.assertFalse(sweep.clean)
        self.assertTrue(any("CONTENT_KEY_COMPOSITE_MISMATCH" in d for d in sweep.defects))

    def test_I5_corrupted_individual_subkey_detected(self):
        bad = replace(self._good_row(), content_key_provenance="corrupted")
        sweep = self._sweep(bad)
        self.assertFalse(sweep.clean)
        self.assertTrue(any("CONTENT_SUBKEY_MISMATCH:PROVENANCE" in d
                            for d in sweep.defects), sweep.defects)

    def test_I6_unknown_algorithm_id_detected(self):
        bad = replace(self._good_row(), content_key_algorithm_id="SOME-OTHER-V9")
        sweep = self._sweep(bad)
        self.assertFalse(sweep.clean)
        self.assertTrue(any("CONTENT_KEY_ALGORITHM_UNRECOGNISED" in d
                            for d in sweep.defects))

    def test_missing_but_reconstructable_key_detected(self):
        bare = row()
        sweep = self._sweep(bare)
        self.assertFalse(sweep.clean)
        self.assertTrue(any("CONTENT_KEY_MISSING_BUT_RECONSTRUCTABLE" in d
                            for d in sweep.defects))

    def test_partially_projected_key_detected(self):
        bad = replace(self._good_row(), content_key_fitted=None)
        sweep = self._sweep(bad)
        self.assertFalse(sweep.clean)
        self.assertTrue(any("CONTENT_KEY_PARTIALLY_PROJECTED" in d
                            for d in sweep.defects))

    def test_good_row_sweeps_clean(self):
        sweep = self._sweep(self._good_row())
        self.assertTrue(sweep.clean, sweep.defects)


if __name__ == "__main__":
    unittest.main()
