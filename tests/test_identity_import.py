import unittest

from tracker_identity import (
    CanonicalEraBoundary, CanonicalIdentityStore, FeatureIdentity,
    FeatureDefinitionCatalogue, FeatureDefinitionRecord,
    IdentityImportManifest, ImportSourceRef, NormalizerSpec, SearchPolicy,
    SourceUniverseAuthority, import_identity_content,
)

def policy():
    p=SearchPolicy("p","1","",("current_active",),("current_active",),{})
    return SearchPolicy(p.policy_id,p.version,p.computed_hash(),p.required_scopes,p.searched_scopes,p.scope_exclusions)

def normalizer():
    n=NormalizerSpec("n","1","",("EXACT_STRUCTURAL_IDENTITY",))
    return NormalizerSpec(n.normalizer_id,n.version,n.computed_hash(),n.equivalence_classes)

def boundary():
    vals=dict(
        era_id="ERA_1",version="1",boundary_hash="",effective_ts="2026-09-19T00:00:00+10:00",
        predecessor_era_id="ERA_0",registry_id="SALIX-ERA1-REGISTRY",catalogue_id="CAT",
        source_universe_id="U1",pre_era_content_default="UNRESOLVED_NON_IMPORTABLE",
        historical_gap_status="UNRESOLVED",historical_gap_owner="MANAGER",
        revisit_trigger="IF_ERA0_ARTIFACT_LOCATED_REVIEW_BEFORE_IMPORT",absent_proven=False,
        created_by="SALIX_MANAGER",approval_authority="OWNER",created_ts="2026-09-19T00:00:00+10:00",
    )
    x=CanonicalEraBoundary(**vals); vals["boundary_hash"]=x.computed_hash()
    return CanonicalEraBoundary(**vals)

def universe(expected=("s",),complete=True,unresolved=()):
    vals=dict(source_universe_id="U1",version="1",source_universe_hash="",
              authority_source_id="boundary",expected_source_ids=tuple(expected),
              universe_complete=complete,era_id="ERA_1",unresolved_source_classes=tuple(unresolved))
    x=SourceUniverseAuthority(**vals); vals["source_universe_hash"]=x.computed_hash()
    return SourceUniverseAuthority(**vals)

def manifest(refs,era="ERA_1"):
    return IdentityImportManifest("M","1",era,tuple(refs))

def ref(source_id="s",authority="CANONICAL",rows=1,era="ERA_1",searched=True):
    return ImportSourceRef(source_id,"source",authority,searched,rows,era)

# Governed content dimensions required for CONTENT_IDENTITY_KEY derivation.
# Fixture updated to the current contract; no assertion was weakened.
CONTENT_DIMS=dict(
    declared_normalization="NONE",causal_time_semantics="TS-V1",
    completion_semantics="LAST_COMPLETED_BEFORE_T",
    availability_class="RECONSTRUCTED_NOT_OBSERVED",source_provider="P1",
    price_basis="BID",data_vintage_mode="CURRENT_RECOMPUTED",
    scope_universe="U/ERA_1",parameters={},fitted_state="NONE",
)

def catalogue(fid="f1", version="1", era="ERA_1"):
    d=FeatureDefinitionRecord(fid,version,"definition","x",(),era,"","",
                              instrument="XAUUSD",timeframe="H1",**CONTENT_DIMS)
    d=FeatureDefinitionRecord(fid,version,"definition","x",(),era,
                              d.computed_definition_hash(),d.computed_graph_hash(),
                              instrument="XAUUSD",timeframe="H1",**CONTENT_DIMS)
    return FeatureDefinitionCatalogue("CAT",era,(d,))

def row(fid="f1",source_id="s",authority="CANONICAL",era="ERA_1",current=True,lifecycle="CURRENT"):
    return FeatureIdentity(
        feature_id=fid,feature_version="1",definition_hash=catalogue(fid).definitions[0].definition_hash,graph_hash=catalogue(fid).definitions[0].graph_hash,
        lifecycle_state=lifecycle,is_current=current,scope="current_active",era_id=era,
        instrument="XAUUSD",timeframe="H1",
        import_source_id=source_id,import_source_authority_class=authority,
    )

def run(rows,man,uni=None,store=None):
    store=store or CanonicalIdentityStore()
    result=import_identity_content(
        target_store=store,rows=tuple(rows),manifest=man,source_universe=uni or universe(),
        era_boundary=boundary(),catalogue=catalogue(rows[0].feature_id if rows else "f1"),search_policy=policy(),normalizer=normalizer())
    return store,result

class ImportBoundaryTests(unittest.TestCase):
    def test_zero_rows_incomplete_universe_not_complete(self):
        man=manifest((ref(rows=0,authority="MANAGER_RECORD"),))
        store,result=run((),man,universe(complete=False,unresolved=("POPULATED_REGISTRY",)))
        self.assertFalse(result.population_complete)
        self.assertEqual(store.all(),())

    def test_zero_rows_complete_era1_universe_can_complete(self):
        man=manifest((ref(rows=0),))
        store,result=run((),man)
        self.assertTrue(result.population_complete)
        self.assertEqual(store.all(),())

    def test_missing_external_source_fails(self):
        man=manifest((ref("s",rows=0),))
        store,result=run((),man,universe(expected=("s","missing")))
        self.assertTrue(any(e.startswith("UNENUMERATED_SOURCE:") for e in result.errors))
        self.assertEqual(store.all(),())

    def test_noncanonical_source_rejected_without_mutation(self):
        man=manifest((ref(authority="HISTORICAL_EXAMPLE"),))
        store,result=run((row(authority="HISTORICAL_EXAMPLE"),),man)
        self.assertTrue(any(e.startswith("NONCANONICAL_SOURCE_HAS_IMPORTABLE_ROWS:") for e in result.errors))
        self.assertEqual(store.all(),())

    def test_provenance_required(self):
        bad=FeatureIdentity("f1","1","a","b","CURRENT",True,"current_active",era_id="ERA_1")
        man=manifest((ref(),))
        store,result=run((bad,),man)
        self.assertTrue(any(e.startswith("ROW_IMPORT_PROVENANCE_REQUIRED:") for e in result.errors))
        self.assertEqual(store.all(),())

    def test_per_source_distribution_reconciles(self):
        man=manifest((ref("s",rows=0),ref("t",rows=1)))
        store,result=run((row(source_id="s"),),man,universe(expected=("s","t")))
        self.assertTrue(any(e.startswith("IMPORT_SOURCE_ROW_COUNT_MISMATCH:") for e in result.errors))
        self.assertEqual(store.all(),())

    def test_stale_sweep_prevents_mutation(self):
        man=manifest((ref(),))
        store,result=run((row(current=True,lifecycle="SUPERSEDED"),),man)
        self.assertIn("STALE_STATE_SWEEP_FAILED",result.errors)
        self.assertEqual(store.all(),())

if __name__=="__main__":
    unittest.main()
