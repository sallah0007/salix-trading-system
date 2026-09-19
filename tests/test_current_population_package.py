import json
import pathlib
import unittest

ROOT=pathlib.Path(__file__).resolve().parents[1]

class CurrentPopulationPackageTests(unittest.TestCase):
    def test_legacy_recovery_package_remains_unresolved_and_nonimportable(self):
        data=json.loads((ROOT/"population"/"current_source_manifest.json").read_text())
        universe=json.loads((ROOT/"population"/"current_source_universe.json").read_text())
        rows=json.loads((ROOT/"population"/"current_identity_rows.json").read_text())
        self.assertEqual(rows,[])
        self.assertFalse(universe["universe_complete"])
        self.assertTrue(universe["unresolved_source_classes"])
        self.assertNotIn("era_id",data)
        self.assertNotIn("era_id",universe)

    def test_era1_package_is_separate_from_legacy_recovery_package(self):
        era1=json.loads((ROOT/"population"/"era1_boundary.json").read_text())
        self.assertEqual(era1["era_id"],"ERA_1")
        self.assertEqual(era1["predecessor_era_id"],"ERA_0")
        self.assertFalse(era1["absent_proven"])

if __name__=="__main__":
    unittest.main()
