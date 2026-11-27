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
    extra: tuple = ()            # ((kind, state, source), ...) Stage A subjects outside Build Plan 14's eight (adapter observations); never part of the local aggregate

def _not_for_subject(o, subject, version, expected):
    """'' when the observation is bound to exactly this feature key + version (and the expected record fields); else the reason it is not attributable."""
    if o.scope != "SUBJECT": return "SCOPE_NOT_SUBJECT:" + o.scope
    if not o.subject: return "NO_SUBJECT_BINDING"
    d = dict(o.subject); key = d.get("expect_scope_key")
    if key != subject or not isinstance(key, str) or key.rsplit("/", 1)[-1] != version: return "OBSERVATION_NOT_FOR_REQUESTED_SUBJECT_OR_VERSION"
    for f, v in (expected or {}).items():
        if d.get(f) != v: return "RECORD_FIELD_DIFFERS:" + str(f)
    return ""

def coverage(core, subject: str, version: str, now: int, *, gateway_snapshot=None, supplied=None, observations=None, policies=None, expected_subject_fields=None) -> SubjectCoverage:
    """observations: {kind: health.adapters.HealthObservation} (facts read from existing records); policies: {kind: callable(facts)->state} SUPPLIED and unadmitted. Facts without a policy are UNKNOWN (an evidence source EXISTS, a verdict does not).
    R36 SCOPE: an observation is applied to the requested (subject, version) ONLY if it is SUBJECT-scoped and its own subject binding names exactly that feature key and version (and every `expected_subject_fields` entry, e.g. record_manifest_hash, equals the record's field). A GLOBAL-scoped or UNSCOPED observation is NEVER attributed to a feature: the local reading is UNKNOWN and its facts are shown in `extra` under its declared scope. An unadmitted policy cannot create a missing factual association."""
    from . import adapters as AD
    supplied = supplied or {}; observations = observations or {}; policies = policies or {}
    if not isinstance(observations, dict) or not all(isinstance(o, AD.HealthObservation) and o.kind == k for k, o in observations.items()): raise Refusal("observations", code="HEALTH_OBSERVATION_INVALID")
    if not isinstance(supplied, dict) or set(supplied) - set(LOCAL_KINDS): raise Refusal("supplied", code="HEALTH_SUBJECT_KIND_UNKNOWN")
    local = []
    for k in LOCAL_KINDS:
        if k in supplied:
            if supplied[k] not in STATES: raise Refusal(k, code="HEALTH_SUBJECT_STATE_INVALID")
            local.append((k, supplied[k], "CALLER_ASSERTED_UNADMITTED"))
        elif k == "RECORDING_VERIFICATION":
            r = core.recording_health(subject, version, now); local.append((k, r.state if r.state in STATES else "UNKNOWN", r.evidence_class))      # a qualified core reports HELD -> not HEALTHY
        elif k == "GATEWAY_BINDING_NON_DELIVERY" and gateway_snapshot is not None:
            if not core.confirm_snapshot(gateway_snapshot) or gateway_snapshot.subject != subject or gateway_snapshot.version != version or not core.snapshot_current_at_use(gateway_snapshot, now): local.append((k, "UNKNOWN", "SNAPSHOT_NOT_CONFIRMED_FOR_SUBJECT_VERSION_OR_NOT_CURRENT_AT_USE"))
            else: local.append((k, "HEALTHY" if gateway_snapshot.acceptable else "NOT_HEALTHY", gateway_snapshot.evidence_class))
        elif k in observations:
            o = observations[k]; why = _not_for_subject(o, subject, version, expected_subject_fields)
            if why: local.append((k, "UNKNOWN", "ADAPTER_FACTS:%s:%s" % (o.source_ref, why)))
            else: st, lab = AD.state_for(o, policies.get(k)); local.append((k, st, "ADAPTER_FACTS:%s:%s" % (o.source_ref, lab)))
        else: local.append((k, "UNKNOWN", NO_SOURCE))
    sts = [s for _, s, _ in local]
    agg = "NOT_HEALTHY" if "NOT_HEALTHY" in sts else ("HEALTHY" if all(s == "HEALTHY" for s in sts) else "UNKNOWN")
    carried = (("FW_ML_CARRIED_UPSTREAM_IMPACT", tuple(core.blast_radius(subject)["dependents"])),)
    extra = tuple((k + ("@" + o.scope if o.scope != "SUBJECT" else ""), *AD.state_for(o, policies.get(k))) for k, o in sorted(observations.items()) if k not in LOCAL_KINDS or _not_for_subject(o, subject, version, expected_subject_fields))
    return SubjectCoverage(tuple(local), carried, agg, all(src != NO_SOURCE for _, _, src in local), False, extra)
