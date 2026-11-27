import unittest
from stage_a.errors import Refusal
from stage_a.fw.lanes import ConsumerManifest as M
from stage_a.ml import receiver as R
from stage_a.schema.encoding import Ref
from tests.trk_stage_a import test_boundaries as B
Q = b"quant"
def aug(req="rq"):
    ref = B.R("x"); bd = B.G.Binding(req, None, b"h", 1)
    return R.AugmentedInput(ref, ref, ref, ref, bd)
def code(fn, *a):
    try: return fn(*a)
    except Refusal as e: return e.code
class T(unittest.TestCase):
    def test_declared_fw_parent_with_rebind_accepted(self):
        g = {"fw": M("fw", "FW", (b"a",)), "ml": M("ml", "ML", (b"a",), derived_from="fw")}
        self.assertEqual(R.check_fw_augmented(g["ml"], aug(), Q, g), "BASELINE")
    def test_hidden_quant_ancestor_through_fw_parent_refused(self):
        g = {"fw": M("fw", "FW", (Q,)), "ml": M("ml", "ML", (b"a",), derived_from="fw")}
        self.assertEqual(code(R.check_fw_augmented, g["ml"], aug(), Q, g), "HIDDEN_QUANT_ANCESTOR")
    def test_must_be_ml(self):
        g = {"fw": M("fw", "FW", ())}; self.assertEqual(code(R.check_fw_augmented, g["fw"], aug(), Q, g), "AUGMENTED_REQUIRES_ML_MANIFEST")
    def test_no_fw_parent_refused(self):
        g = {"ml": M("ml", "ML", ())}; self.assertEqual(code(R.check_fw_augmented, g["ml"], aug(), Q, g), "AUGMENTED_WITHOUT_FW_ANCESTRY")
    def test_unresolved_parent_refused(self):
        g = {"ml": M("ml", "ML", (), derived_from="zz")}; self.assertEqual(code(R.check_fw_augmented, g["ml"], aug(), Q, g), "DERIVED_FROM_UNRESOLVED")
    def test_non_fw_parent_refused(self):
        g = {"p": M("p", "ML", ()), "ml": M("ml", "ML", (), derived_from="p")}
        self.assertEqual(code(R.check_fw_augmented, g["ml"], aug(), Q, g), "AUGMENTED_PARENT_NOT_FW")
    def test_missing_or_empty_rebind_refused(self):
        g = {"fw": M("fw", "FW", ()), "ml": M("ml", "ML", (), derived_from="fw")}
        self.assertEqual(code(R.check_fw_augmented, g["ml"], aug(req=""), Q, g), "NO_GATEWAY_REBIND")
        self.assertEqual(code(R.check_fw_augmented, g["ml"], None, Q, g), "NO_GATEWAY_REBIND")
    def test_standalone_still_rejects_fw_ancestry(self):
        g = {"fw": M("fw", "FW", ()), "ml": M("ml", "ML", (), derived_from="fw")}
        self.assertEqual(code(R.check_generation, g["ml"], Q, g, "ML_STANDALONE"), "HIDDEN_FW_ANCESTRY")
if __name__ == "__main__": unittest.main()
