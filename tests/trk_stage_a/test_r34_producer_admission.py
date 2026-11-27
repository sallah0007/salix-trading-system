import unittest
from stage_a.errors import Refusal
from stage_a.binding import producer_admission as PA
from stage_a.tracker import build_output_check as BO
def code(f, *a, **k):
    try: f(*a, **k)
    except Refusal as e: return e.code
REC = {"scope": "S", "interface_id": "I", "version": "1", "content_hash": "a" * 64, "source_authority": "SA", "acceptance_record": "AR", "validity/supersession": "V"}
def auth(table): return lambda s, i, v: table.get((s, i, v))
class Admission(unittest.TestCase):
    def test_exact_equality_with_the_supplied_authority_record_and_never_qualified(self):
        d = PA.admit(REC, auth({("S", "I", "1"): dict(REC)}), "SRC-1"); self.assertEqual((d.status, d.qualified, d.authority_source_ref), (PA.ADMITTED_AGAINST_SUPPLIED_AUTHORITY, False, "SRC-1"))
    def test_every_field_difference_missing_record_and_malformed_answers_are_unsatisfied(self):
        for f, v in (("content_hash", "b" * 64), ("source_authority", "X"), ("acceptance_record", "X"), ("validity/supersession", "SUPERSEDED")):
            d = PA.admit(REC, auth({("S", "I", "1"): dict(REC, **{f: v})}), "SRC-1"); self.assertEqual((d.status, d.reason), (PA.UNSATISFIED, "FIELD_MISMATCH:" + f))
        self.assertEqual(PA.admit(REC, auth({}), "S").reason, "UNSATISFIED_NO_AUTHORITY_RECORD"); self.assertEqual(PA.admit(REC, auth({("S", "I", "1"): {"scope": "S"}}), "S").status, PA.UNSATISFIED)
        self.assertTrue(PA.admit({k: v for k, v in REC.items() if k != "version"}, auth({}), "S").reason.startswith("SHAPE:"))
        self.assertEqual(PA.admit(dict(REC, version="2"), auth({("S", "I", "1"): dict(REC)}), "S").reason, "UNSATISFIED_NO_AUTHORITY_RECORD")      # authority is looked up by the exact presented key
    def test_no_authority_or_no_source_ref_is_refused_not_defaulted(self):
        self.assertEqual(code(PA.admit, REC, None, "S"), "PRODUCER_ADMISSION_AUTHORITY_NOT_SUPPLIED"); self.assertEqual(code(PA.admit, REC, auth({}), ""), "PRODUCER_ADMISSION_AUTHORITY_NOT_SUPPLIED")
    def test_package_conformance_and_producer_admission_are_different_objects(self):
        pkg = {"ORDER_ID": "O1", "CREATION_REQUEST_ID": "C1"}; self.assertIsNone(BO.check_build_output(pkg, order_id="O1", creation_request_id="C1", learned_derived=False))        # a conforming package says nothing about a producer binding
        self.assertEqual(PA.admit(REC, auth({}), "S").status, PA.UNSATISFIED)
        self.assertEqual(code(BO.check_build_output, dict(pkg, **REC), order_id="O1", creation_request_id="C1", learned_derived=False), None)      # extra unknown keys are not conformance evidence for admission either: admission still needs the authority record
        self.assertEqual(PA.admit(dict(REC), auth({("S", "I", "1"): dict(REC)}), "S").status, PA.ADMITTED_AGAINST_SUPPLIED_AUTHORITY)
if __name__ == "__main__": unittest.main()
