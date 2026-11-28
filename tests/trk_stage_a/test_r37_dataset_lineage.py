"""R37 F1: a supplied generation lineage may never replace or shadow a declared dataset union (ML Integration Addendum s3/s7: ancestry is not erased)."""
import unittest
from stage_a.ml import dataset_manifest as DM, dataset_authority as DA, generation_lifecycle as GL
from .test_r36_dataset_authority import Rig, code
from .test_r35_dataset_manifest import ds
from .test_r29_generation_lifecycle import man

def rig():
    r = Rig()
    for i in ("D1", "D2", "D3"): r.reg.register("w", ds(i))
    for g in ("G1", "G2"):
        r.gr.register_manifest(man(g)); r.gr.append_lifecycle(g, "COMPLETE_CERTIFIED", 1, "c", "A")
    return r
class UnionNotOverwritten(unittest.TestCase):
    def test_reported_defect_supplied_map_keyed_by_a_dataset_cannot_erase_the_declared_union(self):
        r = rig(); a = r.auth; a.declare_union("w", "D1", ("D2",)); a.declare_union("w", "D2", ())
        self.assertEqual(a.gate("D1")["verdict"], "CLEAR"); r.reg.revoke("w", "D2", 5, "contamination", "AUTH"); self.assertEqual(a.gate("D1")["verdict"], "BLOCKED")
        self.assertEqual(code(a.gate, "D1", {"D1": []}), "GENERATION_LINEAGE_KEY_IS_DATASET_NOT_GENERATION")        # the exact reported call now refuses (it used to return CLEAR)
        self.assertEqual(a.union_of("D1"), (("D2",), ())); self.assertEqual(a.derived_from()["D1"], ["D2"]); self.assertEqual(a.gate("D1")["verdict"], "BLOCKED")   # ancestry intact
        self.assertEqual(code(a.derived_from, {"D2": []}), "GENERATION_LINEAGE_KEY_IS_DATASET_NOT_GENERATION")
    def test_unknown_key_and_malformed_maps_refuse_not_ignored(self):
        a = rig().auth; a.declare_union("w", "D1", (), ("G1",))
        for bad in ({"NOPE": []}, {"G1": "x"}, {"G1": [1]}, {"": []}, ["G1"]): self.assertIn(code(a.gate, "D1", bad), ("GENERATION_LINEAGE_KEY_UNKNOWN_GENERATION", "GENERATION_LINEAGE_MALFORMED"), bad)
    def test_real_generation_lineage_positive_and_revoked_contributor_negative_with_unrelated_baseline(self):
        r = rig(); a = r.auth; a.declare_union("w", "D1", (), ("G1",)); a.declare_union("w", "D3", ("D2",)); a.declare_union("w", "D2", ())
        self.assertEqual(a.gate("D1")["verdict"], "BLOCKED_UNKNOWN")                                                  # generation G1 lineage not supplied: not clean
        self.assertEqual(a.gate("D1", {"G1": []})["verdict"], "CLEAR")                                                 # positive: a registered generation, an explicit leaf
        self.assertEqual(a.gate("D1", {"G1": ["G2"], "G2": []})["verdict"], "CLEAR")                                             # a real second generation contributor
        r.gr.append_lifecycle("G2", "REVOKED", 9, "bad", "A")
        self.assertEqual(a.gate("D1", {"G1": ["G2"], "G2": []})["verdict"], "BLOCKED")                                           # negative: revoked contributor behind a generation
        self.assertEqual(a.gate("D3")["verdict"], "CLEAR")                                                             # unrelated baseline untouched
    def test_a_node_id_naming_both_a_dataset_and_a_generation_is_ambiguous_never_resolved_by_guess(self):
        r = rig(); a = r.auth; r.reg.register("w", ds("G1"))                                                          # dataset id equal to a generation manifest id
        self.assertEqual(code(a.declare_union, "w", "D1", ("G1",)), "UNION_NODE_ID_AMBIGUOUS"); self.assertEqual(code(a.declare_union, "w", "D2", (), ("G1",)), "UNION_NODE_ID_AMBIGUOUS")
        a.declare_union("w", "D1", ()); self.assertEqual(code(a.gate, "D1", {"G1": []}), "GENERATION_LINEAGE_KEY_IS_DATASET_NOT_GENERATION")
        r2 = rig(); r2.auth.declare_union("w", "D1", (), ("G1",)); r2.reg.register("w", ds("G1"))                       # ambiguity arising AFTER the union was declared
        v = r2.auth.gate("D1"); self.assertEqual((v["verdict"], v["report"]["reason"]), ("BLOCKED_UNKNOWN", "NODE_ID_NAMES_BOTH_DATASET_AND_GENERATION"))
if __name__ == "__main__": unittest.main()
