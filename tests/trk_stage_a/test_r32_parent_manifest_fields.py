"""R32: Parent 1i5P8z… manifest-completeness list (cited by ID; field identifiers only) is covered by QuantManifest, and the code derives (never trusts) the refit flag. Presence of a field is NOT a semantic award (A07 stays OPEN)."""
import dataclasses, unittest
from stage_a.schema.objects import QuantManifest

LISTED = ("feature_id feature_version model_profile_id model_profile_version state_schema_version parameter_schema_version arithmetic_contract_version logical_encoding_version "
          "shared_evaluator_operator_set_version refit_mode refit_rule_ref parameter_generation_source_ref initialization_rule_set_ref step_class_set_ref step_classifier_ref input_dependencies "
          "transition_program_refs projection_program_refs invariant_program_refs published_projection_set_ref verification_rule_set_ref golden_vector_set_ref health_profile_ref "
          "health_metric_program_refs resource_ceiling_ref data_vintage_policy_ref").split()

class ManifestFieldCoverage(unittest.TestCase):
    def test_every_listed_field_is_a_manifest_field_and_none_is_defaulted(self):
        f = {x.name: x for x in dataclasses.fields(QuantManifest)}
        self.assertEqual([n for n in LISTED if n not in f], [])
        self.assertEqual([n for n in LISTED if f[n].default is not dataclasses.MISSING], [])      # a completeness list cannot be satisfied by a silent default
    def test_coverage_check_can_fail(self):
        f = {x.name for x in dataclasses.fields(QuantManifest)}
        self.assertIn("not_a_listed_field", [n for n in LISTED + ["not_a_listed_field"] if n not in f])
if __name__ == "__main__": unittest.main()
