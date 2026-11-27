"""Build Plan 14 required Health SUBJECT list (quant manifest/profile; fit generation; materialization row; recording verification; scheduler/resource state; Gateway binding/non-delivery; FW/ML carried-upstream impact; replay backlog) and 14A
(CARRIED_UPSTREAM_STATE is recorded as carried evidence and never overwrites the subject's LOCAL_STATE; blast radius comes from declared lineage, not by copying an upstream status downward).
This is a COVERAGE report, not a Health authority and not a Health state writer. Only three kinds have an evidence source in this repository today: RECORDING_VERIFICATION (Core recording health), GATEWAY_BINDING_NON_DELIVERY (a SUPPLIED Core health snapshot) and the
carried-upstream impact (Core blast radius over DECLARED edges only). Every other kind has NO evidence source here and is reported `NO_EVIDENCE_SOURCE` unless the caller SUPPLIES a typed reading (labelled CALLER_ASSERTED_UNADMITTED). A kind without evidence is never HEALTHY,
so the local aggregate is HEALTHY only when all eight kinds carry HEALTHY readings; completeness itself is unadmitted (profile/thresholds/appointment are source-owned and unbound)."""
from dataclasses import dataclass
from ..errors import Refusal
KINDS = ("QUANT_MANIFEST_PROFILE", "FIT_GENERATION", "MATERIALIZATION_ROW", "RECORDING_VERIFICATION", "SCHEDULER_RESOURCE_STATE", "GATEWAY_BINDING_NON_DELIVERY", "FW_ML_CARRIED_UPSTREAM_IMPACT", "REPLAY_BACKLOG")
LOCAL_KINDS = tuple(k for k in KINDS if k != "FW_ML_CARRIED_UPSTREAM_IMPACT")
STATES = ("HEALTHY", "NOT_HEALTHY", "UNKNOWN")
NO_SOURCE = "NO_EVIDENCE_SOURCE"

@dataclass(frozen=True)
class SubjectCoverage:
    local: tuple                 # ((kind, state, source), ...) for the seven LOCAL kinds
    carried: tuple               # ((kind, dependents), ...) carried-upstream IMPACT evidence; never a state
    local_aggregate: str         # HEALTHY only if every LOCAL kind is HEALTHY; NOT_HEALTHY if any is; else UNKNOWN
    complete: bool               # every LOCAL kind has a reading (not an acceptance)
    admitted: bool = False

def coverage(core, subject: str, version: str, now: int, *, gateway_snapshot=None, supplied=None) -> SubjectCoverage:
    supplied = supplied or {}
    if not isinstance(supplied, dict) or set(supplied) - set(LOCAL_KINDS): raise Refusal("supplied", code="HEALTH_SUBJECT_KIND_UNKNOWN")
    local = []
    for k in LOCAL_KINDS:
        if k in supplied:
            if supplied[k] not in STATES: raise Refusal(k, code="HEALTH_SUBJECT_STATE_INVALID")
            local.append((k, supplied[k], "CALLER_ASSERTED_UNADMITTED"))
        elif k == "RECORDING_VERIFICATION":
            r = core.recording_health(subject, version, now); local.append((k, r.state if r.state in STATES else "UNKNOWN", r.evidence_class))      # a qualified core reports HELD -> not HEALTHY
        elif k == "GATEWAY_BINDING_NON_DELIVERY" and gateway_snapshot is not None:
            if not core.confirm_snapshot(gateway_snapshot) or gateway_snapshot.subject != subject or not core.snapshot_current_at_use(gateway_snapshot, now): local.append((k, "UNKNOWN", "SNAPSHOT_NOT_CONFIRMED_FOR_SUBJECT_OR_NOT_CURRENT_AT_USE"))
            else: local.append((k, "HEALTHY" if gateway_snapshot.acceptable else "NOT_HEALTHY", gateway_snapshot.evidence_class))
        else: local.append((k, "UNKNOWN", NO_SOURCE))
    sts = [s for _, s, _ in local]
    agg = "NOT_HEALTHY" if "NOT_HEALTHY" in sts else ("HEALTHY" if all(s == "HEALTHY" for s in sts) else "UNKNOWN")
    carried = (("FW_ML_CARRIED_UPSTREAM_IMPACT", tuple(core.blast_radius(subject)["dependents"])),)
    return SubjectCoverage(tuple(local), carried, agg, all(src != NO_SOURCE for _, _, src in local))
