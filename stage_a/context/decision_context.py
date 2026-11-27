"""Decision Context V4 envelope/domain rules (A0, A1, F, H, FAIL-CLOSED SAFETY RULE) as pure validators. Source: Drive
1dwGRh2EOxzhQGwV6x6TS4K5FFTu3_TJaES4R4BpW-PQ (read read-only). CONTEXT != AUTHORITY: nothing here grants anything.
No storage/mirror producer is built; DRIVE mirror comparison needs Drive bytes the Coder may read but never write."""
from ..errors import Refusal

DOMAINS = ("TRACKER_LIFECYCLE", "FW_RESEARCH", "ML_GOVERNANCE", "HEALTH_GOVERNANCE",
           "TRACKER_CONSTRUCTION", "OWNER_GOVERNANCE", "CONSUMER_STAGE_GOVERNANCE")
EVENT_DOMAIN = {"construction_order": "TRACKER_CONSTRUCTION", "registration_constraint": "TRACKER_CONSTRUCTION",
                "feature_candidate_lifecycle": "TRACKER_LIFECYCLE", "manifest_change_approval": "TRACKER_CONSTRUCTION",
                "import_package_registry_approval": "TRACKER_CONSTRUCTION", "fw_promotion": "FW_RESEARCH",
                "ml_generation_certification": "ML_GOVERNANCE", "owner_decision_or_waiver": "OWNER_GOVERNANCE",
                "consumer_stage_advancement": "CONSUMER_STAGE_GOVERNANCE", "holdout_unseal": "CONSUMER_STAGE_GOVERNANCE"}
SUBJECT_DOMAIN = {"TRACKER": "TRACKER_LIFECYCLE", "ML": "ML_GOVERNANCE", "HEALTH": "HEALTH_GOVERNANCE"}
ENVELOPE_REQUIRED = ("DECISION_CONTEXT_ID", "CONTEXT_DOMAIN", "ORIGIN", "REASON_CODE", "REASON_CODE_VERSION", "DECLARED_SCOPE",
                     "CONSEQUENCE_CLASS", "PREREQUISITES", "RESIDUALS", "NARRATIVE", "DOMAIN_PAYLOAD", "CREATED_AT", "AVAILABLE_ASOF",
                     "DECISION_EFFECTIVE_AT", "NEXT_ELIGIBLE_ACTION_CLASS", "DECIDED_BY", "EVIDENCE_REFS", "CREATED_BY_SYSTEM_OR_HUMAN",
                     "IMMUTABLE_CONTEXT_HASH")
HUMAN_MIRROR = ("DRIVE_FILE_ID", "DRIVE_REVISION_ID", "CONTENT_HASH", "FULL_DECISION_TEXT", "CANONICAL_CONTEXT_OBJECT_HASH")
STATUS_EVENT_REQUIRED = ("STATUS_EVENT_ID", "SUBJECT_TYPE", "SUBJECT_ID", "PRIOR_STATE", "NEW_STATE", "CREATED_AT", "AVAILABLE_ASOF",
                         "EFFECTIVE_AT", "MACHINE_REASON_CODE", "MACHINE_REASON_CODE_VERSION", "DECISION_CONTEXT_ID", "AUTHORITY_STATE",
                         "RELATED_EVIDENCE_REFS", "EVENT_HASH")

def domain_for_event(event_class: str) -> str:
    d = EVENT_DOMAIN.get(event_class)
    if d is None:
        raise Refusal(event_class, code="UNREGISTERED_CONTEXT_EVENT_CLASS")          # implementers may not invent domains
    return d

def check_envelope(o: dict) -> None:
    if "NEXT_PERMITTED_ACTION" in o:
        raise Refusal("NEXT_PERMITTED_ACTION", code="PERMISSION_FIELD_IN_CONTEXT")   # eligibility is not authorization
    missing = [k for k in ENVELOPE_REQUIRED if o.get(k) is None]
    if missing:
        raise Refusal(",".join(missing), code="ENVELOPE_FIELD_MISSING")
    if o["CONTEXT_DOMAIN"] not in DOMAINS:
        raise Refusal(o["CONTEXT_DOMAIN"], code="UNREGISTERED_CONTEXT_DOMAIN")
    if o["ORIGIN"] not in ("HUMAN_GOVERNANCE", "SYSTEM"):
        raise Refusal(o["ORIGIN"], code="BAD_ORIGIN")
    if o["ORIGIN"] == "HUMAN_GOVERNANCE":
        m = [k for k in HUMAN_MIRROR if o.get(k) is None]
        if m:
            raise Refusal(",".join(m), code="HUMAN_MIRROR_FIELD_MISSING")

def check_status_event(e: dict, context_known: bool) -> None:
    """A status event without its DECISION_CONTEXT_ID is refused (STATUS_WITHOUT_REQUIRED_CONTEXT = FAIL_CLOSED) -- except the
    risk-reducing fail-closed rule handled by fail_closed_transition."""
    missing = [k for k in STATUS_EVENT_REQUIRED if e.get(k) is None]
    if missing:
        raise Refusal(",".join(missing), code="STATUS_EVENT_FIELD_MISSING")
    if not context_known:
        raise Refusal(e["DECISION_CONTEXT_ID"], code="STATUS_WITHOUT_REQUIRED_CONTEXT")

def as_of_visible(e: dict, t: int) -> bool:
    """As-of views filter on CREATED_AT / AVAILABLE_ASOF, never retroactive EFFECTIVE_AT."""
    return e["CREATED_AT"] <= t and e["AVAILABLE_ASOF"] <= t

def fail_closed_transition(subject_kind: str, risk_reducing: bool, domain_resolvable: bool) -> dict:
    """FAIL-CLOSED SAFETY RULE: a risk-reducing quarantine/withdrawal is never refused merely because domain metadata cannot be
    resolved; the transition applies, REVIEW/CONTEXT_DOMAIN_RESOLUTION_FAILURE is raised, restoration is prohibited until the
    required governed context exists. A non-risk-reducing transition with unresolved domain is refused."""
    if not risk_reducing:
        if not domain_resolvable:
            raise Refusal(subject_kind, code="CONTEXT_DOMAIN_UNRESOLVED")
        return dict(apply=True, review=None, restoration_allowed=True)
    if domain_resolvable:
        return dict(apply=True, review=None, restoration_allowed=True)
    return dict(apply=True, review="CONTEXT_DOMAIN_RESOLUTION_FAILURE", restoration_allowed=False)
