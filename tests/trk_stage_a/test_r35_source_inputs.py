import unittest
from stage_a.errors import Refusal
from stage_a.tracker import source_inputs as SI
from . import test_r33_composed as TC
H = "a" * 64; H2 = "b" * 64
def code(f, *a, **k):
    try: f(*a, **k)
    except Refusal as e: return e.code
class SourceInputs(unittest.TestCase):
    def setUp(self):
        t = TC.AcceptedRecordVerification(); self.rig, self.fk, self.j, self.body = t.accepted()
    def v(self, b, r=None): return SI.verify_accepted_source_inputs(journal=self.j, store=self.rig.store, feature_key=self.fk, bindings=b, resolver=r)
    def test_bindings_must_cover_exactly_the_accepted_manifests_declared_inputs(self):
        ok = {"close": {"ref": "SRC/close/v1", "hash": H}}
        r = self.v(ok); self.assertEqual((r["overall"], r["inputs"], r["stream_verified"]), ("HELD_UNVERIFIED", {"close": "BOUND_UNVERIFIED"}, False))     # no resolver: shape-only, never VERIFIED
        self.assertEqual(self.v({})["overall"], "FAIL"); self.assertEqual(self.v({})["inputs"], {"close": "MISSING"})
        self.assertEqual((self.v(dict(ok, extra=ok["close"]))["overall"], self.v(dict(ok, extra=ok["close"]))["extra"]), ("FAIL", ("extra",)))
        for bad in ({"ref": "", "hash": H}, {"ref": "r", "hash": "XYZ"}, {"ref": "r"}, {"ref": "r", "hash": H, "x": 1}, "str"): self.assertEqual(self.v({"close": bad})["inputs"], {"close": "MISSING"}, repr(bad))
    def test_a_supplied_resolver_verifies_hashes_and_unresolved_or_wrong_is_fail(self):
        ok = {"close": {"ref": "SRC/close/v1", "hash": H}}
        self.assertEqual(self.v(ok, lambda ref: H)["overall"], "VERIFIED"); self.assertEqual(self.v(ok, lambda ref: H2)["inputs"], {"close": "MISMATCH"}); self.assertEqual(self.v(ok, lambda ref: None)["inputs"], {"close": "UNRESOLVED"}); self.assertEqual(self.v(ok, lambda ref: None)["overall"], "FAIL")
    def test_missing_accepted_record_or_artifact_is_fail_not_rebuilt_and_legacy_is_held(self):
        from stage_a.storage.keys import accepted_materialization_key
        from stage_a.storage.authority_class import _PREFIX
        mk = _PREFIX + accepted_materialization_key(self.body["materialization_hash"]); good = self.rig.raw_store._d[mk]; del self.rig.raw_store._d[mk]
        self.assertEqual((self.v({})["overall"], self.v({})["reason"]), ("FAIL", "ACCEPTED_RECORD_ABSENT")); self.assertNotIn(mk, self.rig.raw_store._d); self.rig.raw_store._d[mk] = good
        self.assertEqual(self.v({"close": {"ref": "r", "hash": H}}, lambda ref: H)["overall"], "VERIFIED")
        self.assertEqual(code(SI.verify_accepted_source_inputs, journal=self.j, store=self.rig.store, feature_key=self.fk, bindings="x"), "SOURCE_INPUT_BINDINGS_INVALID")
class Legacy(unittest.TestCase):
    def test_a_pre_r34_acceptance_has_no_binding_to_verify_and_is_held(self):
        from .test_foundations import accepted_body, mk, NS
        from stage_a.coordination import transition_record as T
        from stage_a.identifiers import FeatureKey, Scope
        b = accepted_body(); del b["materialization_hash"]; _, j = mk(); j.append(j.head(), T.CANONICAL_ACCEPTED, b)
        self.assertEqual(code(SI.verify_accepted_source_inputs, journal=j, store=None, feature_key=FeatureKey(Scope("XAUUSD", "H4"), "mom3", "1"), bindings={}), "ACCEPTED_RECORD_LEGACY_MAINTENANCE_HOLD")
if __name__ == "__main__": unittest.main()
