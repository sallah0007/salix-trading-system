"""E-02 (Build Plan 29A) non-authoritative storage-metadata SIDECAR for a stored governed artifact. Canonical identity stays the artifact's OWN frozen encoding and hash; the sidecar (UTF-8 JSON) is never part of any governed hash domain and never an authority. Fields (source-named): ARTIFACT_KIND, SCHEMA_VERSION/LOGICAL_ENCODING_VERSION, CONTENT_HASH, BYTE_LENGTH, CREATED_AT, SOURCE_REF.
This module invents no hash domain: CONTENT_HASH is verified by a recompute function SUPPLIED by the artifact's owner (the artifact-specific governed hash). Candidate; REFERENCE_ONLY (no storage path writes sidecars yet)."""
import json
from ..errors import Refusal
FIELDS = ("ARTIFACT_KIND", "SCHEMA_VERSION", "LOGICAL_ENCODING_VERSION", "CONTENT_HASH", "BYTE_LENGTH", "CREATED_AT", "SOURCE_REF")
REQUIRED = ("ARTIFACT_KIND", "CONTENT_HASH", "BYTE_LENGTH", "CREATED_AT", "SOURCE_REF")       # plus at least one of SCHEMA_VERSION / LOGICAL_ENCODING_VERSION
def _no_dups(pairs):
    d = {}
    for k, v in pairs:
        if k in d: raise Refusal(k, code="SIDECAR_DUPLICATE_KEY")
        d[k] = v
    return d
def make_sidecar(artifact_bytes: bytes, *, kind, content_hash, created_at, source_ref, schema_version=None, logical_encoding_version=None) -> bytes:
    if not isinstance(artifact_bytes, bytes): raise Refusal("artifact", code="SIDECAR_ARTIFACT_NOT_BYTES")
    d = {"ARTIFACT_KIND": kind, "CONTENT_HASH": content_hash, "BYTE_LENGTH": len(artifact_bytes), "CREATED_AT": created_at, "SOURCE_REF": source_ref}
    if schema_version is not None: d["SCHEMA_VERSION"] = schema_version
    if logical_encoding_version is not None: d["LOGICAL_ENCODING_VERSION"] = logical_encoding_version
    _check_shape(d); return json.dumps(d, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
def _check_shape(d):
    if not isinstance(d, dict): raise Refusal("sidecar", code="SIDECAR_NOT_A_RECORD")
    extra = sorted(set(d) - set(FIELDS))
    if extra: raise Refusal(",".join(extra), code="SIDECAR_UNKNOWN_FIELD")
    miss = [f for f in REQUIRED if f not in d]
    if miss or not ("SCHEMA_VERSION" in d or "LOGICAL_ENCODING_VERSION" in d): raise Refusal(",".join(miss) or "VERSION", code="SIDECAR_FIELD_MISSING")
    for f in d:
        if f == "BYTE_LENGTH":
            if type(d[f]) is not int or d[f] < 0: raise Refusal(f, code="SIDECAR_FIELD_INVALID")
        elif f == "CREATED_AT":
            if type(d[f]) is not int or d[f] < 0: raise Refusal(f, code="SIDECAR_FIELD_INVALID")
        elif not (isinstance(d[f], str) and d[f]): raise Refusal(f, code="SIDECAR_FIELD_INVALID")
def verify_sidecar(sidecar_bytes: bytes, artifact_bytes: bytes, recompute_content_hash) -> dict:
    """Fail-closed: the sidecar must parse as UTF-8 JSON without duplicate keys, carry exactly the source fields, match the artifact's byte length, and its CONTENT_HASH must equal the hash the artifact OWNER's function recomputes from the canonical bytes. A sidecar that agrees proves metadata consistency only, not authority or acceptance."""
    if not isinstance(sidecar_bytes, bytes) or not isinstance(artifact_bytes, bytes) or not callable(recompute_content_hash): raise Refusal("inputs", code="SIDECAR_INPUT_INVALID")
    try: d = json.loads(sidecar_bytes.decode("utf-8"), object_pairs_hook=_no_dups)
    except (UnicodeDecodeError, ValueError) as e: raise Refusal(type(e).__name__, code="SIDECAR_NOT_UTF8_JSON")
    _check_shape(d)
    if d["BYTE_LENGTH"] != len(artifact_bytes): raise Refusal("length", code="SIDECAR_LENGTH_MISMATCH")
    if recompute_content_hash(artifact_bytes) != d["CONTENT_HASH"]: raise Refusal("hash", code="SIDECAR_CONTENT_HASH_MISMATCH")
    return d
