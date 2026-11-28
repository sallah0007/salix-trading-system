"""Canonical FW/ML forecast payload shape (MLCore V1.16 section 26.K, paragraphs 405-424 of the native Drive doc 1cf1uR0wJLPVsWitIy9aVLM9CZPk2fyd4bP_3tFyLKrw, read R52).
Field NAMES and the three SOURCE_LAYER values are the source's. The source says the list applies 'as applicable' and defines no per-field applicability rule, so none is invented here:
every field is required unless the CALLER explicitly names it as not applicable (a declared, visible omission - never a silent one), and the source forbids weakening these semantics
for comparison, replay, audit or cross-instrument use, so a declared omission is returned to the caller and never defaulted. No value domain, byte form or enum is invented for any
other field (PREDICTION, UNCERTAINTY, ...); they must merely be present and not None. Shape check only: not an admission, not an authorization, no model evidence."""
from ..errors import Refusal

FIELDS = ("INSTRUMENT_ID", "FORECAST_TS", "AVAILABLE_ASOF_TS", "TARGET_ID", "TARGET_VERSION", "TARGET_SEMANTICS_ID", "HORIZON_ID", "HORIZON_SEMANTICS_ID",
          "SOURCE_LAYER", "GENERATION_ID", "PREDICTION", "UNCERTAINTY", "CALIBRATION_STATE", "OOD_STATE", "SUPPORT_STATE", "EVIDENCE_CLASS", "AUTHORITY_STATE")
SOURCE_LAYERS = ("FW", "ML_STANDALONE", "ML_FW_AUGMENTED")

def check_forecast_payload(rec, not_applicable=()):
    """Returns the tuple of explicitly-declared not-applicable fields. Refuses: non-dict; unknown not_applicable name; a field both declared not-applicable and present;
    a missing/None required field; SOURCE_LAYER outside the three values; extra keys are allowed (the source allows additional fields)."""
    if not isinstance(rec, dict): raise Refusal(type(rec).__name__, code="FORECAST_PAYLOAD_NOT_A_RECORD")
    na = tuple(not_applicable)
    for n in na:
        if n not in FIELDS: raise Refusal(str(n), code="FORECAST_PAYLOAD_UNKNOWN_NOT_APPLICABLE_FIELD")
        if rec.get(n) is not None: raise Refusal(n, code="FORECAST_PAYLOAD_FIELD_BOTH_PRESENT_AND_NOT_APPLICABLE")
    for f in FIELDS:
        if f in na: continue
        if rec.get(f) is None: raise Refusal(f, code="FORECAST_PAYLOAD_FIELD_MISSING")
    if "SOURCE_LAYER" not in na and rec["SOURCE_LAYER"] not in SOURCE_LAYERS: raise Refusal(str(rec["SOURCE_LAYER"]), code="FORECAST_PAYLOAD_SOURCE_LAYER_INVALID")
    return na
