"""Map a COMMITTED lifecycle journal record (coordination.transition_record kinds) to a Decision Context V4 A1 SUBJECT_STATUS_EVENT.
Sources: Decision Context V4 (Drive 1dwGRh2EOxzhQGwV6x6TS4K5FFTu3_TJaES4R4BpW-PQ) A1, H; R7 sections 2-3; coordination/transition_record.py.
No status principal is appointed or invented. Only a record that was read back from the journal (reachable from HEAD) is mapped; nothing here writes.
DERIVED from the committed record: STATUS_EVENT_ID and EVENT_HASH (= record_hash, the immutable identity), SUBJECT_ID (feature_key), SUBJECT_VERSION_OR_HASH
(feature_version), NEW_STATE (the committed kind), PRIOR_STATE (the previous committed kind of the same subject, when there is one).
EXACT RESIDUAL MISMATCH (A1 fields the lifecycle journal body does NOT carry; they must come from the authority boundary's validated origin evidence, are
never defaulted, and a conflict with a derived value is refused): SUBJECT_TYPE; CREATED_AT; AVAILABLE_ASOF; EFFECTIVE_AT; MACHINE_REASON_CODE;
MACHINE_REASON_CODE_VERSION; DECISION_CONTEXT_ID; AUTHORITY_STATE; RELATED_EVIDENCE_REFS; and PRIOR_STATE for the first transition (the journal has no
'before' state; the source gives no initial-state value). Vocabulary mismatches (not reconciled by any source read): lifecycle kinds
CANONICAL_ACCEPTED/PUBLISHABLE/WITHDRAWN vs A1/V1 state names (CURRENT, QUARANTINED, ...) vs chain-status states (CURRENT/CATCHING_UP/DEGRADED_NOT_CURRENT/HALTED/SUPERSEDED)."""
import json
from ..errors import Refusal
from ..context.decision_context import check_status_event, STATUS_EVENT_REQUIRED
from ..coordination.transition_record import KINDS

DERIVED = ("STATUS_EVENT_ID", "EVENT_HASH", "SUBJECT_ID", "SUBJECT_VERSION_OR_HASH", "NEW_STATE", "PRIOR_STATE")
FROM_BOUNDARY = ("SUBJECT_TYPE", "CREATED_AT", "AVAILABLE_ASOF", "EFFECTIVE_AT", "MACHINE_REASON_CODE", "MACHINE_REASON_CODE_VERSION",
                 "DECISION_CONTEXT_ID", "AUTHORITY_STATE", "RELATED_EVIDENCE_REFS")

def journal_to_status_event(rec, prior_kind, boundary_evidence: dict, context_known: bool) -> dict:
    if rec.kind not in KINDS:
        raise Refusal(rec.kind, code="NOT_A_LIFECYCLE_TRANSITION_KIND")
    body = json.loads(rec.body_json)
    ev = {"STATUS_EVENT_ID": rec.record_hash, "EVENT_HASH": rec.record_hash, "SUBJECT_ID": body.get("feature_key"),
          "SUBJECT_VERSION_OR_HASH": body.get("feature_version"), "NEW_STATE": rec.kind,
          "PRIOR_STATE": prior_kind if prior_kind is not None else (boundary_evidence or {}).get("PRIOR_STATE")}
    for k in FROM_BOUNDARY:
        v = (boundary_evidence or {}).get(k)
        if v is not None:
            ev[k] = v
    for k in DERIVED:
        if boundary_evidence and k in boundary_evidence and k != "PRIOR_STATE" and boundary_evidence[k] != ev[k]:
            raise Refusal(k, code="BOUNDARY_EVIDENCE_CONFLICTS_WITH_COMMITTED_RECORD")
    if prior_kind is not None and boundary_evidence and boundary_evidence.get("PRIOR_STATE") not in (None, prior_kind):
        raise Refusal("PRIOR_STATE", code="BOUNDARY_EVIDENCE_CONFLICTS_WITH_COMMITTED_RECORD")
    check_status_event(ev, context_known)              # A1 required fields present; STATUS_WITHOUT_REQUIRED_CONTEXT fails closed
    return ev
