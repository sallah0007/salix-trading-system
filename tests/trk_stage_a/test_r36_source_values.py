"""R36: accepted source-input / source-VALUE verification binds the accepted receipt -> stored materialization record -> artifact FIRST (root repro: a record whose object_key was repointed at a known foreign artifact still produced VERIFIED)."""
import json, hashlib, unittest
from stage_a.errors import Refusal
from stage_a.tracker import source_inputs as SI
from stage_a.storage.byte_primitives import canonical_bytes
from stage_a.storage.keys import accepted_materialization_key, artifact_key
from stage_a.storage.authority_class import _PREFIX
from . import test_r33_composed as TC
H = lambda s: hashlib.sha256(repr(s).encode()).hexdigest()          # TEST-ONLY series hash; the real encoding is not defined by any source read
SER = [100.0 + i * 0.5 for i in range(30)]
def code(f, *a, **k):
    try: f(*a, **k)
    except Refusal as e: return e.code
class Binding(unittest.TestCase):
    def setUp(self):
        t = TC.AcceptedRecordVerification(); self.rig, self.fk, self.j, self.body = t.accepted(); self.mk = accepted_materialization_key(self.body["materialization_hash"])
        self.good = self.rig.raw_store._d[_PREFIX + self.mk]
    def put(self, d): self.rig.raw_store._d[_PREFIX + self.mk] = (canonical_bytes(d) if isinstance(d, dict) else d, 1)
    def rec(self): return json.loads(self.good[0])
    def names(self, r=None): return SI.verify_accepted_source_inputs(journal=self.j, store=self.rig.store, feature_key=self.fk, bindings={"close": {"ref": "r", "hash": "a" * 64}}, resolver=lambda ref: "a" * 64)
    def test_genuine_positive_and_restart(self):
        self.assertEqual(self.names()["overall"], "VERIFIED"); self.assertEqual(self.names()["overall"], "VERIFIED")
    def test_a_record_repointed_at_a_known_foreign_artifact_is_not_verified(self):
        from .test_r33_composed import momentum_manifest, Manifest, SIMS
        from stage_a.tracker.materialization.stateful_materializer import StatefulMaterializer
        from stage_a.tracker.verification.stateful_verifier import probe_for
        from stage_a.composer.expression.canonical_encoding import encode_manifest
        o = momentum_manifest(); o["feature_id"] = "foreign"; o["nodes"][3]["n"] = 4
        scratch = SIMS(); m2 = Manifest.from_dict(o); r2 = StatefulMaterializer(scratch).materialize(m2, probe_for(encode_manifest(m2)))
        self.rig.raw_store._d[_PREFIX + artifact_key(r2["manifest_hash"])] = (scratch.get(artifact_key(r2["manifest_hash"]))[0], 1)       # the foreign artifact is a KNOWN stored object
        self.put(dict(self.rec(), object_key=artifact_key(r2["manifest_hash"])))                                                           # old materialization_hash and accepted body retained
        r = SI.verify_accepted_source_inputs(journal=self.j, store=self.rig.store, feature_key=self.fk, bindings={"close": {"ref": "r", "hash": "a" * 64}}, resolver=lambda ref: "a" * 64)
        self.assertEqual(r["overall"], "FAIL"); self.assertTrue(r["reason"].startswith("ACCEPTED_RECORD_NOT_VERIFIED_AS_FOUND")); self.assertEqual(r["inputs"], {})
        v = SI.verify_source_values(journal=self.j, store=self.rig.store, feature_key=self.fk, bindings={"close": {"ref": "r", "hash": H(SER)}}, fetch=lambda ref: SER, series_hash=H)
        self.assertEqual(v["overall"], "FAIL"); self.assertIsNone(v["recomputed"])
    def test_altered_record_identity_fields_and_missing_bytes_fail_closed(self):
        for k, val in (("feature_key", "XAUUSD/H4/other/1"), ("feature_version", "9"), ("materialization_hash", "0" * 64)):
            self.put(dict(self.rec(), **{k: val})); self.assertEqual((self.names()["overall"], self.names()["reason"]), ("FAIL", "ACCEPTED_RECORD_ABSENT_OR_UNBOUND"), k)
        self.put(self.rec()); art = self.rig.raw_store._d.pop(_PREFIX + artifact_key(self.body["manifest_hash"])); self.assertEqual(self.names()["overall"], "FAIL")
        self.rig.raw_store._d[_PREFIX + artifact_key(self.body["manifest_hash"])] = art; self.put(self.good[0]); self.assertEqual(self.names()["overall"], "VERIFIED")        # genuine again
class Values(unittest.TestCase):
    def setUp(self):
        t = TC.AcceptedRecordVerification(); self.rig, self.fk, self.j, self.body = t.accepted()
    def v(self, ser=SER, h=None, exp=None, fetch=None):
        return SI.verify_source_values(journal=self.j, store=self.rig.store, feature_key=self.fk, bindings={"close": {"ref": "SRC/close", "hash": h or H(SER)}}, fetch=fetch or (lambda ref: ser), series_hash=H, expected_output=exp)
    def test_independent_recomputation_and_the_provider_proof_stays_held(self):
        r = self.v(); self.assertEqual((r["overall"], r["stream_verified"], r["provider_vintage_clock_proof"], r["matches_expected"]), ("VERIFIED_RECOMPUTED", False, "HELD", None)); self.assertTrue(r["recomputed"])
        self.assertEqual(self.v(exp=r["recomputed"])["matches_expected"], True); bad = list(r["recomputed"]); bad[-1] = bad[-1] ^ 1 if isinstance(bad[-1], int) else bad[-1]
        self.assertEqual(self.v(exp=bad)["overall"], "FAIL" if bad != r["recomputed"] else "VERIFIED_RECOMPUTED")
    def test_wrong_hash_unresolved_malformed_series_and_extra_inputs_fail(self):
        self.assertEqual(self.v(h="b" * 64)["inputs"], {"close": "MISMATCH"}); self.assertEqual(self.v(fetch=lambda ref: None)["inputs"], {"close": "UNRESOLVED"})
        self.assertEqual(self.v(ser=[1, 2, 3], h=H([1, 2, 3]))["inputs"], {"close": "SERIES_MALFORMED"}); self.assertEqual(self.v(ser=[], h=H([]))["inputs"], {"close": "SERIES_MALFORMED"})
        r = SI.verify_source_values(journal=self.j, store=self.rig.store, feature_key=self.fk, bindings={"close": {"ref": "r", "hash": H(SER)}, "x": {"ref": "r", "hash": H(SER)}}, fetch=lambda ref: SER, series_hash=H)
        self.assertEqual((r["overall"], r["extra"]), ("FAIL", ("x",))); self.assertEqual(code(SI.verify_source_values, journal=self.j, store=self.rig.store, feature_key=self.fk, bindings={}, fetch=None, series_hash=H), "SOURCE_VALUE_INPUTS_INVALID")
    def test_the_recomputed_output_depends_on_the_supplied_values(self):
        a = self.v()["recomputed"]; ser2 = [100.0 + i * 0.7 for i in range(30)]; b = SI.verify_source_values(journal=self.j, store=self.rig.store, feature_key=self.fk, bindings={"close": {"ref": "r", "hash": H(ser2)}}, fetch=lambda ref: ser2, series_hash=H)["recomputed"]
        self.assertNotEqual(a, b)
if __name__ == "__main__": unittest.main()
