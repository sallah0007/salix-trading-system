"""R18: FIELD->DIMENSION partition rule and relationship-state consequences (REFERENCE_ONLY validators; negatives and positive control)."""
import unittest
from stage_a.errors import Refusal
from stage_a.tracker import version_relationship as V
def code(*a):
    try: V.check_field_dimension_map(*a)
    except Refusal as e: return e.code
OK = [(f, d) for f, d in V.REQUIRED_FITTING_MAPPING.items()]
class Partition(unittest.TestCase):
    def test_positive_control_the_required_fitting_mapping_is_a_valid_total_disjoint_map(self):
        self.assertIsNone(code(list(V.REQUIRED_FITTING_MAPPING), OK))
    def test_unmapped_field_is_raised_not_skipped(self): self.assertEqual(code(list(V.REQUIRED_FITTING_MAPPING) + ["new_field"], OK), "DIFF_PARTITION_INCOMPLETE")
    def test_dual_homed_field_is_not_disjoint(self): self.assertEqual(code(["a"], [("a", "CAUSAL_TIME"), ("a", "CAUSAL_TIME")]), "DIFF_PARTITION_NOT_DISJOINT"); self.assertEqual(code(["a"], [("a", "CAUSAL_TIME"), ("a", "FITTED_LEARNED_STATE")]), "DIFF_PARTITION_NOT_DISJOINT")
    def test_one_sided_field_is_a_schema_mismatch(self): self.assertEqual(code(["a"], [("a", "CAUSAL_TIME"), ("ghost", "CAUSAL_TIME")]), "SCHEMA_MISMATCH")
    def test_unknown_dimension_is_never_invented(self): self.assertEqual(code(["a"], [("a", "MY_NEW_CATEGORY")]), "UNKNOWN_DIMENSION")
    def test_attempt_identity_is_outside_the_version_content_diff(self): self.assertEqual(code(["attempt_identity"], [("attempt_identity", "FITTED_LEARNED_STATE")]), "ATTEMPT_IDENTITY_IN_DIFF")
    def test_required_fitting_fields_must_map_where_the_source_puts_them(self):
        for f in V.REQUIRED_FITTING_MAPPING:
            other = "CAUSAL_TIME" if V.REQUIRED_FITTING_MAPPING[f] != "CAUSAL_TIME" else "PROVENANCE_SOURCE"
            self.assertEqual(code([f], [(f, other)]), "FITTING_FIELD_MISMAPPED", f)
    def test_data_vintage_is_provenance_not_causal_time(self): self.assertEqual(V.REQUIRED_FITTING_MAPPING["data_vintage"], "PROVENANCE_SOURCE")
    def test_empty_schema_refuses(self): self.assertEqual(code([], []), "DIFF_SCHEMA_EMPTY")
    def test_five_dimensions_exactly(self): self.assertEqual(len(V.DIMENSIONS), 5)
class States(unittest.TestCase):
    def test_uncomputed_blocks_supersession_but_not_existing_delivery(self):
        c = V.relationship_consequences(V.UNCOMPUTED); self.assertTrue(c["blocks_supersession_claim"]); self.assertFalse(c["blocks_gateway_delivery_of_existing_eligible_version"]); self.assertFalse(c["may_yield_correction"])
    def test_uncomputable_never_yields_correction_and_is_not_a_deadlock(self):
        c = V.relationship_consequences(V.UNCOMPUTABLE); self.assertFalse(c["may_yield_correction"]); self.assertFalse(c["blocks_supersession_claim"]); self.assertEqual(c["routes_to"], "MATERIAL_ALTERNATIVE")
    def test_unknown_state_refuses(self):
        for s in ("COMPUTED", "", None):
            with self.assertRaises(Refusal) as c: V.relationship_consequences(s)
            self.assertEqual(c.exception.code, "UNKNOWN_RELATIONSHIP_STATE")
if __name__ == "__main__": unittest.main()
