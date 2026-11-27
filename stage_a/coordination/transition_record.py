"""Feature lifecycle transitions as accepted-journal records, with the state machine that governs them.
A technical 'latest' is never authority; authority is the accepted chain."""
from dataclasses import dataclass
from typing import Optional
from ..errors import Refusal

CANONICAL_ACCEPTED = "CANONICAL_ACCEPTED"
PUBLISHABLE = "PUBLISHABLE"
WITHDRAWN = "WITHDRAWN"
KINDS = (CANONICAL_ACCEPTED, PUBLISHABLE, WITHDRAWN)

# per-version state machine: None -> ACCEPTED -> PUBLISHABLE -> WITHDRAWN ; ACCEPTED -> WITHDRAWN
_NEXT = {None: {CANONICAL_ACCEPTED}, CANONICAL_ACCEPTED: {PUBLISHABLE, WITHDRAWN},
         PUBLISHABLE: {WITHDRAWN}, WITHDRAWN: set()}

_REQUIRED = {
    CANONICAL_ACCEPTED: ("feature_key", "feature_version", "manifest_hash", "graph_hash", "program_hash",
                         "attempt_id", "verification_hash", "certification_hash", "claim_witness",
                         "safe_intake_report_hash", "materialization_hash"),
    PUBLISHABLE: ("feature_key", "feature_version", "accepted_seq", "accepted_hash", "verification_hash"),
    WITHDRAWN: ("feature_key", "feature_version", "reason"),
}

def validate_body(kind: str, body: dict):
    if kind not in KINDS:
        raise Refusal(kind, code="UNKNOWN_TRANSITION_KIND")
    req = _REQUIRED[kind]
    missing = [k for k in req if k not in body or body[k] in (None, "")]
    if missing:
        raise Refusal("%s missing %s" % (kind, missing), code="TRANSITION_BODY_INCOMPLETE")
    extra = set(body) - set(req)
    if extra:
        raise Refusal("%s unexpected %s" % (kind, sorted(extra)), code="TRANSITION_BODY_UNEXPECTED_FIELDS")

def check_transition(prior_kind: Optional[str], kind: str):
    if kind not in _NEXT.get(prior_kind, set()):
        raise Refusal("%s -> %s" % (prior_kind, kind), code="ILLEGAL_TRANSITION")
