"""Seven-field producer binding ADMISSION against a SUPPLIED authoritative lookup (C25 register: 'Missing is UNSATISFIED'). Different object from Composer 27/28 BUILD_OUTPUT_PACKAGE conformance: a producer binding names the producer interface a payload field comes from;
a build-output package is evidence about one build. Neither passing implies the other.
Admission here is EXACT EQUALITY, field by field, between the presented record and the record a supplied `authority(scope, interface_id, version)` returns for that exact key (None -> UNSATISFIED_NO_AUTHORITY_RECORD). It does not parse `validity/supersession` (no grammar in any source
read): the authority record is the only judge, and an authority record whose validity/supersession differs from the presented one is a mismatch, never a pass. Nothing supplies the authority here: the lookup is a SOURCE-OWNED input (governed Drive record is Manager-only), so every
decision is labelled `qualified=False` and `authority_source_ref` must be supplied and is echoed, never defaulted."""
from dataclasses import dataclass
from ..errors import Refusal
from .producer_binding import check_shape, SEVEN_FIELDS
ADMITTED_AGAINST_SUPPLIED_AUTHORITY, UNSATISFIED = "ADMITTED_AGAINST_SUPPLIED_AUTHORITY", "UNSATISFIED"

@dataclass(frozen=True)
class AdmissionDecision:
    status: str; reason: str; authority_source_ref: str; qualified: bool = False

def admit(rec, authority, authority_source_ref) -> AdmissionDecision:
    if not (isinstance(authority_source_ref, str) and authority_source_ref.strip()) or not callable(authority): raise Refusal("authority", code="PRODUCER_ADMISSION_AUTHORITY_NOT_SUPPLIED")
    try: check_shape(rec)
    except Refusal as e: return AdmissionDecision(UNSATISFIED, "SHAPE:" + e.code, authority_source_ref)
    a = authority(rec["scope"], rec["interface_id"], rec["version"])
    if a is None: return AdmissionDecision(UNSATISFIED, "UNSATISFIED_NO_AUTHORITY_RECORD", authority_source_ref)
    try: check_shape(a)
    except Refusal as e: return AdmissionDecision(UNSATISFIED, "AUTHORITY_RECORD_MALFORMED:" + e.code, authority_source_ref)      # a malformed authority answer admits nothing
    diff = [f for f in SEVEN_FIELDS if rec[f] != a[f]]
    return AdmissionDecision(UNSATISFIED, "FIELD_MISMATCH:" + ",".join(diff), authority_source_ref) if diff else AdmissionDecision(ADMITTED_AGAINST_SUPPLIED_AUTHORITY, "", authority_source_ref)
