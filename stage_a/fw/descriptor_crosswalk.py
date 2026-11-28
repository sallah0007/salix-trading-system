"""FW ten-field descriptor crosswalk (documentary), from the finite mapping/dependency disposition (Drive 12h77ZuFRezmZr4_8Zrs1BDyYUtpnoMlI,
61,967 B; R52: raw bytes downloaded, SHA-256 ea9e7949397dd1e9ad001334425fdfeb96706d7eadca67bd043496d6ec91dfc0 RECOMPUTED = match; FW_crosswalk rows 10/10 compared field-by-field to SOURCE_STATUS = match). It is documentary requirements/mapping, NOT a second FW/ML
interface authority. Every actual payload binding is UNDECLARED in that source, so this module's only behaviour is fail-closed refusal:
no descriptor value may be produced from a payload until an exact real binding exists. Nothing here selects a binding.

BOUNDARY (R09): DOCUMENTARY_LOOKUP_ONLY. No authority-bearing consumer exists in this repository (checked by grep); this module must not be
wired into admission/delivery. A caller-supplied binding is accepted only if it has the seven-field producer-binding SHAPE
(stage_a.binding.producer_binding); shape is not admission, so a returned value is still unverified evidence, never an authorization."""
from ..errors import Refusal
from ..binding.producer_binding import check_shape
DOCUMENTARY_LOOKUP_ONLY = True

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
    return check_shape(b)

def require_all(bindings: dict = None) -> None:
    for f in FIELDS: require_real_binding(f, bindings)


# R52: REVIEWABLE statement of exactly what is missing per field. Documentary only: it produces no value, selects no binding, and is not an admission or an authorization.
SOURCE_RELATION = {   # own-word reading of the A04 FW_crosswalk row (Manager-decoded raw payload, R52); NOT governing text
    "OBSERVATION_REF": "H3 series identity plus observation-time origin: only a PARTIAL carrier; it does not identify one observation uniquely",
    "DEPENDENCY_INTERVAL_START": "direct H3 field; exact boundary units/profile are required before any value is read",
    "DEPENDENCY_INTERVAL_END": "direct H3 field; exact boundary units/profile are required before any value is read",
    "HORIZON_ID": "direct H3 field", "HORIZON_VERSION": "direct H3 field",
    "SEGMENT_REF": "no direct mapping is demonstrated: the authorized segment set is not per-observation membership",
    "AUTHORIZED_SEGMENT_SET": "carried by the H3 authorized-segment-set/stage pair plus the consumer stage",
    "KNOWABLE_AT": "no demonstrated direct field: AVAILABLE_ASOF is a decision cutoff, not per-observation knowability",
    "ADMISSIBILITY_STATE": "FW-owned derived state: no external enum or default exists to bind",
    "VINTAGE_REF": "constrained only by policy/mode: not an exact per-observation vintage identity"}
def binding_declaration_review(bindings: dict = None) -> list:
    """One row per field: the A04 status, the source relation, whether a real payload binding is declared, and the exact missing slots. A row is `CLOSABLE_BY_BINDING_DECLARATION` only for DIRECT/PARTIAL fields; MISSING/INTERNAL fields are
    `NOT_CLOSABLE_BY_BINDING` (they need a source mapping or an FW-owned derivation, which no binding can supply)."""
    b = ACTUAL_BINDINGS if bindings is None else bindings; rows = []
    for f in FIELDS:
        st = SOURCE_STATUS[f]; declared = b.get(f) is not None; closable = st not in (MISSING_EXACT_SOURCE_MAPPING, INTERNAL_DERIVATION_UNBOUND)
        missing = []
        if closable:
            if not declared: missing.append("real payload binding: a seven-field producer binding (" + ", ".join(__import__("stage_a.binding.producer_binding", fromlist=["x"]).SEVEN_FIELDS) + ")")
            missing.append("exact payload key naming where the value lives in the delivered payload")
        else:
            missing.append("exact source mapping" if st == MISSING_EXACT_SOURCE_MAPPING else "FW-owned derivation definition (owner, enum, defaults)")
        rows.append({"field": f, "a04_status": st, "source_relation": SOURCE_RELATION[f], "actual_payload_binding": "DECLARED_SHAPE_ONLY" if declared and closable else "NULL",
                     "classification": "CLOSABLE_BY_BINDING_DECLARATION" if closable else "NOT_CLOSABLE_BY_BINDING", "missing": missing})
    return rows
