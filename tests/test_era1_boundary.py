import json
import pathlib
import unittest

from tracker_identity import (
    CanonicalEraBoundary, CanonicalIdentityStore, FeatureIdentity,
    FeatureDefinitionCatalogue, FeatureDefinitionRecord,
    IdentityImportManifest, ImportSourceRef, NormalizerSpec, SearchPolicy,
    SourceUniverseAuthority, import_identity_content,
)

ROOT=pathlib.Path(__file__).resolve().parents[1]

def policy():
    p=SearchPolicy("era1","1","",("validation",),("validation",),{})
    return SearchPolicy(p.policy_id,p.version,p.computed_hash(),p.required_scopes,p.searched_scopes,p.scope_exclusions)

def normalizer():
    n=NormalizerSpec("era1","1","",("EXACT_STRUCTURAL_IDENTITY",))
    return NormalizerSpec(n.normalizer_id,n.version,n.computed_hash(),n.equivalence_classes)

def boundary(**changes):
    vals=dict(
        era_id="ERA_1",version="1",boundary_hash="",effective_ts="2026-09-19T00:00:00+10:00",
        predecessor_era_id="ERA_0",registry_id="SALIX-ERA1-REGISTRY",
        catalogue_id="SALIX-ERA1-FEATURE-CATALOGUE",source_universe_id="SALIX-ERA1-SOURCE-UNIVERSE-001",
        pre_era_content_default="UNRESOLVED_NON_IMPORTABLE",historical_gap_status="UNRESOLVED",
        historical_gap_owner="MANAGER",revisit_trigger="IF_ERA0_ARTIFACT_LOCATED_REVIEW_BEFORE_IMPORT",
        absent_proven=False,created_by="SALIX_MANAGER",approval_authority="OWNER",
        created_ts="2026-09-19T00:00:00+10:00",
    )
    vals.update(changes)
    vals["boundary_hash"]=""
    x=CanonicalEraBoundary(**vals)
    vals["boundary_hash"]=x.computed_hash()
    return CanonicalEraBoundary(**vals)

def universe(**changes):
    vals=dict(
        source_universe_id="SALIX-ERA1-SOURCE-UNIVERSE-001",version="1",source_universe_hash="",
        authority_source_id="governance:ERA1_BOUNDARY",expected_source_ids=("era1:catalogue:neutral-core",),
        universe_complete=True,era_id="ERA_1",unresolved_source_classes=(),
    )
    vals.update(changes)
    vals["source_universe_hash"]=""
    x=SourceUniverseAuthority(**vals)
    vals["source_universe_hash"]=x.computed_hash()
    return SourceUniverseAuthority(**vals)

def manifest(ref_era="ERA_1",manifest_era="ERA_1",rows=1):
    return IdentityImportManifest(
        "M","1",manifest_era,
        (ImportSourceRef("era1:catalogue:neutral-core","neutral","CURRENT_FEATURE_DEFINITION_CATALOGUE",True,rows,ref_era),)
    )

def catalogue(era="ERA_1"):
    d=FeatureDefinitionRecord("salix.neutral.identity_anchor","1","Instrument-neutral identity anchor whose deterministic transform is identity(x)=x.","identity(x)=x",(),era,"","",None,None,"OWNER_APPROVED_ERA1_START_DIRECTION__BASELINE_CANDIDATE_UNFROZEN","TYPE_1_IDENTITY_BASELINE_CONFORMANCE")
    d=FeatureDefinitionRecord(d.feature_id,d.feature_version,d.semantic_definition,d.formula,d.dependencies,d.era_id,d.computed_definition_hash(),d.computed_graph_hash(),d.instrument,d.timeframe,d.authority,d.purpose)
    return FeatureDefinitionCatalogue("SALIX-ERA1-FEATURE-CATALOGUE",era,(d,))

def row(era="ERA_1"):
    return FeatureIdentity(
        feature_id="salix.neutral.identity_anchor",feature_version="1",
        definition_hash=catalogue(era).definitions[0].definition_hash,
        graph_hash=catalogue(era).definitions[0].graph_hash,
        lifecycle_state="VALIDATION_ONLY",is_current=True,scope="validation",era_id=era,
        import_source_id="era1:catalogue:neutral-core",
        import_source_authority_class="CURRENT_FEATURE_DEFINITION_CATALOGUE",
    )

def do_import(rows=None, store=None, man=None, uni=None, bd=None, cat=None):
    rows=(row(),) if rows is None else tuple(rows)
    store=store or CanonicalIdentityStore()
    result=import_identity_content(
        target_store=store,rows=rows,manifest=man or manifest(rows=len(rows)),
        source_universe=uni or universe(),era_boundary=bd or boundary(),catalogue=cat or catalogue(),
        search_policy=policy(),normalizer=normalizer(),
    )
    return store,result

