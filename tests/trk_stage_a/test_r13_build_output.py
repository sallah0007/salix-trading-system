"""R13: Composer V9 s27/s28 build-output conformance, wired into Tracker intake. Supplied evidence only; nothing is defaulted."""
import dataclasses, unittest
from stage_a.errors import Refusal
from stage_a.tracker import build_output_check as B
from stage_a.tracker.quant_intake_adapter import admit, QUANT_FEATURE
from tests.trk_stage_a.fixtures import package, momentum_manifest, build_output_for

def codes(a): return [c for d, c in a.failed if d == "BUILD_OUTPUT_CONTRACT"]
def adm(**o): return admit(package(**o), accepted_fit_generations=o.pop("fits", {}))
def code(fn, *a, **k):
    try: fn(*a, **k)
    except Refusal as e: return e.code
class Intake(unittest.TestCase):
    def test_valid_admits(self): self.assertEqual(adm().classification, QUANT_FEATURE)
    def test_missing_package_fails_closed(self): self.assertEqual(codes(adm(build_output=None)), ["BUILD_OUTPUT_PACKAGE_MISSING"])
    def test_order_id_must_be_the_governed_order(self):
        self.assertEqual(codes(adm(build_output=dict(build_output_for(momentum_manifest()), ORDER_ID="ORD-OTHER"))), ["BUILD_OUTPUT_ORDER_ID_DIFFERS_FROM_GOVERNED_ORDER"])
        bo = build_output_for(momentum_manifest()); del bo["ORDER_ID"]
        self.assertEqual(codes(adm(build_output=bo)), ["BUILD_OUTPUT_ORDER_ID_DIFFERS_FROM_GOVERNED_ORDER"])
    def test_creation_request_must_match(self):
        self.assertEqual(codes(adm(build_output=dict(build_output_for(momentum_manifest()), CREATION_REQUEST_ID="X"))), ["BUILD_OUTPUT_CREATION_REQUEST_ID_DIFFERS"])
    def test_package_is_never_a_gateway_package_or_registry_entry(self):
        for k in B.FORBIDDEN_FIELDS:
            self.assertEqual(codes(adm(build_output=dict(build_output_for(momentum_manifest()), **{k: "x"}))), ["BUILD_OUTPUT_PACKAGE_CARRIES_OTHER_OBJECT_IDENTITY"], k)
    def test_empty_token_field_refused(self):
        self.assertEqual(codes(adm(build_output=dict(build_output_for(momentum_manifest()), BUILDER_BUILD_ID=" "))), ["BUILD_OUTPUT_FIELD_EMPTY"])
    def test_upstream_ancestry_without_fit_refs_refused(self):
        self.assertEqual(codes(adm(build_output=dict(build_output_for(momentum_manifest()), UPSTREAM_MODEL_ID="m", UPSTREAM_GENERATION_ID="g"))), ["UPSTREAM_ANCESTRY_WITHOUT_LEARNED_DERIVATION"])
    def test_binding_into_package_hash(self):
        a = package(); b = dataclasses.replace(a, build_output=dict(a.build_output, BUILDER_BUILD_ID="other")); self.assertNotEqual(a.content_hash(), b.content_hash())
class LearnedDerivedAtIntake(unittest.TestCase):
    FITS = {2: "b" * 64}
    def _m(self): return momentum_manifest(fit_refs=[{"generation": 2, "ref_hash": "b" * 64}])
    def test_fit_refs_make_the_construct_learned_derived_and_upstream_identity_mandatory(self):
        m = self._m(); bo = {k: v for k, v in build_output_for(m).items() if not k.startswith("UPSTREAM") and k != "GENERATION_AUTHORITY_CLASS"}
        a = admit(package(m, build_output=bo), accepted_fit_generations=self.FITS)
        self.assertEqual(codes(a), ["LEARNED_DERIVED_WITHOUT_UPSTREAM_GENERATION_IDENTITY"])
        self.assertEqual(codes(admit(package(m), accepted_fit_generations=self.FITS)), [])
class Direct(unittest.TestCase):
    OK = dict(order_id="O", creation_request_id="R")
    def test_learned_derived_requires_upstream_identity_each_field(self):
        full = {"ORDER_ID": "O", "CREATION_REQUEST_ID": "R", "UPSTREAM_MODEL_ID": "m", "UPSTREAM_GENERATION_ID": "g", "GENERATION_AUTHORITY_CLASS": "c"}
        self.assertIsNone(code(B.check_build_output, full, learned_derived=True, **self.OK))
        for k in B.LEARNED_DERIVED_REQUIRED:
            bo = dict(full); del bo[k]
            self.assertEqual(code(B.check_build_output, bo, learned_derived=True, **self.OK), "LEARNED_DERIVED_WITHOUT_UPSTREAM_GENERATION_IDENTITY", k)
    def test_forbidden_outcome_access(self):
        self.assertEqual(code(B.check_outcome_access, "FORBIDDEN", True), "OUTCOME_INFORMATION_CONSULTED_UNDER_FORBIDDEN")
        self.assertEqual(code(B.check_outcome_access, "FORBIDDEN", None), "OUTCOME_ACCESS_UNVERIFIED_UNDER_FORBIDDEN")
        self.assertIsNone(code(B.check_outcome_access, "FORBIDDEN", False)); self.assertIsNone(code(B.check_outcome_access, "OTHER", True))
    def test_dangling_input(self):
        self.assertEqual(code(B.check_inputs_resolve, ["a", "z"], {"a"}, set()), "DANGLING_INPUT"); self.assertIsNone(code(B.check_inputs_resolve, ["a", "n1"], {"a"}, {"n1"}))
    def test_reproduction(self):
        self.assertEqual(code(B.check_reproduction, "h1", "h2"), "DETERMINISTIC_RECOMPUTATION_MISMATCH")
        self.assertEqual(code(B.check_reproduction, "h1", None), "RECOMPUTATION_IMPOSSIBLE_WITHOUT_GOVERNED_REASON")
        self.assertIsNone(code(B.check_reproduction, "h1", None, "GOV-REASON")); self.assertIsNone(code(B.check_reproduction, "h", "h"))
    def test_non_dict_refused(self): self.assertEqual(code(B.check_build_output, [], learned_derived=False, **self.OK), "BUILD_OUTPUT_PACKAGE_MISSING")
if __name__ == "__main__": unittest.main()
