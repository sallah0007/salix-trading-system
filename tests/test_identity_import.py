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
    instrument_applicability="INSTRUMENT_SPECIFIC",
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

def approve_package(*,era_boundary,source_universe,manifest,catalogue,**_ignored):
    """TEST ONLY (DC-006R). Pin exactly THIS package in the approved-import
    registry for one block, by code replacement (mock). Production has no such
    path: its registry is empty and read-only."""
    from unittest import mock
    from tracker_identity import import_package_registry as reg
    entry=reg.ApprovedImportPackageEntry(
        "TEST-FIXTURE-PACKAGE",
        *reg.package_hashes(era_boundary=era_boundary,source_universe=source_universe,
                            manifest=manifest,catalogue=catalogue),
        approval_ref="TEST-FIXTURE:not-a-governed-approval")
    return mock.patch.object(reg,"APPROVED_IMPORT_PACKAGE_REGISTRY",reg._build_registry((entry,)))

def run(rows,man,uni=None,store=None):
    store=store or CanonicalIdentityStore()
    package=dict(manifest=man,source_universe=uni or universe(),era_boundary=boundary(),
                 catalogue=catalogue(rows[0].feature_id if rows else "f1"))
    with approve_package(**package):
        result=import_identity_content(
            target_store=store,rows=tuple(rows),**package,search_policy=policy(),normalizer=normalizer())
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

class ImportAuthorityBoundaryA14006(unittest.TestCase):
    """DC-006 Correction C — the GOVERNED IMPORT write path.

    The import is NOT forced through the construction claim. It writes only
    through the store-owned import commit, which re-runs the whole contract;
    store.extend no longer exists as an escape hatch.
    """

    def _ok_contract(self,store):
        return dict(rows=(row(),),manifest=manifest((ref(),)),source_universe=universe(),
                    era_boundary=boundary(),catalogue=catalogue("f1"),
                    search_policy=policy(),normalizer=normalizer())

    def test_valid_import_writes_through_the_governed_commit(self):
        store,result=run((row(),),manifest((ref(),)))
        self.assertEqual(result.errors,())
        self.assertEqual(result.imported_row_count,1)
        self.assertEqual(len(store.all()),1)
        self.assertTrue(store.all()[0].content_key_composite)   # catalogue-derived

    def test_generator_rows_are_materialized_once(self):
        store=CanonicalIdentityStore()
        c=self._ok_contract(store); c["rows"]=(r for r in (row(),))
        with approve_package(**c):
            result=import_identity_content(target_store=store,**c)
        self.assertEqual(result.errors,())
        self.assertEqual(len(store.all()),1)

    def test_planning_alone_never_writes(self):
        from tracker_identity.importer import _plan_identity_import
        store=CanonicalIdentityStore()
        c=self._ok_contract(store)
        with approve_package(**c):
            planned,result=_plan_identity_import(target_store=store,**c)
        self.assertEqual(len(planned),1)
        self.assertEqual(result.errors,())
        self.assertEqual(store.all(),())

    def test_direct_store_import_commit_cannot_skip_the_contract(self):
        """Calling the store-owned import writer directly is exactly as strong
        as import_identity_content: it re-runs every check itself."""
        from tracker_identity import store as store_module
        store=CanonicalIdentityStore()
        bad=[
            dict(manifest=manifest((ref(rows=2),))),                       # row count
            dict(rows=(row(authority="MANAGER_RECORD"),),
                 manifest=manifest((ref(authority="MANAGER_RECORD"),))),     # authority class
            dict(rows=(row(source_id=""),)),                                # provenance
            dict(rows=(row(era="ERA_0"),)),                                 # era
            dict(catalogue=catalogue("other")),                             # not in catalogue
        ]
        for over in bad:
            c=self._ok_contract(store); c.update(over)
            with approve_package(**c):     # approved: every OTHER check must still refuse
                result=store_module._commit_governed_import(store,**c)
            self.assertNotIn("IMPORT_PACKAGE_NOT_APPROVED",result.errors)
            self.assertTrue(result.errors,over)
            self.assertEqual(result.imported_row_count,0)
            self.assertEqual(store.all(),(),over)

    def test_supplied_content_key_is_never_trusted(self):
        from dataclasses import replace
        store=CanonicalIdentityStore()
        c=self._ok_contract(store); c["rows"]=(replace(row(),content_key_composite="FORGED"),)
        with approve_package(**c):
            result=import_identity_content(target_store=store,**c)
        self.assertTrue(any("ROW_SUPPLIED_CONTENT_KEY_REJECTED" in e for e in result.errors))
        self.assertEqual(store.all(),())

    def test_duplicate_and_currentness_checks_not_weakened(self):
        store,first=run((row(),),manifest((ref(),)))
        self.assertEqual(len(store.all()),1)
        _,second=run((row(),),manifest((ref(),)),store=store)
        self.assertIn("STALE_STATE_SWEEP_FAILED",second.errors)
        self.assertEqual(len(store.all()),1)

    def test_staging_copy_cannot_be_imported_into(self):
        from tracker_identity import store as store_module
        staged=store_module._staging_copy(CanonicalIdentityStore())
        c=self._ok_contract(staged)
        with approve_package(**c):
            result=import_identity_content(target_store=staged,**c)
        self.assertIn("STORE_IS_STAGING_COPY",result.errors)
        self.assertEqual(staged.all(),())

    def test_import_has_no_extend_escape_hatch(self):
        store=CanonicalIdentityStore()
        self.assertFalse(hasattr(store,"extend"))
        self.assertFalse(hasattr(store,"add"))

    def test_self_consistent_fake_package_cannot_write(self):
        """DC-006R inverted the DC-006 residual pin. A caller-built, fully
        self-consistent package (every self-hash verifies, approval_authority
        says OWNER) is NOT in the governed registry, so it writes nothing."""
        store=CanonicalIdentityStore()
        c=self._ok_contract(store)
        self.assertEqual(c["era_boundary"].completeness_errors(),())
        self.assertEqual(c["era_boundary"].approval_authority,"OWNER")
        result=import_identity_content(target_store=store,**c)
        self.assertIn("IMPORT_PACKAGE_NOT_APPROVED",result.errors)
        self.assertEqual(result.imported_row_count,0)
        self.assertEqual(store.all(),())


