import unittest

from tracker_identity import (
    CanonicalIdentityStore,
    FeatureIdentity,
    NormalizerSpec,
    SearchPolicy,
)
from tracker_identity.importer import (
    IdentityImportManifest,
    ImportSourceRef,
    SourceUniverseAuthority,
    import_identity_content,
)

SCOPES=("current_active",)

def policy():
    p=SearchPolicy(
        policy_id="p",version="1",policy_hash="",
        required_scopes=SCOPES,searched_scopes=SCOPES,scope_exclusions={},
    )
    return SearchPolicy(
        policy_id=p.policy_id,version=p.version,policy_hash=p.computed_hash(),
        required_scopes=p.required_scopes,searched_scopes=p.searched_scopes,
        scope_exclusions=p.scope_exclusions,
    )

def normalizer():
    n=NormalizerSpec(
        normalizer_id="n",version="1",normalizer_hash="",
        equivalence_classes=("EXACT_STRUCTURAL_IDENTITY",),
    )
    return NormalizerSpec(
        normalizer_id=n.normalizer_id,version=n.version,
        normalizer_hash=n.computed_hash(),equivalence_classes=n.equivalence_classes,
    )

def universe(expected=("s",), complete=True, unresolved=()):
    u=SourceUniverseAuthority(
        source_universe_id="U1",version="1",source_universe_hash="",
        authority_source_id="drive:census",expected_source_ids=tuple(expected),
        universe_complete=complete,unresolved_source_classes=tuple(unresolved),
    )
    return SourceUniverseAuthority(
        source_universe_id=u.source_universe_id,version=u.version,
        source_universe_hash=u.computed_hash(),
        authority_source_id=u.authority_source_id,
        expected_source_ids=u.expected_source_ids,
        universe_complete=u.universe_complete,
        unresolved_source_classes=u.unresolved_source_classes,
    )

def row(fid="f1", source_id="s", authority="CANONICAL"):
    return FeatureIdentity(
        feature_id=fid,feature_version="1",definition_hash="a",graph_hash="b",
        lifecycle_state="CURRENT",is_current=True,scope="current_active",
        import_source_id=source_id,import_source_authority_class=authority,
    )

class ImportBoundaryTests(unittest.TestCase):
    def test_zero_rows_incomplete_universe_does_not_claim_population_complete(self):
        manifest=IdentityImportManifest(
            manifest_id="M1",version="1",
            source_refs=(ImportSourceRef("s","source","MANAGER_RECORD",True,0),),
        )
        store=CanonicalIdentityStore()
        result=import_identity_content(
            target_store=store,rows=(),manifest=manifest,
            source_universe=universe(complete=False,unresolved=("POPULATED_REGISTRY",)),
            search_policy=policy(),normalizer=normalizer(),
        )
        self.assertEqual(result.imported_row_count,0)
        self.assertFalse(result.population_complete)
        self.assertEqual(store.all(),())

    def test_zero_rows_complete_external_universe_can_be_complete(self):
        manifest=IdentityImportManifest(
            manifest_id="M2",version="1",
            source_refs=(ImportSourceRef("s","source","CANONICAL",True,0),),
        )
        result=import_identity_content(
            target_store=CanonicalIdentityStore(),rows=(),manifest=manifest,
            source_universe=universe(),search_policy=policy(),normalizer=normalizer(),
        )
        self.assertTrue(result.population_complete)

    def test_manifest_cannot_self_certify_missing_census_source(self):
        manifest=IdentityImportManifest(
            manifest_id="M3",version="1",
            source_refs=(ImportSourceRef("s","source","CANONICAL",True,0),),
        )
        store=CanonicalIdentityStore()
        result=import_identity_content(
            target_store=store,rows=(),manifest=manifest,
            source_universe=universe(expected=("s","missing-source")),
            search_policy=policy(),normalizer=normalizer(),
        )
        self.assertFalse(result.population_complete)
        self.assertTrue(any(e.startswith("UNENUMERATED_SOURCE:") for e in result.errors))
        self.assertEqual(store.all(),())

    def test_noncanonical_source_rows_are_rejected_without_mutation(self):
        manifest=IdentityImportManifest(
            manifest_id="M4",version="1",
            source_refs=(ImportSourceRef("s","historical","HISTORICAL_EXAMPLE",True,1),),
        )
        store=CanonicalIdentityStore()
        result=import_identity_content(
            target_store=store,
            rows=(row(authority="HISTORICAL_EXAMPLE"),),
            manifest=manifest,source_universe=universe(),
            search_policy=policy(),normalizer=normalizer(),
        )
        self.assertFalse(result.population_complete)
        self.assertTrue(any(e.startswith("NONCANONICAL_SOURCE_HAS_IMPORTABLE_ROWS:") for e in result.errors))
        self.assertTrue(any(e.startswith("ROW_SOURCE_AUTHORITY_NOT_PERMITTED:") for e in result.errors))
        self.assertEqual(store.all(),())

    def test_row_authority_must_match_manifest_source(self):
        manifest=IdentityImportManifest(
            manifest_id="M5",version="1",
            source_refs=(ImportSourceRef("s","source","CANONICAL",True,1),),
        )
        store=CanonicalIdentityStore()
        result=import_identity_content(
            target_store=store,
            rows=(row(authority="CURRENT_CANONICAL_REGISTRY"),),
            manifest=manifest,source_universe=universe(),
            search_policy=policy(),normalizer=normalizer(),
        )
        self.assertFalse(result.population_complete)
        self.assertTrue(any(e.startswith("ROW_SOURCE_AUTHORITY_MISMATCH:") for e in result.errors))
        self.assertEqual(store.all(),())

    def test_per_source_row_count_mismatch_fails_without_mutation(self):
        manifest=IdentityImportManifest(
            manifest_id="M6",version="1",
            source_refs=(
                ImportSourceRef("s","source","CANONICAL",True,0),
                ImportSourceRef("t","source2","CANONICAL",True,1),
            ),
        )
        store=CanonicalIdentityStore()
        result=import_identity_content(
            target_store=store,
            rows=(row(source_id="s"),),
            manifest=manifest,source_universe=universe(expected=("s","t")),
            search_policy=policy(),normalizer=normalizer(),
        )
        self.assertFalse(result.population_complete)
        self.assertTrue(any(e.startswith("IMPORT_SOURCE_ROW_COUNT_MISMATCH:") for e in result.errors))
        self.assertEqual(store.all(),())

    def test_stale_rows_fail_before_mutation(self):
        manifest=IdentityImportManifest(
            manifest_id="M7",version="1",
            source_refs=(ImportSourceRef("s","source","CANONICAL",True,1),),
        )
        stale=FeatureIdentity(
            feature_id="f1",feature_version="1",definition_hash="a",graph_hash="b",
            lifecycle_state="SUPERSEDED",is_current=True,scope="current_active",
            import_source_id="s",import_source_authority_class="CANONICAL",
        )
        store=CanonicalIdentityStore()
        result=import_identity_content(
            target_store=store,rows=(stale,),manifest=manifest,
            source_universe=universe(),search_policy=policy(),normalizer=normalizer(),
        )
        self.assertFalse(result.population_complete)
        self.assertIn("STALE_STATE_SWEEP_FAILED",result.errors)
        self.assertEqual(store.all(),())

if __name__=="__main__":
    unittest.main()
