"""Seven-field producer binding record shape (C25 register, Drive 1GuI4R58P3G8x9mo5NY9fGurA_Cq-lNjG, 'exact_required_producer_binding_fields'):
scope, interface_id, version, content_hash, source_authority, acceptance_record, validity/supersession. 'Missing is UNSATISFIED'.

THIS IS A SHAPE CHECK ONLY. It cannot establish that the content_hash matches the source bytes, that the acceptance record exists, or that the
source_authority is current: those need the governed Drive record (read-only for the Coder). A record passing here is NOT admitted evidence."""
import re
from ..errors import Refusal

SEVEN_FIELDS = ("scope", "interface_id", "version", "content_hash", "source_authority", "acceptance_record", "validity/supersession")
_HEX64 = re.compile(r"[0-9a-f]{64}\Z")

def check_shape(rec) -> dict:
    if not isinstance(rec, dict):
        raise Refusal(type(rec).__name__, code="BINDING_NOT_A_RECORD")
    extra = set(rec) - set(SEVEN_FIELDS)
    if extra:
        raise Refusal(",".join(sorted(map(str, extra))), code="BINDING_UNKNOWN_FIELD")
    missing = [f for f in SEVEN_FIELDS if f not in rec]
    if missing:
        raise Refusal(",".join(missing), code="BINDING_UNSATISFIED_MISSING_FIELD")
    for f in SEVEN_FIELDS:
        v = rec[f]
        if type(v) is not str or not v.strip():
            raise Refusal(f, code="BINDING_FIELD_EMPTY_OR_NOT_TEXT")
    if not _HEX64.match(rec["content_hash"]):
        raise Refusal("content_hash", code="BINDING_HASH_NOT_SHA256_HEX")
    return rec