class Era1BoundaryTests(unittest.TestCase):
    def test_valid_era1_import(self):
        store,result=do_import()
        self.assertEqual(result.errors,())
        self.assertEqual(len(store.all()),1)
        self.assertTrue(result.population_complete)

    def test_wrong_boundary_hash_fails_without_mutation(self):
        good=boundary()
        bad=CanonicalEraBoundary(**{**good.__dict__,"boundary_hash":"wrong"})
        store,result=do_import(bd=bad)
        self.assertIn("ERA_BOUNDARY_HASH_MISMATCH",result.errors)
        self.assertEqual(store.all(),())

    def test_wrong_registry_binding_fails_without_mutation(self):
        store,result=do_import(store=CanonicalIdentityStore(registry_id="WRONG"))
        self.assertIn("ERA_BOUNDARY_REGISTRY_ID_MISMATCH",result.errors)
        self.assertEqual(store.all(),())

    def test_wrong_source_universe_binding_fails_without_mutation(self):
        store,result=do_import(uni=universe(source_universe_id="OTHER"))
        self.assertIn("ERA_BOUNDARY_SOURCE_UNIVERSE_ID_MISMATCH",result.errors)
        self.assertEqual(store.all(),())

    def test_era0_row_cannot_enter_era1(self):
        store,result=do_import(rows=(row("ERA_0"),))
        self.assertTrue(any(e.startswith("ROW_ERA_MISMATCH") for e in result.errors))
        self.assertEqual(store.all(),())

    def test_era0_source_ref_cannot_enter_era1(self):
        store,result=do_import(man=manifest(ref_era="ERA_0"))
        self.assertIn("IMPORT_SOURCE_REF_ERA_MISMATCH",result.errors)
        self.assertEqual(store.all(),())

    def test_manifest_era_mismatch_fails(self):
        store,result=do_import(man=manifest(manifest_era="ERA_0",ref_era="ERA_0"))
        self.assertTrue(any("ERA_MISMATCH" in e for e in result.errors))
        self.assertEqual(store.all(),())

    def test_boundary_cannot_claim_historical_absence(self):
        store,result=do_import(bd=boundary(absent_proven=True))
        self.assertIn("HISTORICAL_ABSENT_MUST_REMAIN_UNPROVEN",result.errors)
        self.assertEqual(store.all(),())

    def test_deliberate_wrong_definition_hash_fails_without_mutation(self):
        bad=FeatureIdentity(**{**row().__dict__,"definition_hash":"0"*64})
        store,result=do_import(rows=(bad,))
        self.assertTrue(any(x.startswith("ROW_DEFINITION_HASH_MISMATCH") for x in result.errors))
        self.assertEqual(store.all(),())

    def test_deliberate_broken_dependency_graph_fails_without_mutation(self):
        bad=FeatureIdentity(**{**row().__dict__,"dependencies":("missing.feature",)})
        store,result=do_import(rows=(bad,))
        self.assertTrue(any(x.startswith("ROW_DEPENDENCY_GRAPH_MISMATCH") for x in result.errors))
        self.assertEqual(store.all(),())

    def test_deliberate_unapproved_source_fails_without_mutation(self):
        badrow=FeatureIdentity(**{**row().__dict__,"import_source_authority_class":"HISTORICAL_EXAMPLE"})
        badman=IdentityImportManifest("M","1","ERA_1",(ImportSourceRef("era1:catalogue:neutral-core","neutral","HISTORICAL_EXAMPLE",True,1,"ERA_1"),))
        store,result=do_import(rows=(badrow,),man=badman)
        self.assertTrue(any("NONCANONICAL_SOURCE_HAS_IMPORTABLE_ROWS" in x or "ROW_SOURCE_AUTHORITY_NOT_PERMITTED" in x for x in result.errors))
        self.assertEqual(store.all(),())

    def test_deliberate_catalogue_tamper_fails_without_mutation(self):
        good=catalogue().definitions[0]
        tampered=FeatureDefinitionRecord(
            good.feature_id,good.feature_version,good.semantic_definition+" tampered",good.formula,
            good.dependencies,good.era_id,good.definition_hash,good.graph_hash,good.instrument,good.timeframe,
            good.authority,good.purpose,
        )
        store,result=do_import(cat=FeatureDefinitionCatalogue("SALIX-ERA1-FEATURE-CATALOGUE","ERA_1",(tampered,)))
        self.assertTrue(any(x.startswith("CATALOGUE_DEFINITION_HASH_MISMATCH") for x in result.errors))
        self.assertEqual(store.all(),())

    def test_checked_in_boundary_and_universe_hashes(self):
        bd=json.loads((ROOT/"population"/"era1_boundary.json").read_text())
        un=json.loads((ROOT/"population"/"era1_source_universe.json").read_text())
        b=CanonicalEraBoundary(**bd)
        u=SourceUniverseAuthority(
            source_universe_id=un["source_universe_id"],version=un["version"],
            source_universe_hash=un["source_universe_hash"],authority_source_id=un["authority_source_id"],
            expected_source_ids=tuple(un["expected_source_ids"]),universe_complete=un["universe_complete"],
            era_id=un["era_id"],unresolved_source_classes=tuple(un["unresolved_source_classes"]),
        )
        self.assertEqual(b.boundary_hash,b.computed_hash())
        self.assertEqual(u.source_universe_hash,u.computed_hash())

if __name__=="__main__":
    unittest.main()
