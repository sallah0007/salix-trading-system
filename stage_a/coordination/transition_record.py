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

# R52 (E03-F1): CANDIDATE optional field. `canonical_accepted_at` is present ONLY when a supplied attempt-time port minted it for that exact CAS attempt (coordination/attempt_time.py). Records without it (all history) stay valid and their acceptance time is UNKNOWN/held: never back-filled.
OPTIONAL = {CANONICAL_ACCEPTED: ("canonical_accepted_at",)}
# R35: R34 added `materialization_hash` to CANONICAL_ACCEPTED. Accepted journals written before R34 lack it and MUST stay readable: they are classified LEGACY (the accepted-materialization binding is ABSENT, never
# fabricated, never back-filled into a committed record) and are HELD for maintenance by the verifier. NEW writes (default) still require the field; only READING a committed record accepts the legacy shape.
LEGACY_ACCEPTED_OMITS = ("materialization_hash",)
def body_generation(kind: str, body: dict) -> str:
    """CURRENT, or LEGACY_NO_MATERIALIZATION_BINDING for a committed CANONICAL_ACCEPTED body that is exactly the pre-R34 shape. Anything else is validated normally by the caller."""
    return "LEGACY_NO_MATERIALIZATION_BINDING" if kind == CANONICAL_ACCEPTED and isinstance(body, dict) and "materialization_hash" not in body else "CURRENT"

def validate_body(kind: str, body: dict, *, legacy_read: bool = False):
    if kind not in KINDS:
        raise Refusal(kind, code="UNKNOWN_TRANSITION_KIND")
    req = _REQUIRED[kind]
    if legacy_read and kind == CANONICAL_ACCEPTED and body_generation(kind, body) != "CURRENT": req = tuple(k for k in req if k not in LEGACY_ACCEPTED_OMITS)
    missing = [k for k in req if k not in body or body[k] in (None, "")]
    if missing:
        raise Refusal("%s missing %s" % (kind, missing), code="TRANSITION_BODY_INCOMPLETE")
    opt = OPTIONAL.get(kind, ())
    if "canonical_accepted_at" in opt and "canonical_accepted_at" in body:
        v = body["canonical_accepted_at"]
        if type(v) is not int or v < 0 or v > 2**63 - 1: raise Refusal("%s canonical_accepted_at" % kind, code="TRANSITION_ACCEPTED_AT_INVALID")
    extra = set(body) - set(req) - set(opt)
    if extra:
        raise Refusal("%s unexpected %s" % (kind, sorted(extra)), code="TRANSITION_BODY_UNEXPECTED_FIELDS")

def check_transition(prior_kind: Optional[str], kind: str):
    if kind not in _NEXT.get(prior_kind, set()):
        raise Refusal("%s -> %s" % (prior_kind, kind), code="ILLEGAL_TRANSITION")
