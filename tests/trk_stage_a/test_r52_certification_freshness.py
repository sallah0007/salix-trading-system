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