class ApprovedImportPackageRegistry006R(unittest.TestCase):
    """DC-006R Correction C: APPROVED_IMPORT_PACKAGE_REGISTRY."""

    def _package(self):
        return dict(rows=(row(),),manifest=manifest((ref(),)),source_universe=universe(),
                    era_boundary=boundary(),catalogue=catalogue("f1"),
                    search_policy=policy(),normalizer=normalizer())

    def _entry(self,c,**over):
        from tracker_identity import import_package_registry as reg
        vals=dict(zip(("era_boundary_hash","source_universe_hash","import_manifest_hash",
                       "catalogue_hash"),reg.package_hashes(**{k:c[k] for k in (
                           "era_boundary","source_universe","manifest","catalogue")})))
        vals.update(package_id="P",approval_ref="DRIVE:governed-approval-ref")
        vals.update(over)
        return reg.ApprovedImportPackageEntry(**vals)

    def test_C1_production_registry_is_empty_and_import_is_closed(self):
        from tracker_identity import import_package_registry as reg
        self.assertEqual(len(reg.APPROVED_IMPORT_PACKAGE_REGISTRY),0)
        self.assertEqual(reg._ENTRIES,())
        store=CanonicalIdentityStore()
        result=import_identity_content(target_store=store,**self._package())
        self.assertIn("IMPORT_PACKAGE_NOT_APPROVED",result.errors)
        self.assertEqual(store.all(),())

    def test_C2_registry_is_runtime_immutable(self):
        from tracker_identity import import_package_registry as reg
        registry=reg.APPROVED_IMPORT_PACKAGE_REGISTRY
        entry=self._entry(self._package())
        with self.assertRaises(TypeError):
            registry[entry.key]=entry
        with self.assertRaises(TypeError):
            del registry[("x",)]
        for name in ("update","setdefault","pop","popitem","clear"):
            self.assertFalse(hasattr(registry,name),name)
        with self.assertRaises(AttributeError):
            entry.approval_ref="OTHER"                          # frozen entry
        self.assertIsInstance(reg._ENTRIES,tuple)
        # No module-level backing dict to reach around the read-only view.
        self.assertFalse(any(isinstance(v,dict) for k,v in vars(reg).items()
                             if not k.startswith("__")))

    def test_C3_approved_package_imports_and_any_change_refuses(self):
        from unittest import mock
        from dataclasses import replace
        from tracker_identity import import_package_registry as reg
        c=self._package()
        with mock.patch.object(reg,"APPROVED_IMPORT_PACKAGE_REGISTRY",
                               reg._build_registry((self._entry(c),))):
            store=CanonicalIdentityStore()
            result=import_identity_content(target_store=store,**c)
            self.assertEqual(result.errors,())
            self.assertEqual(len(store.all()),1)
            # Same shape, one catalogue field different: a different package.
            cat=c["catalogue"]
            d=replace(cat.definitions[0],purpose="tampered")
            other=dict(c,catalogue=replace(cat,definitions=(d,)))
            store2=CanonicalIdentityStore()
            r2=import_identity_content(target_store=store2,**other)
            self.assertIn("IMPORT_PACKAGE_NOT_APPROVED",r2.errors)
            self.assertEqual(store2.all(),())
            # Different manifest id: a different package.
            other=dict(c,manifest=replace(c["manifest"],manifest_id="M2"))
            r3=import_identity_content(target_store=CanonicalIdentityStore(),**other)
            self.assertIn("IMPORT_PACKAGE_NOT_APPROVED",r3.errors)

    def test_C4_approval_strings_are_not_authorization(self):
        from tracker_identity import import_package_registry as reg
        c=self._package()
        for ref_value in ("OWNER","owner"," MANAGER ","APPROVED","","  ",None):
            e=self._entry(c,approval_ref=ref_value)
            self.assertTrue(e.registry_errors(),repr(ref_value))
            with self.assertRaises(RuntimeError):
                reg._build_registry((e,))
        self.assertEqual(self._entry(c).registry_errors(),())

    def test_C5_malformed_registry_entries_are_refused(self):
        from tracker_identity import import_package_registry as reg
        c=self._package()
        good=self._entry(c)
        for bad in (self._entry(c,catalogue_hash="abc"),
                    self._entry(c,era_boundary_hash=good.era_boundary_hash.upper()),
                    self._entry(c,package_id="")):
            with self.assertRaises(RuntimeError):
                reg._build_registry((bad,))
        with self.assertRaises(RuntimeError):
            reg._build_registry((good,good))                    # duplicate
        with self.assertRaises(RuntimeError):
            reg._build_registry((object(),))                    # wrong type

    def test_C6_integrity_is_revalidated_at_use(self):
        from unittest import mock
        from types import MappingProxyType
        from dataclasses import replace
        from tracker_identity import import_package_registry as reg
        c=self._package()
        good=self._entry(c)
        pkg={k:c[k] for k in ("era_boundary","source_universe","manifest","catalogue")}
        class Lookalike: pass
        for planted,code in ((Lookalike(),"IMPORT_PACKAGE_ENTRY_TYPE_INVALID"),
                             (replace(good,approval_ref="OWNER"),"IMPORT_PACKAGE_ENTRY_INTEGRITY_FAILED"),
                             (replace(good,catalogue_hash="0"*64),"IMPORT_PACKAGE_ENTRY_KEY_MISMATCH")):
            with mock.patch.object(reg,"APPROVED_IMPORT_PACKAGE_REGISTRY",
                                   MappingProxyType({good.key:planted})):
                errors=reg.resolve_approved_import_package(**pkg)
            self.assertTrue(errors and errors[0].startswith(code),(code,errors))

    def test_C7_declared_hash_fields_are_never_the_package_identity(self):
        """Copying an approved package's hash STRINGS does not make another
        package approved: identity is recomputed from content."""
        from unittest import mock
        from dataclasses import replace
        from tracker_identity import import_package_registry as reg
        c=self._package()
        with mock.patch.object(reg,"APPROVED_IMPORT_PACKAGE_REGISTRY",
                               reg._build_registry((self._entry(c),))):
            forged_uni=replace(universe(expected=("s","t")),
                               source_universe_hash=c["source_universe"].source_universe_hash)
            errors=reg.resolve_approved_import_package(
                era_boundary=c["era_boundary"],source_universe=forged_uni,
                manifest=c["manifest"],catalogue=c["catalogue"])
            self.assertEqual(errors,("IMPORT_PACKAGE_NOT_APPROVED",))


