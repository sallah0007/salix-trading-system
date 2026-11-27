"""Generic bounded Health EVIDENCE adapters over records this repository already produces (Typed Annex XVII: Health supplies evidence only; MasterHealth V3 B0 is the SOLE operative envelope: no competing schema, no second Health authority; Build Plan 14/14A subject list).
Each adapter returns a `HealthObservation`: a subject KIND, the FACTS read from the existing record (counts, statuses, reason codes, hashes), the exact source-record reference, and `held_slots` naming every B0 envelope field that remains SOURCE-OWNED and UNBOUND
(HEALTH_PROFILE_*, HEALTH_POLICY_*, CRITICAL_SET_*, REASON_CODE registry, producer identity/signature, thresholds, expectation state). An observation never carries a HEALTHY/NOT_HEALTHY verdict: mapping facts to a state needs a governed policy (thresholds are DEFERRED by the source),
so `state_for(obs, policy)` applies a SUPPLIED policy callable and labels the result CALLER_POLICY_UNADMITTED; with no policy the state is UNKNOWN (never HEALTHY). Facts are read, never fabricated: an absent record yields `facts=None`/UNKNOWN, not an empty healthy reading.
These adapters are not a Health service, emit nothing to a Health authority and change no status."""
from dataclasses import dataclass
from typing import Optional
from ..errors import Refusal
B0_HELD_SLOTS = ("HEALTH_PROFILE_ID/VERSION", "HEALTH_POLICY_ID/VERSION", "CRITICAL_SET_ID/VERSION", "REASON_CODE registry", "PRODUCER_ID/VERSION", "PRODUCER_SIGNATURE_OR_INTEGRITY_BINDING", "thresholds", "EXPECTATION_STATE")
KINDS = ("MATERIALIZATION_ROW", "SCHEDULER_RESOURCE_STATE", "GATEWAY_BINDING_NON_DELIVERY", "FW_RETURNS", "ML_GENERATION_AND_CLAIMS")
STATES = ("HEALTHY", "NOT_HEALTHY", "UNKNOWN")

@dataclass(frozen=True)
class HealthObservation:
    kind: str; facts: Optional[dict]; source_ref: str; held_slots: tuple = B0_HELD_SLOTS; admitted: bool = False
    subject: Optional[tuple] = None      # R36: ((field, value), ...) the record's OWN subject binding (Typed Annex XVII 616-662: feature/version/instrument/timeframe/materialization evidence fields); None = the record carries none
    scope: str = "UNSCOPED"              # "SUBJECT" (facts about one feature subject, bound by `subject`) | "GLOBAL:<name>" (declared global statistics, never attributed to a feature automatically) | "UNSCOPED" (no declared scope: attributed to nothing)

def from_verification_result(res, source_ref: str) -> HealthObservation:
    from ..tracker.verification.verification_result import VerificationResult, split_levels, result_is_self_consistent
    if not isinstance(res, VerificationResult): return HealthObservation("MATERIALIZATION_ROW", None, source_ref)
    l1, l2 = split_levels(res)
    return HealthObservation("MATERIALIZATION_ROW", {"status": res.status, "scope": res.scope, "l1": l1, "l2": l2, "failed_checks": tuple(sorted(n for n, ok in res.checks if not ok)), "reasons": tuple(res.reasons), "result_hash": res.result_hash, "self_consistent": result_is_self_consistent(res)}, source_ref, subject=tuple(res.subject), scope="SUBJECT")

def from_reverify_pass(core, pass_id: str) -> HealthObservation:
    p = core.reverify_pass(pass_id)
    if p is None: return HealthObservation("SCHEDULER_RESOURCE_STATE", None, "reverify_pass:" + str(pass_id))
    items = p["items"]; by = {}
    for it in items: by[it[2]] = by.get(it[2], 0) + 1                       # outcome is the third element (subject, trigger, outcome, ...)
    return HealthObservation("SCHEDULER_RESOURCE_STATE", {"at": p["at"], "max_items": p["max_items"], "items": len(items), "by_outcome": dict(sorted(by.items())), "skipped": sum(v for k, v in by.items() if k.startswith("SKIPPED"))}, "reverify_pass:" + pass_id, scope="GLOBAL:REVERIFY_PASS")

def from_final_store(store) -> HealthObservation:
    out = store.outcomes(); by = {}
    for ident, o in out:
        k = type(o).__name__ + (":" + o.reason if type(o).__name__ == "NonDeliveryResolution" else ""); by[k] = by.get(k, 0) + 1
    return HealthObservation("GATEWAY_BINDING_NON_DELIVERY", {"windows": len(out), "by_outcome": dict(sorted(by.items()))}, "final_resolution_store", scope="GLOBAL:FINAL_RESOLUTION_STORE")

def from_fw_association(assoc) -> HealthObservation:
    rets = assoc.all_returns(); by = {}
    for r in rets: by[r.return_class] = by.get(r.return_class, 0) + 1
    return HealthObservation("FW_RETURNS", {"returns": len(rets), "by_class": dict(sorted(by.items())), "payload_fields": "HELD_UNBOUND"}, "fw_association", scope="GLOBAL:FW_ASSOCIATION")

def from_claim_ledger(claims, registry_correlations: dict = None) -> HealthObservation:
    cs = claims.claims(); corr = dict(registry_correlations or {})
    return HealthObservation("ML_GENERATION_AND_CLAIMS", {"claims": len(cs), "authority_bearing": sum(1 for c in cs if c.authority_bearing), "writer_correlations": {k: v for k, v in sorted(corr.items())}}, "claim_ledger", scope="GLOBAL:CLAIM_LEDGER")

def state_for(obs: HealthObservation, policy=None):
    """(state, label). No policy -> UNKNOWN. A supplied policy must return exactly HEALTHY / NOT_HEALTHY / UNKNOWN; anything else refuses. An observation without facts is UNKNOWN whatever the policy says."""
    if not isinstance(obs, HealthObservation): raise Refusal("obs", code="NOT_A_HEALTH_OBSERVATION")
    if obs.facts is None or policy is None: return "UNKNOWN", ("NO_FACTS" if obs.facts is None else "NO_POLICY_SUPPLIED")
    st = policy(obs.facts)
    if st not in STATES or type(st) is not str: raise Refusal(repr(st), code="HEALTH_POLICY_RESULT_INVALID")
    return st, "CALLER_POLICY_UNADMITTED"
