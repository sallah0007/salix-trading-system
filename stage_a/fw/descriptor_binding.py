"""FW10 / N-2 OUTCOME-TARGET-series (H3) descriptor reader. Separate from the feature-view DeliveredFeatureEntry (gateway/binding.py owns that). Truthful by construction: a field is READ only where the A04 status is DIRECT or PARTIAL AND a seven-field producer
binding (shape-checked) AND an exact payload key were SUPPLIED; the value is typed-checked and labelled UNVERIFIED. SEGMENT_REF and KNOWABLE_AT (exact per-observation mapping unbound) and ADMISSIBILITY_STATE (FW-owned internal derivation unbound)
are HELD with their exact missing slot, even if a payload carries a same-named key; no substitution is performed: AUTHORIZED_SEGMENT_SET is not segment membership, HORIZON_ID is not the rules, a policy id is not time, and AVAILABLE_ASOF / a decision cutoff is
not KNOWABLE_AT. The result is never complete while any field is held."""
from dataclasses import dataclass
from ..errors import Refusal
from ..binding.producer_binding import check_shape
from .descriptor_crosswalk import FIELDS, SOURCE_STATUS, MISSING_EXACT_SOURCE_MAPPING, INTERNAL_DERIVATION_UNBOUND, PARTIAL_SOURCE_CARRIER

_TYPES = {"DEPENDENCY_INTERVAL_START": "int", "DEPENDENCY_INTERVAL_END": "int", "HORIZON_ID": "str", "HORIZON_VERSION": "str", "AUTHORIZED_SEGMENT_SET": "strs", "OBSERVATION_REF": "str", "VINTAGE_REF": "str"}
NEVER_A_SUBSTITUTE = ("AVAILABLE_ASOF", "DECISION_CUTOFF", "POLICY_ID", "AUTHORIZED_SEGMENT_SET_AS_MEMBERSHIP")

@dataclass(frozen=True)
class Descriptor:
    values: dict           # field -> (value, status) for READ fields only; status DIRECT_UNVERIFIED | PARTIAL_UNVERIFIED
    held: dict             # field -> exact reason/missing slot
    complete: bool = False

def _ok(v, t):
    if t == "int": return type(v) is int and v >= 0
    if t == "str": return isinstance(v, str) and bool(v)
    return isinstance(v, (list, tuple)) and len(v) > 0 and all(isinstance(x, str) and x for x in v) and len(set(v)) == len(v)

def read_descriptor(payload, bindings: dict, key_of: dict) -> Descriptor:
    if not isinstance(payload, dict) or not isinstance(bindings, dict) or not isinstance(key_of, dict): raise Refusal("inputs", code="DESCRIPTOR_INPUT_INVALID")
    unknown = sorted((set(bindings) | set(key_of)) - set(FIELDS))
    if unknown: raise Refusal(",".join(map(str, unknown)), code="UNKNOWN_DESCRIPTOR_FIELD")
    for f, k in key_of.items():
        if k in NEVER_A_SUBSTITUTE or (isinstance(k, str) and k.upper() in NEVER_A_SUBSTITUTE): raise Refusal(f + "<-" + str(k), code="DESCRIPTOR_SUBSTITUTION_NOT_PERMITTED")
    vals, held = {}, {}
    for f in FIELDS:
        st = SOURCE_STATUS[f]
        if st == MISSING_EXACT_SOURCE_MAPPING: held[f] = "EXACT_SOURCE_MAPPING_UNBOUND"; continue
        if st == INTERNAL_DERIVATION_UNBOUND: held[f] = "FW_OWNED_INTERNAL_DERIVATION_UNBOUND"; continue
        if f not in bindings: held[f] = "UNDECLARED_REAL_PAYLOAD_BINDING"; continue
        check_shape(bindings[f])                                                  # shape only: not admission
        k = key_of.get(f)
        if not (isinstance(k, str) and k) or k not in payload: held[f] = "PAYLOAD_KEY_NOT_SUPPLIED_OR_ABSENT"; continue
        if not _ok(payload[k], _TYPES[f]): raise Refusal(f, code="DESCRIPTOR_VALUE_MALFORMED")
        vals[f] = (payload[k], "PARTIAL_UNVERIFIED" if st == PARTIAL_SOURCE_CARRIER else "DIRECT_UNVERIFIED")
    if "DEPENDENCY_INTERVAL_START" in vals and "DEPENDENCY_INTERVAL_END" in vals and vals["DEPENDENCY_INTERVAL_START"][0] >= vals["DEPENDENCY_INTERVAL_END"][0]: raise Refusal("interval", code="DESCRIPTOR_INTERVAL_NOT_ORDERED")
    return Descriptor(vals, held, False)
