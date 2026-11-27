"""R12: source-bound resource ceilings + capability declaration. No numeric ceiling is chosen by the code; absence refuses."""
import copy, dataclasses, unittest
from stage_a.errors import Refusal
from stage_a.composer.expression import ceilings as C
from stage_a.composer.expression.manifest import Manifest
from stage_a.tracker.quant_intake_adapter import admit, FAILED_REQUESTED_BUILD, QUANT_FEATURE
from tests.trk_stage_a.fixtures import package, CEILINGS, momentum_manifest, declaration_for

def codes(a, dim): return [c for d, c in a.failed if d == dim]
def adm(**over): return admit(package(**over), accepted_fit_generations={})
def cc(**ch):
    v = dict(CEILINGS); v.update(ch); return v

class Ceilings(unittest.TestCase):
    def test_valid_admits(self): self.assertEqual(adm().classification, QUANT_FEATURE)
    def test_absent_ref_refused_and_nothing_defaulted(self):
        a = adm(resource_ceiling_ref=None)
        self.assertEqual(codes(a, "RESOURCE_CEILING"), ["RESOURCE_CEILING_REF_MISSING"]); self.assertEqual(a.classification, FAILED_REQUESTED_BUILD)
        self.assertEqual(codes(adm(resource_ceiling_ref="  "), "RESOURCE_CEILING"), ["RESOURCE_CEILING_REF_MISSING"])
    def test_absent_values_refused(self):
        self.assertEqual(codes(adm(resource_ceilings=None), "RESOURCE_CEILING"), ["RESOURCE_CEILINGS_NOT_SUPPLIED"])
    def test_each_missing_ceiling_refused(self):
        for k in C.CEILING_KEYS:
            v = dict(CEILINGS); del v[k]
            self.assertEqual(codes(adm(resource_ceilings=v), "RESOURCE_CEILING"), ["RESOURCE_CEILING_VALUE_MISSING"], k)
    def test_non_integer_negative_bool_refused(self):
        for bad in (-1, 1.5, "5", True, None):
            self.assertEqual(codes(adm(resource_ceilings=cc(MAX_BRANCH_COUNT=bad)), "RESOURCE_CEILING"),
                             ["RESOURCE_CEILING_NOT_A_NONNEGATIVE_INTEGER"], repr(bad))
    def test_opcode_count_ceiling(self):
        n = len(momentum_manifest()["nodes"])
        self.assertEqual(adm(resource_ceilings=cc(MAX_OPCODE_COUNT_PER_PROGRAM=n)).classification, QUANT_FEATURE)
        self.assertEqual(codes(adm(resource_ceilings=cc(MAX_OPCODE_COUNT_PER_PROGRAM=n - 1)), "SCHEMA"), ["CEILING_OPCODE_COUNT_EXCEEDED"])
    def test_reduction_ceiling(self):
        w = max(x["n"] for x in momentum_manifest()["nodes"] if x["op"] in C.REDUCTION_OPS)
        self.assertEqual(adm(resource_ceilings=cc(MAX_REDUCTION_LENGTH=w)).classification, QUANT_FEATURE)
        self.assertEqual(codes(adm(resource_ceilings=cc(MAX_REDUCTION_LENGTH=w - 1)), "SCHEMA"), ["CEILING_REDUCTION_LENGTH_EXCEEDED"])
    def test_no_silent_numeric_default_remains_in_schema(self):
        from stage_a.composer.expression import schema
        self.assertFalse(hasattr(schema, "MAX_NODES") or hasattr(schema, "MAX_WINDOW"))
        big = momentum_manifest(); 
        Manifest.from_dict(big)                                                   # structural parse assumes no bound
    def test_ceilings_are_bound_into_package_hash(self):
        a = package(); b = dataclasses.replace(a, resource_ceilings=cc(MAX_BRANCH_COUNT=9))
        self.assertNotEqual(a.content_hash(), b.content_hash())
        c = dataclasses.replace(a, resource_ceiling_ref="OTHER"); self.assertNotEqual(a.content_hash(), c.content_hash())

class CapabilityDeclaration(unittest.TestCase):
    def test_missing_declaration_refused(self):
        self.assertEqual(codes(adm(capability_declaration=None), "CAPABILITY_DECLARATION"), ["CAPABILITY_DECLARATION_MISSING"])
    def test_class_outside_enum_routes_generic_extension(self):
        d = declaration_for(momentum_manifest()); 
        for bad in ("EGARCH", "MATRIX_SOLVE", None, "scalar_recurrence"):
            d["PROGRAM_CAPABILITY_CLASS"] = bad
            self.assertEqual(codes(adm(capability_declaration=dict(d)), "CAPABILITY_DECLARATION"), ["CAPABILITY_CLASS_NOT_ADMITTED_ROUTE_GENERIC_EXTENSION"], bad)
    def test_every_enum_class_is_accepted_shape(self):
        for k in C.CAPABILITY_CLASSES:
            d = declaration_for(momentum_manifest()); d["PROGRAM_CAPABILITY_CLASS"] = k
            self.assertEqual(codes(adm(capability_declaration=d), "CAPABILITY_DECLARATION"), [], k)
    def test_opcode_set_must_equal_program_and_have_no_duplicates(self):
        d = declaration_for(momentum_manifest()); d["OPCODE_SET_USED"] = d["OPCODE_SET_USED"][:-1]
        self.assertEqual(codes(adm(capability_declaration=d), "CAPABILITY_DECLARATION"), ["OPCODE_SET_USED_DIFFERS_FROM_PROGRAM"])
        d = declaration_for(momentum_manifest()); d["OPCODE_SET_USED"] = d["OPCODE_SET_USED"] + d["OPCODE_SET_USED"][:1]
        self.assertEqual(codes(adm(capability_declaration=d), "CAPABILITY_DECLARATION"), ["OPCODE_SET_USED_INVALID_OR_DUPLICATE"])
    def test_declaration_must_name_the_same_ceiling_ref(self):
        d = declaration_for(momentum_manifest(), ref="OTHER")
        self.assertEqual(codes(adm(capability_declaration=d), "CAPABILITY_DECLARATION"), ["DECLARATION_CEILING_REF_DIFFERS"])
    def test_program_ref_required(self):
        d = declaration_for(momentum_manifest()); d["PROGRAM_REF"] = ""
        self.assertEqual(codes(adm(capability_declaration=d), "CAPABILITY_DECLARATION"), ["CAPABILITY_DECLARATION_PROGRAM_REF_MISSING"])
if __name__ == "__main__": unittest.main()
