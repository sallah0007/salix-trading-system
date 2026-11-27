"""R11: s7A request record wired into Tracker intake (admit). Fails closed; a code event only."""
import copy, dataclasses, unittest
from stage_a.tracker.quant_intake_adapter import admit, FAILED_REQUESTED_BUILD, QUANT_FEATURE
from tests.trk_stage_a.fixtures import package, REQUEST_RECORD

def adm(**rr):
    rec = copy.deepcopy(REQUEST_RECORD); rec.update(rr)
    return admit(package(request_record=rec), accepted_fit_generations={})
def codes(a): return [c for d, c in a.failed if d == "REQUEST_RECORD"]

class IntakeRequestRecord(unittest.TestCase):
    def test_valid_record_admits(self):
        a = adm(); self.assertEqual(codes(a), []); self.assertEqual(a.classification, QUANT_FEATURE)
    def test_missing_record_fails_closed(self):
        a = admit(package(request_record=None), accepted_fit_generations={})
        self.assertEqual(codes(a), ["REQUEST_RECORD_MISSING"]); self.assertEqual(a.classification, FAILED_REQUESTED_BUILD)
    def test_unknown_target_is_review_required_not_admitted(self):
        a = adm(TARGET_CONSUMER="UNKNOWN")
        self.assertEqual(codes(a), ["REQUEST_REVIEW_REQUIRED_TARGET_CONSUMER_UNKNOWN"]); self.assertFalse(a.admissible)
    def test_missing_purpose_refused(self):
        self.assertEqual(codes(adm(PURPOSE_STATEMENT="")), ["REQUEST_PURPOSE_STATEMENT_MISSING"])
    def test_bad_enum_refused(self):
        self.assertEqual(codes(adm(REQUESTER_TYPE="SALIX_AI")), ["REQUEST_ENUM_VALUE_NOT_IN_SOURCE_LIST"])
    def test_correction_needs_evidence(self):
        self.assertEqual(codes(adm(REQUEST_CONTEXT="CORRECTION")), ["REQUEST_CORRECTION_WITHOUT_EVIDENCE_REF"])
    def test_record_bound_into_package_hash(self):
        a = package(); b = dataclasses.replace(a, request_record=dict(a.request_record, PURPOSE_STATEMENT="other"))
        self.assertNotEqual(a.content_hash(), b.content_hash())
    def test_no_quant_request_unaffected(self):
        from stage_a.tracker.quant_intake_adapter import NO_QUANT_FEATURE
        a = admit(package(None, quant=False, request_record=None), accepted_fit_generations={})
        self.assertEqual(a.classification, NO_QUANT_FEATURE)
class PolicyPinsDimension(unittest.TestCase):
    def test_policy_hash_names_request_record_dimension(self):
        from stage_a.tracker import quant_intake_adapter as Q
        from stage_a.storage.byte_primitives import canonical_bytes, domain_hash
        dims = ["SCHEMA", "HASH_BINDING", "CAPABILITY", "FIT_ANCESTRY", "SCOPE_BINDING", "IDENTITY_CONTENT_KEY",
                "LOOKUP_COMPLETENESS", "DUPLICATE", "CONSTRUCTION_AUTHORITY", "REQUEST_RECORD", "RESOURCE_CEILING", "CAPABILITY_DECLARATION"]
        self.assertEqual(Q.POLICY["HASH"], domain_hash("SALIX_STAGE_A_INTAKE_POLICY_V1", canonical_bytes({"dimensions": dims})))
if __name__ == "__main__": unittest.main()
