"""Composer s7A APPEND request-record validation (source-stated enums and constraints only; Composer V9 export s7A APPEND, read in R10).
Shape/enum validation of a request record. It issues no order, resolves no REQUESTER_ID (a registered identity needs a registry that does not
exist here), and computes no IDENTITY_KEY. Placement note: not in the Build Plan E-03 module map (see coder_returns R10 section on E-03)."""
from ..errors import Refusal

REQUESTER_TYPES = ("OWNER", "MANAGER", "AI", "FORWARD_WALK", "MACHINE_LEARNING", "DIAGNOSTIC", "MANUAL_REVIEW", "OTHER_GOVERNED_PROCESS")
REQUEST_CLASSES = ("GOVERNED_INTAKE_REQUEST", "STREAM_B_EXPLORATION_REQUEST")
TARGET_CONSUMERS = ("FORWARD_WALK", "MACHINE_LEARNING", "BOTH", "UNKNOWN")
REQUEST_CONTEXTS = ("MANUAL_CHECKUP", "FW_MANIFEST_NEED", "ML_DATASET_OR_MODEL_NEED", "DIAGNOSTIC_GAP", "RESEARCH_HYPOTHESIS", "CORRECTION", "OTHER")
STAGES = ("PROPOSAL", "ORDER")

def _text(rec, k, code):
    v = rec.get(k)
    if type(v) is not str or not v.strip(): raise Refusal(k, code=code)
    return v

def check_request_record(rec: dict, stage: str) -> str:
    """Return 'OK' or 'REVIEW_REQUIRED'; refuse otherwise. Stage ORDER additionally needs PURPOSE_STATEMENT and a resolved TARGET_CONSUMER."""
    if stage not in STAGES: raise Refusal(str(stage), code="REQUEST_STAGE_UNKNOWN")
    if not isinstance(rec, dict): raise Refusal(type(rec).__name__, code="REQUEST_NOT_A_RECORD")
    for k, allowed in (("REQUESTER_TYPE", REQUESTER_TYPES), ("REQUEST_CLASS", REQUEST_CLASSES),
                       ("TARGET_CONSUMER", TARGET_CONSUMERS), ("REQUEST_CONTEXT", REQUEST_CONTEXTS)):
        if rec.get(k) not in allowed: raise Refusal("%s=%r" % (k, rec.get(k)), code="REQUEST_ENUM_VALUE_NOT_IN_SOURCE_LIST")
    _text(rec, "REQUEST_SCHEMA_VERSION", "REQUEST_FIELD_MISSING")
    _text(rec, "REQUESTER_ID", "REQUEST_FIELD_MISSING")                    # free text is not an identity; resolution is NOT performed here
    if rec["REQUEST_CLASS"] == "STREAM_B_EXPLORATION_REQUEST" and rec.get("REQUEST_ORIGIN") != "FORWARD_WALK":
        raise Refusal(str(rec.get("REQUEST_ORIGIN")), code="STREAM_B_ORIGIN_NOT_FORWARD_WALK")
    if rec["REQUEST_CONTEXT"] == "OTHER" or rec["REQUESTER_TYPE"] == "OTHER_GOVERNED_PROCESS":
        _text(rec, "GOVERNED_REASON", "REQUEST_OTHER_WITHOUT_GOVERNED_REASON")
    if rec["REQUEST_CONTEXT"] == "CORRECTION":
        _text(rec, "DEFECT_EVIDENCE_REF", "REQUEST_CORRECTION_WITHOUT_EVIDENCE_REF")
    if stage == "ORDER":
        _text(rec, "PURPOSE_STATEMENT", "REQUEST_PURPOSE_STATEMENT_MISSING")
        if rec["TARGET_CONSUMER"] == "UNKNOWN": return "REVIEW_REQUIRED"
    return "OK"
