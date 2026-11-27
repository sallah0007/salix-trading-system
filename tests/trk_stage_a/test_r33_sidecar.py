import hashlib, unittest
from stage_a.errors import Refusal
from stage_a.storage import artifact_sidecar as SC
def code(f, *a, **k):
    try: f(*a, **k)
    except Refusal as e: return e.code
H = lambda b: hashlib.sha256(b).hexdigest()
A = b"\x00canonical-bytes\xff"
def mk(**o): return SC.make_sidecar(A, **dict(dict(kind="PROGRAM", content_hash=H(A), created_at=5, source_ref="ref", logical_encoding_version="LE1"), **o))
class Sidecar(unittest.TestCase):
    def test_roundtrip_and_each_inconsistency_is_refused(self):
        self.assertEqual(SC.verify_sidecar(mk(), A, H)["ARTIFACT_KIND"], "PROGRAM")
        self.assertEqual(code(SC.verify_sidecar, mk(), A + b"x", H), "SIDECAR_LENGTH_MISMATCH")
        self.assertEqual(code(SC.verify_sidecar, mk(content_hash="0" * 64), A, H), "SIDECAR_CONTENT_HASH_MISMATCH")
        self.assertEqual(code(SC.verify_sidecar, mk(), A, lambda b: "0" * 64), "SIDECAR_CONTENT_HASH_MISMATCH")                    # the owner's recompute decides, not the sidecar
        self.assertEqual(code(SC.verify_sidecar, b"\xff\xfe", A, H), "SIDECAR_NOT_UTF8_JSON"); self.assertEqual(code(SC.verify_sidecar, b"[]", A, H), "SIDECAR_NOT_A_RECORD")
        self.assertEqual(code(SC.verify_sidecar, b'{"ARTIFACT_KIND":"a","ARTIFACT_KIND":"b"}', A, H), "SIDECAR_DUPLICATE_KEY")
        self.assertEqual(code(SC.verify_sidecar, mk(), A, None), "SIDECAR_INPUT_INVALID")
    def test_shape_unknown_fields_missing_version_and_bad_types_are_refused(self):
        import json
        d = json.loads(mk())
        for k, v in (("EXTRA", "x"),): self.assertEqual(code(SC.verify_sidecar, json.dumps(dict(d, **{k: v})).encode(), A, H), "SIDECAR_UNKNOWN_FIELD")
        for k in ("ARTIFACT_KIND", "CONTENT_HASH", "BYTE_LENGTH", "CREATED_AT", "SOURCE_REF", "LOGICAL_ENCODING_VERSION"):
            x = dict(d); del x[k]; self.assertEqual(code(SC.verify_sidecar, json.dumps(x).encode(), A, H), "SIDECAR_FIELD_MISSING", k)
        for k, v in (("BYTE_LENGTH", True), ("BYTE_LENGTH", -1), ("CREATED_AT", "5"), ("SOURCE_REF", "")): self.assertEqual(code(SC.verify_sidecar, json.dumps(dict(d, **{k: v})).encode(), A, H), "SIDECAR_FIELD_INVALID", k)
        self.assertEqual(code(SC.make_sidecar, "not-bytes", kind="k", content_hash="h", created_at=1, source_ref="s", schema_version="1"), "SIDECAR_ARTIFACT_NOT_BYTES")
    def test_sidecar_is_not_part_of_the_artifact_identity(self):
        self.assertEqual(H(A), SC.verify_sidecar(mk(created_at=1), A, H)["CONTENT_HASH"]); self.assertEqual(SC.verify_sidecar(mk(created_at=1), A, H)["CONTENT_HASH"], SC.verify_sidecar(mk(created_at=999, source_ref="other"), A, H)["CONTENT_HASH"])
if __name__ == "__main__": unittest.main()