class CommitStageStagedGuardF6006R(unittest.TestCase):
    """DC-006R Correction D: F6 is killable, not equivalent. The planner's
    staged check is bypassed by test instrumentation; the store's commit-stage
    guard must refuse on its own AND report the refusal."""

    def test_F6_commit_stage_guard_refuses_independently(self):
        from unittest import mock
        from tracker_identity import importer, store as store_module
        from tracker_identity.importer import _plan_identity_import
        staged=store_module._staging_copy(CanonicalIdentityStore())
        c=dict(rows=(row(),),manifest=manifest((ref(),)),source_universe=universe(),
               era_boundary=boundary(),catalogue=catalogue("f1"),
               search_policy=policy(),normalizer=normalizer())
        with approve_package(**c), mock.patch.object(importer,"_is_staged",lambda s: False):
            planned,_=_plan_identity_import(target_store=staged,**c)
            self.assertIsNotNone(planned)          # planner really was bypassed
            result=store_module._commit_governed_import(staged,**c)
        self.assertEqual(result.errors,("STORE_IS_STAGING_COPY",))
        self.assertEqual(result.imported_row_count,0)
        self.assertFalse(result.population_complete)
        self.assertEqual(staged.all(),())

    def test_F6b_planner_staged_check_refuses_independently(self):
        """The converse: the planner's own staged check, with no commit stage."""
        from tracker_identity import store as store_module
        from tracker_identity.importer import _plan_identity_import
        staged=store_module._staging_copy(CanonicalIdentityStore())
        c=dict(rows=(row(),),manifest=manifest((ref(),)),source_universe=universe(),
               era_boundary=boundary(),catalogue=catalogue("f1"),
               search_policy=policy(),normalizer=normalizer())
        with approve_package(**c):
            planned,result=_plan_identity_import(target_store=staged,**c)
        self.assertIsNone(planned)
        self.assertIn("STORE_IS_STAGING_COPY",result.errors)

if __name__=="__main__":
    unittest.main()
