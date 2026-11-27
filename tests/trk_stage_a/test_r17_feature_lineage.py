"""R17: feature_deps derived from QuantManifest.input_dependencies feeds blast radius. Ref-type vocabulary is D3-open (caller-supplied); instances are test values."""
import dataclasses, unittest
from stage_a.errors import Refusal
from stage_a.schema.encoding import Ref
from stage_a.tracker.feature_lineage import feature_deps_from_quant_manifests as D
from stage_a.health import blast_radius as BR
from tests.trk_stage_a.test_schema_annex import manifest

def fid(n): return bytes([n]) * 16
def m(n, *deps, extra=()):
    return manifest(feature_id=fid(n), input_dependencies=tuple(("in%d" % i, Ref("ROW", fid(d))) for i, d in enumerate(deps)) + tuple(extra) or (("x", Ref("RULE", b"r")),))
def code(fn, *a):
    try: fn(*a)
    except Refusal as e: return e.code
class Lineage(unittest.TestCase):
    FT = {"ROW"}
    def test_ref_types_are_required_not_defaulted(self):
        for bad in (None, (), set()): self.assertEqual(code(D, [m(1)], bad), "FEATURE_REF_TYPES_REQUIRED_D3_VOCABULARY")
    def test_only_feature_typed_refs_count(self):
        d = D([m(1, 2, extra=(("src", Ref("RULE", b"not-a-feature")),)), m(2, 3), m(3, extra=(("s", Ref("RULE", b"r")),))], self.FT)
        self.assertEqual(d, {fid(1): (fid(2),), fid(2): (fid(3),), fid(3): ()})
    def test_non_manifest_and_self_dependency_refuse(self):
        self.assertEqual(code(D, [object()], self.FT), "NOT_A_QUANT_MANIFEST")
        self.assertEqual(code(D, [m(1, 1)], self.FT), "FEATURE_DEPENDS_ON_ITSELF")
    def test_feeds_blast_radius_complete_lineage(self):
        d = D([m(1), m(2, 1), m(3, 2), m(9)], self.FT)
        aff, incomplete = BR.downstream_features(fid(1), d)
        self.assertEqual((aff, incomplete), ({fid(1), fid(2), fid(3)}, False))                 # transitive dependents; unrelated feature 9 untouched (positive control)
        self.assertNotIn(fid(9), aff)
    def test_dependency_target_without_a_supplied_manifest_makes_lineage_incomplete_not_unaffected(self):
        d = D([m(2, 7)], self.FT)                                                              # feature 7's own lineage was never supplied
        self.assertTrue(BR.downstream_features(fid(1), d)[1])
class Determinism(unittest.TestCase):
    def test_dependency_tuples_are_sorted_not_set_order(self):
        d = D([m(1, *range(40, 20, -1))], {"ROW"})
        self.assertEqual(d[fid(1)], tuple(sorted(fid(n) for n in range(21, 41))))
if __name__ == "__main__": unittest.main()
