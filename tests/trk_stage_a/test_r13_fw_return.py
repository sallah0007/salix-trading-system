import unittest
from stage_a.errors import Refusal
from stage_a.fw import return_lineage as F
def code(fn, *a):
    try: fn(*a)
    except Refusal as e: return e.code
class T(unittest.TestCase):
    def test_only_evidence_requests_lineage(self):
        self.assertIsNone(code(F.check_fw_return_classes, ["EVIDENCE", "REQUEST", "LINEAGE"]))
        for bad in ("FEATURE", "PREDICTIVE_INPUT", "PACKAGE", "evidence"): self.assertEqual(code(F.check_fw_return_classes, ["EVIDENCE", bad]), "FW_RETURN_CLASS_NOT_PERMITTED", bad)
        self.assertEqual(code(F.check_fw_return_classes, []), "FW_RETURN_EMPTY")
    def test_fw_derived_predictive_input_needs_lineage_and_rebind(self):
        self.assertEqual(code(F.check_ml_input_origin, True, None), "FW_DERIVED_INPUT_WITHOUT_LINEAGE_AND_REBIND")
        self.assertIsNone(code(F.check_ml_input_origin, True, object())); self.assertIsNone(code(F.check_ml_input_origin, False, None))
if __name__ == "__main__": unittest.main()
