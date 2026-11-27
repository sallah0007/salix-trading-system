"""Resource ceilings and capability declaration (Parent V1.2 'CAPABILITY-EMULATION FIREWALL' / Annex V1.2 certification requirements 1-6).
SOURCE-BOUND: RESOURCE_CEILING_REF must resolve and bind seven governed integer ceilings; 'no silent infrastructure default is permitted'.
This module chooses NO numeric value. Absence of the ref or of any ceiling refuses. The values are supplied by the caller from the resolved governed
artifact (resolving the REF to an immutable artifact is the artifact store's job and is OPEN here; supplied values are CLAIMED, not authenticated).
NOT enforced (exact missing semantic rules): MAX_STATE_ELEMENTS counting for the prototype lag/rolling constructs (the source defines no state-element
count for them); MAX_BRANCH_COUNT/MAX_VECTOR_LENGTH/MAX_MATRIX_* have no construct in this prototype manifest (select/vector/matrix are not manifest opcodes: no
numeric wire opcode table exists), so they are trivially unexercised, not 'passed'.
Class-to-structure compatibility (Annex req. 3) is NOT decidable from the source read: no rule maps a class to permitted structure. Declared class is
checked only against the five-value enum; ambiguity fails closed."""
from ...errors import Refusal

CEILING_KEYS = ("MAX_OPCODE_COUNT_PER_PROGRAM", "MAX_BRANCH_COUNT", "MAX_VECTOR_LENGTH", "MAX_MATRIX_ROWS", "MAX_MATRIX_COLS",
                "MAX_STATE_ELEMENTS", "MAX_REDUCTION_LENGTH")
CAPABILITY_CLASSES = ("SCALAR_RECURRENCE", "ELEMENTWISE_FIXED_SHAPE_RECURRENCE", "BOUNDED_REDUCTION", "BOUNDED_STATE_TABLE", "SCALAR_CLOSED_FORM_RATIO")
REDUCTION_OPS = ("rolling_sum", "rolling_mean")          # sequential accumulation over a declared window ~ FIXED_SUM (opcodes.py mapping)

def _int(v): return isinstance(v, int) and not isinstance(v, bool)

def check_ceilings(ref, values) -> dict:
    if not isinstance(ref, str) or not ref.strip():
        raise Refusal(str(ref), code="RESOURCE_CEILING_REF_MISSING")
    if not isinstance(values, dict):
        raise Refusal(type(values).__name__, code="RESOURCE_CEILINGS_NOT_SUPPLIED")
    for k in CEILING_KEYS:
        if k not in values:
            raise Refusal(k, code="RESOURCE_CEILING_VALUE_MISSING")       # no default is ever substituted
        if not _int(values[k]) or values[k] < 0:
            raise Refusal("%s=%r" % (k, values[k]), code="RESOURCE_CEILING_NOT_A_NONNEGATIVE_INTEGER")
    return {k: values[k] for k in CEILING_KEYS}

def check_program_within(m, ceilings: dict) -> None:
    nodes = m.data["nodes"]
    if len(nodes) > ceilings["MAX_OPCODE_COUNT_PER_PROGRAM"]:
        raise Refusal("%d>%d" % (len(nodes), ceilings["MAX_OPCODE_COUNT_PER_PROGRAM"]), code="CEILING_OPCODE_COUNT_EXCEEDED")
    for n in nodes:
        if n["op"] in REDUCTION_OPS and n["n"] > ceilings["MAX_REDUCTION_LENGTH"]:
            raise Refusal("%s n=%d>%d" % (n["id"], n["n"], ceilings["MAX_REDUCTION_LENGTH"]), code="CEILING_REDUCTION_LENGTH_EXCEEDED")

def check_capability_declaration(decl, m, ceiling_ref) -> None:
    """Exactly one declaration for the program; class in the five-value enum; OPCODE_SET_USED has no duplicates and equals the extracted set; the
    declaration's RESOURCE_CEILING_REF equals the package's. Order 'canonical ascending opcode code' cannot be checked: no code table exists."""
    from .capability import extract_opcodes
    if not isinstance(decl, dict):
        raise Refusal(type(decl).__name__, code="CAPABILITY_DECLARATION_MISSING")
    if decl.get("PROGRAM_CAPABILITY_CLASS") not in CAPABILITY_CLASSES:
        raise Refusal(str(decl.get("PROGRAM_CAPABILITY_CLASS")), code="CAPABILITY_CLASS_NOT_ADMITTED_ROUTE_GENERIC_EXTENSION")
    used = decl.get("OPCODE_SET_USED")
    if not isinstance(used, list) or len(set(used)) != len(used):
        raise Refusal(str(used), code="OPCODE_SET_USED_INVALID_OR_DUPLICATE")
    if sorted(used) != extract_opcodes(m):
        raise Refusal("declared=%s extracted=%s" % (sorted(used), extract_opcodes(m)), code="OPCODE_SET_USED_DIFFERS_FROM_PROGRAM")
    if decl.get("RESOURCE_CEILING_REF") != ceiling_ref:
        raise Refusal(str(decl.get("RESOURCE_CEILING_REF")), code="DECLARATION_CEILING_REF_DIFFERS")
    if not isinstance(decl.get("PROGRAM_REF"), str) or not decl["PROGRAM_REF"].strip():
        raise Refusal("PROGRAM_REF", code="CAPABILITY_DECLARATION_PROGRAM_REF_MISSING")
