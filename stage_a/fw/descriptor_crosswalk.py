"""FW ten-field descriptor crosswalk (documentary), from the finite mapping/dependency disposition (Drive 12h77ZuFRezmZr4_8Zrs1BDyYUtpnoMlI,
61,967 B, text read this pass; its SHA-256 ea9e7949... is NOT recomputed here). It is documentary requirements/mapping, NOT a second FW/ML
interface authority. Every actual payload binding is UNDECLARED in that source, so this module's only behaviour is fail-closed refusal:
no descriptor value may be produced from a payload until an exact real binding exists. Nothing here selects a binding."""
from ..errors import Refusal

DIRECT_SCHEMA_FIELD_NOT_INSTANCE = "DIRECT_SCHEMA_FIELD_NOT_INSTANCE"
DIRECT_SCHEMA_CARRIER_NOT_INSTANCE = "DIRECT_SCHEMA_CARRIER_NOT_INSTANCE"
PARTIAL_SOURCE_CARRIER = "PARTIAL_SOURCE_CARRIER"
MISSING_EXACT_SOURCE_MAPPING = "MISSING_EXACT_SOURCE_MAPPING"
INTERNAL_DERIVATION_UNBOUND = "INTERNAL_DERIVATION_UNBOUND"

SOURCE_STATUS = {
    "OBSERVATION_REF": PARTIAL_SOURCE_CARRIER, "DEPENDENCY_INTERVAL_START": DIRECT_SCHEMA_FIELD_NOT_INSTANCE,
    "DEPENDENCY_INTERVAL_END": DIRECT_SCHEMA_FIELD_NOT_INSTANCE, "HORIZON_ID": DIRECT_SCHEMA_FIELD_NOT_INSTANCE,
    "HORIZON_VERSION": DIRECT_SCHEMA_FIELD_NOT_INSTANCE, "SEGMENT_REF": MISSING_EXACT_SOURCE_MAPPING,
    "AUTHORIZED_SEGMENT_SET": DIRECT_SCHEMA_CARRIER_NOT_INSTANCE, "KNOWABLE_AT": MISSING_EXACT_SOURCE_MAPPING,
    "ADMISSIBILITY_STATE": INTERNAL_DERIVATION_UNBOUND, "VINTAGE_REF": PARTIAL_SOURCE_CARRIER}
FIELDS = tuple(SOURCE_STATUS)
ACTUAL_BINDINGS = {f: None for f in FIELDS}            # source: all ten UNDECLARED_REAL_PAYLOAD_BINDING

def source_status(field: str) -> str:
    if field not in SOURCE_STATUS:
        raise Refusal(str(field), code="UNKNOWN_DESCRIPTOR_FIELD")
    return SOURCE_STATUS[field]

def require_real_binding(field: str, bindings: dict = None) -> object:
    """Return the declared real binding or refuse. Fields whose source mapping is MISSING/INTERNAL are refused even if a binding is
    supplied: their closure needs a justified derivation this repository cannot verify."""
    st = source_status(field)
    b = (ACTUAL_BINDINGS if bindings is None else bindings).get(field)
    if b is None:
        raise Refusal(field, code="UNDECLARED_REAL_PAYLOAD_BINDING")
    if st in (MISSING_EXACT_SOURCE_MAPPING, INTERNAL_DERIVATION_UNBOUND):
        raise Refusal(field, code="DERIVATION_NOT_VERIFIABLE")
    return b

def require_all(bindings: dict = None) -> None:
    for f in FIELDS: require_real_binding(f, bindings)
