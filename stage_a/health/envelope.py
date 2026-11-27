"""Master Health Extension V3 section B0 common envelope, anti-replay, silence derivation and recovery gating as pure validators.
Source: Drive 1paXK6vPORaZ4QtQo3Vv3f49h7w2oHVt1-McSC2g6Bkk (read read-only; connector read, bytes not retained). Reason codes and their recovery
classes live in a governed registry this repository does not have; thresholds, flap limits and critical-set membership are DEFERRED by the
source, so none is invented. News/Context Health has no governed profile home yet (source G): that blocks first FW/ML execution and is not
solved here. Health evidence never becomes control (H: BLOCK != CONTROL)."""
import json
from ..errors import Refusal

REQUIRED = ("SOURCE_AUTHORITY_REF", "SUBJECT_IDENTITY", "PRODUCER_ID", "PRODUCER_VERSION", "HEALTH_PROFILE_ID", "HEALTH_PROFILE_VERSION",
            "HEALTH_POLICY_ID", "HEALTH_POLICY_VERSION", "PRODUCER_REPORTED_LOCAL_STATE", "EVIDENCE_REF", "REASON_CODE", "REASON_CODE_VERSION",
            "EXPECTATION_STATE", "VALIDITY_EXPIRES_AT", "CRITICAL_SET_ID", "CRITICAL_SET_VERSION", "HEALTH_EVENT_ID", "EFFECTIVE_ASOF",
            "AVAILABLE_ASOF", "EFFECTIVE_FROM", "EFFECTIVE_TO", "EFFECTIVE_FROM_BASIS", "LAST_VERIFIED_GOOD_AT", "PRODUCER_SEQUENCE",
            "PRODUCER_SIGNATURE_OR_INTEGRITY_BINDING", "HEALTH_ENVELOPE_SCHEMA_VERSION")
WHERE_APPLICABLE = ("SUBJECT_VERSION_OR_HASH", "BLOCKING_CRITICAL_SET", "DEPENDENCY_UPSTREAM_REFS", "DERIVED_OPERATIONAL_STATE",
                    "INCIDENT_ROOT_CAUSE_REF", "ACTION_CONSEQUENCE_REF")
EXPECTATION = ("EXPECTED", "NOT_EXPECTED", "EXPECTATION_UNKNOWN")
FROM_BASIS = ("OBSERVED", "INFERRED_RETROACTIVE", "UNKNOWN")
RECOVERY = ("TRANSIENT_AUTO_RECOVERABLE", "EVIDENCE_REVALIDATION_REQUIRED", "AUTHORISED_RESTORATION_REQUIRED")

def check_envelope(e: dict, known_schema_versions) -> None:
    if "ML_LOCAL_STATE" in e:
        raise Refusal("ML_LOCAL_STATE", code="SECOND_LOCAL_STATE_FIELD")       # ML Health V2: only PRODUCER_REPORTED_LOCAL_STATE may be emitted
    if "EVIDENCE_REFS" in e:
        raise Refusal("EVIDENCE_REFS", code="COMPETING_EVIDENCE_FIELD")      # plural alias must map to one EVIDENCE_REF before it goes outward
    missing = [k for k in REQUIRED if e.get(k) is None]
    if missing:
        raise Refusal(",".join(missing), code="HEALTH_ENVELOPE_FIELD_MISSING")
    si = e["SUBJECT_IDENTITY"]
    if not isinstance(si, dict) or si.get("AUTHORITY_STATE") is None or si.get("INSTRUMENT_ID") is None:
        raise Refusal("SUBJECT_IDENTITY", code="SUBJECT_IDENTITY_INCOMPLETE")  # feed/instrument boundaries may not collapse
    if e["EXPECTATION_STATE"] not in EXPECTATION:
        raise Refusal(str(e["EXPECTATION_STATE"]), code="BAD_EXPECTATION_STATE")
    if e["EFFECTIVE_FROM_BASIS"] not in FROM_BASIS:
        raise Refusal(str(e["EFFECTIVE_FROM_BASIS"]), code="BAD_EFFECTIVE_FROM_BASIS")
    et = e["EFFECTIVE_TO"]
    if et != "OPEN" and (type(et) is not int or et < e["EFFECTIVE_FROM"]):
        raise Refusal(str(et), code="BAD_EFFECTIVE_TO")
    if type(e["PRODUCER_SEQUENCE"]) is not int or e["PRODUCER_SEQUENCE"] < 0:
        raise Refusal("PRODUCER_SEQUENCE", code="BAD_PRODUCER_SEQUENCE")
    if e["HEALTH_ENVELOPE_SCHEMA_VERSION"] not in known_schema_versions:
        raise Refusal(str(e["HEALTH_ENVELOPE_SCHEMA_VERSION"]), code="UNKNOWN_ENVELOPE_SCHEMA_VERSION")
    # LAST_VERIFIED_GOOD_AT is in the B0 required list, so the unknown-onset back-bound is already enforced by the missing-field check.

