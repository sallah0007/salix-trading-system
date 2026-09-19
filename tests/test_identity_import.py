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

def row(fid="f1"):
    return FeatureIdentity(
        feature_id=fid,feature_version="1",definition_hash="a",graph_hash="b",
        lifecycle_state="CURRENT",is_current=True,scope="current_active",
    )

class ImportBoundaryTests(unittest.TestCase):
    def test_zero_rows_incomplete_universe_does_not_claim_population_complete(self):
        manifest=IdentityImportManifest(
            manifest_id="M1",version="1",
            source_refs=(
                ImportSourceRef(
                    source_id="drive:lookup-attempt",title="lookup attempt",
                    authority_class="MANAGER_RECORD",searched=True,
                    importable_identity_rows=0,
                ),
            ),
            declared_source_universe_complete=False,
            unresolved_source_classes=("POPULATED_REGISTRY","FEATURE_DEFINITION_CATALOGUE"),
        )
        store=CanonicalIdentityStore()
        result=import_identity_content(
            target_store=store,rows=(),manifest=manifest,
            search_policy=policy(),normalizer=normalizer(),
        )
        self.assertEqual(result.imported_row_count,0)
        self.assertFalse(result.population_complete)
        self.assertEqual(store.all(),())

    def test_zero_rows_complete_universe_can_be_complete(self):
        manifest=IdentityImportManifest(
            manifest_id="M2",version="1",
            source_refs=(
                ImportSourceRef(
                    source_id="authority:empty",title="governed empty authority",
                    authority_class="CANONICAL",searched=True,
                    importable_identity_rows=0,
                ),
            ),
            declared_source_universe_complete=True,
            unresolved_source_classes=(),
        )
        result=import_identity_content(
            target_store=CanonicalIdentityStore(),rows=(),manifest=manifest,
            search_policy=policy(),normalizer=normalizer(),
        )
        self.assertTrue(result.population_complete)

    def test_row_count_mismatch_fails_without_mutation(self):
        manifest=IdentityImportManifest(
            manifest_id="M3",version="1",
            source_refs=(
                ImportSourceRef("s","source","CANONICAL",True,1),
            ),
            declared_source_universe_complete=True,
        )
        store=CanonicalIdentityStore()
        result=import_identity_content(
            target_store=store,rows=(),manifest=manifest,
            search_policy=policy(),normalizer=normalizer(),
        )
        self.assertFalse(result.population_complete)
        self.assertTrue(any("IMPORT_ROW_COUNT_MISMATCH" in e for e in result.errors))
        self.assertEqual(store.all(),())

    def test_stale_rows_fail_before_mutation(self):
        manifest=IdentityImportManifest(
            manifest_id="M4",version="1",
            source_refs=(ImportSourceRef("s","source","CANONICAL",True,1),),
            declared_source_universe_complete=True,
        )
        stale=FeatureIdentity(
            feature_id="f1",feature_version="1",definition_hash="a",graph_hash="b",
            lifecycle_state="SUPERSEDED",is_current=True,scope="current_active",
        )
        store=CanonicalIdentityStore()
        result=import_identity_content(
            target_store=store,rows=(stale,),manifest=manifest,
            search_policy=policy(),normalizer=normalizer(),
        )
        self.assertFalse(result.population_complete)
        self.assertIn("STALE_STATE_SWEEP_FAILED",result.errors)
        self.assertEqual(store.all(),())

if __name__=="__main__":
    unittest.main()
