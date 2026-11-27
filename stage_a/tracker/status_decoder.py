"""Generic record -> StatusFact DECODER built from a SUPPLIED declarative mapping (the interface `StatusProjection` requires; R7 section 2 defines neither the mapping nor a status-origin principal, so NOTHING is defaulted here).
spec = {"record_kind": str, "mv": (field names, exactly five: feature_id, feature_version, instrument_id, timeframe_id, materialization_version), "bytes_fields": {name: width}, "status_field": str, "status_map": {body value: chain_status status},
"sequence_field": str, "available_asof_field": str, "correction_field": str, "designation_field": optional str}. Every key is the SOURCE OWNER's to supply; this module appoints no origin principal and does not map PUBLISHABLE to CURRENT (a status_map that does so is the owner's supplied rule, not ours).
Other record kinds decode to None (a committed record that carries no status fact). A record of the mapped kind that does not fit the mapping refuses (fail closed): wrong id width/type, unmapped status value, non-int sequence/as-of, non-bool flags."""
import json
from ..errors import Refusal
from .chain_status import StatusFact, ALL
_KEYS = {"record_kind", "mv", "bytes_fields", "status_field", "status_map", "sequence_field", "available_asof_field", "correction_field", "designation_field"}
def make_decoder(spec: dict):
    if not (isinstance(spec, dict) and set(spec) <= _KEYS and _KEYS - {"designation_field"} <= set(spec)): raise Refusal("spec", code="STATUS_MAPPING_SPEC_INVALID")
    mv, bf, sm = spec["mv"], spec["bytes_fields"], spec["status_map"]
    if not (isinstance(mv, tuple) and len(mv) == 5 and all(isinstance(x, str) and x for x in mv) and len(set(mv)) == 5 and isinstance(bf, dict) and all(isinstance(w, int) and w > 0 for w in bf.values()) and set(bf) <= set(mv)
            and isinstance(sm, dict) and sm and all(isinstance(k, str) and v in ALL for k, v in sm.items()) and all(isinstance(spec[k], str) and spec[k] for k in _KEYS - {"mv", "bytes_fields", "status_map", "designation_field"})):
        raise Refusal("spec", code="STATUS_MAPPING_SPEC_INVALID")
    def decode(rec):
        if rec.kind != spec["record_kind"]: return None
        try: b = json.loads(rec.body_json)
        except ValueError: raise Refusal("body", code="STATUS_RECORD_NOT_JSON")
        if not isinstance(b, dict): raise Refusal("body", code="STATUS_RECORD_NOT_AN_OBJECT")
        vals = []
        for n in mv:
            v = b.get(n)
            if n in bf:
                if not (isinstance(v, str) and len(v) == 2 * bf[n]): raise Refusal(n, code="STATUS_RECORD_ID_WIDTH")
                try: v = bytes.fromhex(v)
                except ValueError: raise Refusal(n, code="STATUS_RECORD_ID_NOT_HEX")
            elif not (isinstance(v, str) and v): raise Refusal(n, code="STATUS_RECORD_FIELD_INVALID")
            vals.append(v)
        st = sm.get(b.get(spec["status_field"]) if isinstance(b.get(spec["status_field"]), str) else None)
        if st is None: raise Refusal(spec["status_field"], code="STATUS_RECORD_STATUS_UNMAPPED")
        seq, asof, corr = b.get(spec["sequence_field"]), b.get(spec["available_asof_field"]), b.get(spec["correction_field"])
        if type(seq) is not int or type(asof) is not int or seq < 1 or asof < 0 or type(corr) is not bool: raise Refusal("numbers", code="STATUS_RECORD_NUMBERS_INVALID")
        des = False
        if spec.get("designation_field") is not None:
            des = b.get(spec["designation_field"])
            if type(des) is not bool: raise Refusal("designation", code="STATUS_RECORD_NUMBERS_INVALID")
        return StatusFact(tuple(vals), seq, st, asof, corr, des)
    return decode
