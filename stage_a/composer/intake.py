"""Composer V9 s7A (TRACKER-FIRST GOVERNED INTAKE, COMMON PROTECTIVE GATES, APPLICABILITY ROUTING) + s8 order bindings: REQUEST_DISPOSITION = PROCEED | REVIEW_REQUIRED | FAIL_CLOSED, FIELD_APPLICABILITY DERIVED from REQUEST_CLASS and
TARGET_CONSUMER only (never from REQUESTER_TYPE, never requester-declared; a requester-asserted NOT_APPLICABLE is disregarded and noted). Source-present behaviour only.
Inputs that are SUPPLIED, not performed here (no registry/archive/survivor-chain/near-match engine exists in this repo; each is a lookup RESULT with a ref, labelled unadmitted): registry lookup, archive/quarantine/rejected/retired lookup BY
IDENTITY ONLY, canonical-survivor-chain traversal, near-match review (NO CLAIM), active/pending lookup, the candidate identity (IDENTITY_KEY composition is not defined here), and the requester-identity resolution (REQUESTER_ID must resolve to a registered
identity - no registry exists, so only a non-empty governed id is checked). Which consumer owner decides REVIEW_REQUIRED vs FAIL_CLOSED for a missing CONSUMER_LOCAL field is source-owned elsewhere: REVIEW_REQUIRED is used, never PROCEED.
An evaluation is NOT an order: only TrackerCore.issue_order (journaled) issues one."""
from dataclasses import dataclass
from ..errors import Refusal
from .request_record import check_request_record, REQUEST_CLASSES, TARGET_CONSUMERS

PROCEED, REVIEW_REQUIRED, FAIL_CLOSED = "PROCEED", "REVIEW_REQUIRED", "FAIL_CLOSED"
COMMON_FIELDS_ORDER = ("REQUESTED_AT", "IDEA_ORIGIN", "IDEA_BASIS", "EXPECTED_DELIVERY_CONTRACT", "CANDIDATE_IDENTITY")
COMMON_LOOKUPS = ("REGISTRY_LOOKUP", "ARCHIVE_LOOKUP_BY_IDENTITY", "SURVIVOR_CHAIN_TRAVERSAL", "NEAR_MATCH_REVIEW_NO_CLAIM", "ACTIVE_PENDING_REQUEST_LOOKUP")
CONSUMER_LOCAL_ORDER_FIELDS = ("CAUSAL_BOUNDARY_DECISION_T", "SCOPE", "TEMPORAL_EVIDENCE_CONTRACT", "VINTAGE_MODE", "CAUSAL_FEATURE_AVAILABILITY", "ALLOWED_INPUTS", "FORBIDDEN_INPUTS")
FW_ML_ADOPTION_FIELDS = ("PACKAGE_LOCK", "FRESHNESS", "ASSEMBLY_COMPLETENESS", "LIVE_T_EXPIRY", "REPLAY_INTERVAL", "STATE_AT_T", "STREAM_POLICY", "SLOT_STATUS", "DEDUP",
                         "TRAIN_VALIDATION_HOLDOUT", "HOLDOUT_EXPOSURE", "LEAKAGE_CONTROLS", "TARGET_LABEL", "HORIZON", "MODEL_FAMILY", "SEEDS", "DATASET_IDENTITIES", "LABEL_SET_IDENTITIES")   # binding-stage (s19/s33): never required, never satisfied by an order

@dataclass(frozen=True)
class IntakeDecision:
    disposition: str; reasons: tuple; field_applicability: dict; stage: str; order_authority: bool = False

def _ok_text(v): return isinstance(v, str) and bool(v.strip())

def derive_applicability(rec: dict) -> dict:
    """FIELD_APPLICABILITY from REQUEST_CLASS and TARGET_CONSUMER ONLY. UNKNOWN consumer => FW and ML consumer-local fields NOT_APPLICABLE."""
    tc = rec.get("TARGET_CONSUMER"); cl = rec.get("REQUEST_CLASS")
    if cl not in REQUEST_CLASSES or tc not in TARGET_CONSUMERS: raise Refusal("class/consumer", code="INTAKE_APPLICABILITY_INPUT_INVALID")
    local = "CONSUMER_LOCAL_REQUIRED"
    return {"COMMON": "COMMON_REQUIRED", "FW_LOCAL": local if tc in ("FORWARD_WALK", "BOTH") else "NOT_APPLICABLE", "ML_LOCAL": local if tc in ("MACHINE_LEARNING", "BOTH") else "NOT_APPLICABLE",
            "ADOPTION_GOVERNANCE": "NOT_APPLICABLE"}              # adoption governance is required at BINDING stage by the consumer's owner; an order never carries it

def evaluate_intake(rec, stage: str, lookups: dict = None) -> IntakeDecision:
    reasons = []; fail = False; review = False
    try: base = check_request_record(rec, stage)
    except Refusal as e: return IntakeDecision(FAIL_CLOSED, (e.code,), {}, stage)
    if base == "REVIEW_REQUIRED": review = True; reasons.append("TARGET_CONSUMER_UNKNOWN_AT_ORDER")
    asserted = sorted(k for k in rec if "APPLICABILITY" in str(k).upper())
    if asserted: reasons.append("REQUESTER_ASSERTED_APPLICABILITY_DISREGARDED:" + ",".join(asserted))        # derived, never declared
    app = derive_applicability(rec)
    lookups = lookups or {}
    if stage == "ORDER":
        if not (type(rec.get("REQUESTED_AT")) is int and rec["REQUESTED_AT"] >= 0): fail = True; reasons.append("COMMON_REQUIRED_MISSING:REQUESTED_AT")
        for f in COMMON_FIELDS_ORDER[1:]:
            if not _ok_text(rec.get(f)): fail = True; reasons.append("COMMON_REQUIRED_MISSING:" + f)
        for l in COMMON_LOOKUPS:
            v = lookups.get(l)
            if not (isinstance(v, dict) and v.get("state") == "DONE" and _ok_text(v.get("ref"))): fail = True; reasons.append("COMMON_GATE_MISSING:" + l)
        if rec.get("OUTCOME_INFORMATION_ACCESS") == "PERMITTED_UNDER_DECLARED_FITTING_CONTRACT" and not _ok_text(rec.get("RESEARCH_FAMILY_REFERENCE")): fail = True; reasons.append("COMMON_REQUIRED_MISSING:RESEARCH_FAMILY_REFERENCE")
        for side in ("FW_LOCAL", "ML_LOCAL"):
            if app[side] == "CONSUMER_LOCAL_REQUIRED":
                for f in CONSUMER_LOCAL_ORDER_FIELDS:
                    if not _ok_text(rec.get(side + ":" + f)) and not _ok_text(rec.get(f)): review = True; reasons.append("CONSUMER_LOCAL_REQUIRED_MISSING:%s:%s" % (side, f))
        ap = lookups.get("ACTIVE_PENDING_REQUEST_LOOKUP")
        if isinstance(ap, dict) and ap.get("collision") not in (None, "NONE", "ATTACH_AS_PROVENANCE"): review = True; reasons.append("REQUEST_COLLISION_NEEDS_REVIEW")
    disp = FAIL_CLOSED if fail else REVIEW_REQUIRED if review else PROCEED
    return IntakeDecision(disp, tuple(sorted(set(reasons))), app, stage)
