"""Binding of a Gateway ABSENCE / NON-DELIVERY outcome to the exact declared dependency and to an actually ISSUED immutable Gateway outcome (Annex V1.2 s X: absence is versioned, manifest-bound,
model-defined, recorded; s XIV: per-dependency absence keyed by FEATURE_ID + FEATURE_VERSION). A binding branch already checks origin; an absence/non-delivery branch must not bypass provenance
by returning early. `gateway=None` means the caller asked for a SHAPE-ONLY check (no origin proof) and the result is labelled so by the caller's API (see fw.receiver.receive_verified)."""
from ..errors import Refusal
from .contracts import AbsenceApplied, NonDeliveryResolution, DependencyEntry, OPTIONAL

def check_dependency_outcome(o, e: DependencyEntry, gateway):
    if not isinstance(o, (AbsenceApplied, NonDeliveryResolution)):
        raise Refusal(type(o).__name__, code="UNKNOWN_OUTCOME_TYPE")
    if o.feature_id != e.feature_id or o.feature_version != e.feature_version:
        raise Refusal("outcome for a different dependency", code="ABSENCE_FOR_DIFFERENT_DEPENDENCY")
    if isinstance(o, AbsenceApplied):
        if e.requirement_class != OPTIONAL or e.absence_rule_ref is None or o.absence_handling_applied_ref != e.absence_rule_ref:
            raise Refusal("absence only via the exact governed rule", code="ABSENCE_RULE_MISMATCH")
    if gateway is not None and gateway.outcome(o.request_id) is not o:
        raise Refusal(o.request_id, code="OUTCOME_NOT_FROM_GATEWAY")          # forged / foreign / replayed outcome: not the stored immutable one
