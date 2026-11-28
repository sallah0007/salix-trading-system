import unittest
from stage_a.ml.certification_freshness import BOUND_IDENTITIES, certification_blocks_promotion as blk

CUR = {n: "id-" + n for n in BOUND_IDENTITIES}
def cert(**kw):
    c = {"CERTIFICATION_ID": "CERT-1", "STATE": "PASS", "BOUND": dict(CUR)}; c.update(kw); return c

class CertFreshness(unittest.TestCase):
    def test_current_pass_is_the_positive_control(self): self.assertIsNone(blk(cert(), CUR))
    def test_change_of_any_one_bound_identity_makes_it_stale(self):
        for n in BOUND_IDENTITIES: self.assertEqual(blk(cert(), {**CUR, n: "other"}), "CERTIFICATION_STALE", n)
    def test_fail_not_tested_unknown_state_and_missing_identity_block(self):
        self.assertEqual(blk(cert(STATE="FAIL"), CUR), "CERTIFICATION_FAIL"); self.assertEqual(blk(cert(STATE="NOT_TESTED"), CUR), "CERTIFICATION_NOT_TESTED")
        self.assertEqual(blk(cert(STATE="MAYBE"), CUR), "CERTIFICATION_STATE_UNKNOWN"); self.assertEqual(blk(cert(CERTIFICATION_ID=""), CUR), "CERTIFICATION_IDENTITY_MISSING")
        self.assertEqual(blk(None, CUR), "CERTIFICATION_MISSING")
    def test_incomplete_binding_or_unknown_current_identity_fail_closed(self):
        for n in BOUND_IDENTITIES:
            b = dict(CUR); del b[n]; self.assertEqual(blk(cert(BOUND=b), CUR), "CERTIFICATION_BINDING_INCOMPLETE", n)
            c = dict(CUR); del c[n]; self.assertEqual(blk(cert(), c), "CURRENT_IDENTITY_UNKNOWN", n)
        self.assertEqual(blk(cert(BOUND="x"), CUR), "CERTIFICATION_BINDING_MISSING")
    def test_unresolved_violation_blocks_even_a_current_pass(self):
        self.assertEqual(blk(cert(), CUR, unresolved_violation=True), "UNRESOLVED_ISOLATION_VIOLATION"); self.assertEqual(blk(cert(), CUR, unresolved_violation="yes"), "UNRESOLVED_ISOLATION_VIOLATION")

    def test_manager_public_api_negatives_bool_int_and_blank_identities_are_not_identities(self):
        c = cert(); c["BOUND"]["CODE"] = False; cur = dict(CUR); cur["CODE"] = 0
        self.assertEqual(blk(c, cur), "CERTIFICATION_BINDING_INCOMPLETE")                    # False vs 0 must not count as an unchanged identity
        c = cert(); c["BOUND"]["CODE"] = ""; cur = dict(CUR); cur["CODE"] = ""
        self.assertEqual(blk(c, cur), "CERTIFICATION_BINDING_INCOMPLETE")                    # blank == blank is not an identity
        c = cert(); c["BOUND"]["CODE"] = "   "; self.assertEqual(blk(c, CUR), "CERTIFICATION_BINDING_INCOMPLETE")
        for bad in (0, 1, 1.5, b"x", ("a",), None):
            cur = dict(CUR); cur["CODE"] = bad; self.assertEqual(blk(cert(), cur), "CURRENT_IDENTITY_UNKNOWN", repr(bad))
            c = cert(); c["BOUND"]["RUNTIME"] = bad; self.assertEqual(blk(c, CUR), "CERTIFICATION_BINDING_INCOMPLETE", repr(bad))
    def test_valid_opaque_string_identities_remain_the_positive_control(self):
        self.assertIsNone(blk(cert(), dict(CUR))); self.assertIsNone(blk(cert(BOUND={n: "x:" + n + "/1" for n in BOUND_IDENTITIES}), {n: "x:" + n + "/1" for n in BOUND_IDENTITIES}))