class AntiReplay:
    """PRODUCER_SEQUENCE must strictly increase per (producer, subject). A replayed or stale packet is refused and changes nothing,
    so a replayed HEALTHY cannot restore current Health. In-memory, single process (provider/atomicity decisions unchanged)."""
    def __init__(self):
        self._last = {}
    def admit(self, e: dict, integrity_ok: bool) -> None:
        if not integrity_ok:
            raise Refusal("integrity binding failed", code="HEALTH_INTEGRITY_BINDING_FAILED")   # validated before authority-bearing use
        si = e["SUBJECT_IDENTITY"]
        try: subject = json.dumps(si, sort_keys=True, allow_nan=False)           # the FULL validated subject scope (no canonical ID field/layout is invented): distinct subjects never share a sequence
        except (TypeError, ValueError): raise Refusal("SUBJECT_IDENTITY", code="SUBJECT_IDENTITY_NOT_SERIALIZABLE")
        key = (e["PRODUCER_ID"], subject, e.get("SUBJECT_VERSION_OR_HASH"))
        last = self._last.get(key)
        if last is not None and e["PRODUCER_SEQUENCE"] <= last:
            raise Refusal(e["PRODUCER_SEQUENCE"], code="HEALTH_REPLAY_OR_STALE")
        self._last[key] = e["PRODUCER_SEQUENCE"]

def derive_silence(now: int, validity_expires_at: int, expectation: str):
    """NO_HEARTBEAT after validity expiry derives STALE_NO_PRODUCER; silence is never HEALTHY; EXPECTATION_UNKNOWN != NOT_EXPECTED."""
    if expectation not in EXPECTATION:
        raise Refusal(expectation, code="BAD_EXPECTATION_STATE")
    if now <= validity_expires_at:
        return None
    if expectation == "EXPECTED":
        return "STALE_NO_PRODUCER"
    if expectation == "EXPECTATION_UNKNOWN":
        return "EXPECTATION_UNKNOWN_SILENCE"
    return "NOT_APPLICABLE_SILENCE"

def may_clear(recovery_class: str, evidence_kind: str) -> bool:
    """A heartbeat alone never clears anything beyond what its class allows. AUTHORISED_RESTORATION_REQUIRED never self-clears at Health:
    restoration is a governed lifecycle/Decision Context event."""
    if recovery_class not in RECOVERY:
        raise Refusal(recovery_class, code="UNKNOWN_RECOVERY_CLASS")                     # fail closed on the unread
    if recovery_class == "AUTHORISED_RESTORATION_REQUIRED":
        return False
    if recovery_class == "EVIDENCE_REVALIDATION_REQUIRED":
        return evidence_kind == "REVALIDATION_PROOF"
    return evidence_kind in ("FRESH_QUALIFYING_EVIDENCE", "REVALIDATION_PROOF")

# ---- Master Health V3 invariants (sections 5, 10): aggregate masking and upstream-vs-local attribution -------------------------
def aggregate_state(members) -> str:
    """AGGREGATE_HEALTHY cannot mask a critical member. members = iterable of (producer_reported_state, is_critical).
    Only the literal 'HEALTHY' counts as healthy; any other, missing or unknown state is not healthy (state vocabulary is not
    enumerated in the sources read, so none is invented). Empty input is UNKNOWN, never HEALTHY. Critical-set MEMBERSHIP is supplied
    by the caller (its registry is DEFERRED, D18)."""
    members = list(members)
    if not members:
        return "UNKNOWN"
    if any(c and s != "HEALTHY" for s, c in members):
        return "BLOCKED_BY_CRITICAL_MEMBER"
    if all(s == "HEALTHY" for s, _ in members):
        return "AGGREGATE_HEALTHY"
    return "NON_CRITICAL_MEMBER_NOT_HEALTHY"

def attribute_failure(independent_local_evidence: bool, upstream_unhealthy: bool) -> tuple:
    """Causes that may be reported. BLOCKED_BY_UPSTREAM != local failure unless independent local evidence exists, and (ML Health V2 s4)
    an upstream problem and an independent local defect may coexist and MUST NOT be merged into one cause, so both are returned."""
    causes = []
    if independent_local_evidence:
        causes.append("LOCAL_FAILURE")
    if upstream_unhealthy:
        causes.append("BLOCKED_BY_UPSTREAM")
    return tuple(causes) if causes else ("NO_FAILURE_ATTRIBUTED",)
