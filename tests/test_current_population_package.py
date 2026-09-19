import json
import pathlib
import unittest

from tracker_identity import CanonicalIdentityStore, NormalizerSpec, SearchPolicy
from tracker_identity.importer import IdentityImportManifest, ImportSourceRef, import_identity_content

ROOT=pathlib.Path(__file__).resolve().parents[1]

class CurrentPopulationPackageTests(unittest.TestCase):
    def test_current_package_cannot_claim_population_complete(self):
        data=json.loads((ROOT/"population"/"current_source_manifest.json").read_text())
        rows=json.loads((ROOT/"population"/"current_identity_rows.json").read_text())

        refs=tuple(ImportSourceRef(**r) for r in data["source_refs"])
        manifest=IdentityImportManifest(
            manifest_id=data["manifest_id"],
            version=data["version"],
            source_refs=refs,
            declared_source_universe_complete=data["declared_source_universe_complete"],
            unresolved_source_classes=tuple(data["unresolved_source_classes"]),
        )

        p=SearchPolicy(
            policy_id="population-validation",version="1",policy_hash="",
            required_scopes=("current_active",),searched_scopes=("current_active",),
            scope_exclusions={},
        )
        p=SearchPolicy(
            policy_id=p.policy_id,version=p.version,policy_hash=p.computed_hash(),
            required_scopes=p.required_scopes,searched_scopes=p.searched_scopes,
            scope_exclusions=p.scope_exclusions,
        )
        n=NormalizerSpec(
            normalizer_id="population-validation",version="1",normalizer_hash="",
            equivalence_classes=("EXACT_STRUCTURAL_IDENTITY",),
        )
        n=NormalizerSpec(
            normalizer_id=n.normalizer_id,version=n.version,
            normalizer_hash=n.computed_hash(),equivalence_classes=n.equivalence_classes,
        )

        result=import_identity_content(
            target_store=CanonicalIdentityStore(),
            rows=tuple(rows),
            manifest=manifest,
            search_policy=p,
            normalizer=n,
        )
        self.assertEqual(result.imported_row_count,0)
        self.assertFalse(result.population_complete)
        self.assertTrue(manifest.unresolved_source_classes)

if __name__=="__main__":
    unittest.main()
