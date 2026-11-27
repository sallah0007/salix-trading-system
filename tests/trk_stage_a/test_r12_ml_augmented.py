import dataclasses, unittest
from stage_a.errors import Refusal
from stage_a.fw.lanes import ConsumerManifest as M
from stage_a.ml import receiver as R
from tests.trk_stage_a import test_boundaries as B
Q = b"quant"
def aug(gw_b=None):
    gw, bd = gw_b or B._bound(); ref = B.R("x")
    return gw, R.AugmentedInput(ref, ref, ref, ref, bd, ref, ref)
def code(fn, *a, **k):
    try: return fn(*a, **k)
    except Refusal as e: return e.code
FWML = lambda: {"fw": M("fw", "FW", (b"a",)), "ml": M("ml", "ML", (b"a",), derived_from="fw")}
class T(unittest.TestCase):
    def test_declared_fw_parent_with_issued_rebind_is_verified(self):
        g = FWML(); gw, a = aug(); c = R.check_fw_augmented(g["ml"], a, Q, g, gateway=gw)
        self.assertEqual((c.lane, c.rebind_verified, c.status), ("BASELINE", True, "VERIFIED_ISSUED_BINDING")); self.assertEqual(R.require_verified(c), "BASELINE")
    def test_without_a_gateway_the_result_is_unverified_and_not_reliable(self):
        g = FWML(); _, a = aug(); c = R.check_fw_augmented(g["ml"], a, Q, g)
        self.assertEqual((c.rebind_verified, c.status), (False, "UNVERIFIED_SHAPE_ONLY"))
        self.assertEqual(code(R.require_verified, c), "AUGMENTED_REBIND_UNVERIFIED")
        self.assertEqual(code(R.require_verified, "BASELINE"), "AUGMENTED_REBIND_UNVERIFIED")             # a bare lane string is not a verified result
    def test_well_typed_but_unissued_binding_refused(self):
        g = FWML(); gw, a = aug(); other, _ = B._bound()                 # a second, independent gateway that never issued `a`'s binding
        self.assertEqual(code(R.check_fw_augmented, g["ml"], a, Q, g, gateway=other), "BINDING_NOT_FROM_GATEWAY")
        forged = dataclasses.replace(a.gateway_rebind, request_id="NOT-ISSUED")
        ref = B.R("x"); fa = R.AugmentedInput(ref, ref, ref, ref, forged, ref, ref)
        self.assertEqual(code(R.check_fw_augmented, g["ml"], fa, Q, g, gateway=gw), "BINDING_NOT_FROM_GATEWAY")
        copy = dataclasses.replace(a.gateway_rebind)                    # equal but not the issued object
        self.assertEqual(code(R.check_fw_augmented, g["ml"], R.AugmentedInput(ref, ref, ref, ref, copy, ref, ref), Q, g, gateway=gw), "BINDING_NOT_FROM_GATEWAY")
    def test_hidden_quant_ancestor_through_fw_parent_refused(self):
        g = {"fw": M("fw", "FW", (Q,)), "ml": M("ml", "ML", (b"a",), derived_from="fw")}; gw, a = aug()
        self.assertEqual(code(R.check_fw_augmented, g["ml"], a, Q, g, gateway=gw), "HIDDEN_QUANT_ANCESTOR")
    def test_must_be_ml(self):
        g = {"fw": M("fw", "FW", ())}; self.assertEqual(code(R.check_fw_augmented, g["fw"], aug()[1], Q, g), "AUGMENTED_REQUIRES_ML_MANIFEST")
    def test_no_fw_parent_refused(self):
        g = {"ml": M("ml", "ML", ())}; self.assertEqual(code(R.check_fw_augmented, g["ml"], aug()[1], Q, g), "AUGMENTED_WITHOUT_FW_ANCESTRY")
    def test_unresolved_parent_refused(self):
        g = {"ml": M("ml", "ML", (), derived_from="zz")}; self.assertEqual(code(R.check_fw_augmented, g["ml"], aug()[1], Q, g), "DERIVED_FROM_UNRESOLVED")
    def test_non_fw_parent_refused(self):
        g = {"p": M("p", "ML", ()), "ml": M("ml", "ML", (), derived_from="p")}
        self.assertEqual(code(R.check_fw_augmented, g["ml"], aug()[1], Q, g), "AUGMENTED_PARENT_NOT_FW")
    def test_cyclic_ancestry_refused_before_any_parent_is_trusted(self):
        g = {"fw": M("fw", "FW", (), derived_from="ml"), "ml": M("ml", "ML", (), derived_from="fw")}
        self.assertEqual(code(R.check_fw_augmented, g["ml"], aug()[1], Q, g), "DERIVATION_CYCLE")
    def test_non_augmented_input_refused(self):
        g = FWML(); self.assertEqual(code(R.check_fw_augmented, g["ml"], None, Q, g), "NO_GATEWAY_REBIND")
    def test_standalone_still_rejects_fw_ancestry(self):
        g = {"fw": M("fw", "FW", ()), "ml": M("ml", "ML", (), derived_from="fw")}
        self.assertEqual(code(R.check_generation, g["ml"], Q, g, "ML_STANDALONE"), "HIDDEN_FW_ANCESTRY")
class AugmentedInputStructure(unittest.TestCase):
    def kw(self):
        _, b = B._bound(); ref = B.R("x")
        return dict(fw_lineage_ref=ref, uncertainty_ref=ref, ood_ref=ref, dependency_interval_ref=ref, gateway_rebind=b, fw_generation_identity_ref=ref, research_exposure_ref=ref)
    def test_each_ref_is_required(self):
        for n in ("fw_lineage_ref", "uncertainty_ref", "ood_ref", "dependency_interval_ref", "fw_generation_identity_ref", "research_exposure_ref"):
            k = self.kw(); k[n] = None; self.assertEqual(code(R.AugmentedInput, **k), "AUGMENTED_FIELD_MISSING", n)
    def test_arbitrary_objects_are_not_refs(self):
        for n in ("fw_lineage_ref", "uncertainty_ref", "ood_ref", "dependency_interval_ref", "fw_generation_identity_ref", "research_exposure_ref"):
            for bad in (object(), "x", b"x", 1):
                k = self.kw(); k[n] = bad; self.assertEqual(code(R.AugmentedInput, **k), "AUGMENTED_FIELD_MALFORMED", (n, bad))
    def test_rebind_must_be_a_binding_with_a_request_id(self):
        from types import SimpleNamespace
        k = self.kw(); k["gateway_rebind"] = SimpleNamespace(request_id="NOT-ISSUED"); self.assertEqual(code(R.AugmentedInput, **k), "NO_GATEWAY_REBIND")
        k = self.kw(); k["gateway_rebind"] = dataclasses.replace(k["gateway_rebind"], request_id=""); self.assertEqual(code(R.AugmentedInput, **k), "NO_GATEWAY_REBIND")
        k = self.kw(); k["gateway_rebind"] = None; self.assertEqual(code(R.AugmentedInput, **k), "NO_GATEWAY_REBIND")
if __name__ == "__main__": unittest.main()
