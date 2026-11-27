"""Principal capability lookups. DOCUMENTARY ROLE LOOKUPS ONLY: not authentication, not a grant, not an appointment.

Two tables, two scopes, never mixed:
 * E06 / capabilities(): Build Plan E-06 ten principals (production / outside the isolated replica). Unchanged.
 * REPLICA_ROLES / replica_capabilities(): R7 SECTIONS 3 role refinement for the ISOLATED REPLICA ONLY. Source status (Matrix 1RRZD4i...,
   'R7 SOURCE-SELECTION CHANGE SET 01'): R7 sections 1-6 are CURRENT as a conditional DESIGN source for the isolated replica; Binding V1 controls
   outside those intersections; E-06 production/outside-replica is untouched. Design-source selection is NOT operational reliance: no actual
   principal, trust anchor, grant, provider, host, namespace or operation instance is appointed or certified. (The earlier 'pending effectiveness'
   wording is the dated approval-record snapshot and is historical for this selection.)
Origin/commit split (R7 s1/s3): the replica refines E-06 tracker-acceptor into acceptance-origin (produces authorized acceptance evidence; cannot
write HEAD or materialize) and replica-commit-service (exclusive governed replica HEAD/transition writer; no originating-role, verdict, semantic
identity or materialization power). tracker-acceptor therefore has NO replica lookup: its HEAD-write right is not inherited by acceptance-origin.
R7 s3 also lists further proposed principals (order issuer, claim origin, reservation, lifecycle, quarantine, config, expiry, review, grant/security,
rollback/replacement, audit) but gives them NO names; none is encoded here (names would be invented)."""
from typing import Iterable
from ..errors import Refusal

WRITE_CANDIDATE, WRITE_PENDING_CANDIDATE, WRITE_VERIFICATION_EVIDENCE, WRITE_HEAD_TRANSITION = (
    "WRITE_CANDIDATE", "WRITE_PENDING_CANDIDATE", "WRITE_VERIFICATION_EVIDENCE", "WRITE_HEAD_TRANSITION")
WRITE_STATUS_EVENT, WRITE_CONTEXT, WRITE_GATEWAY_BINDING, WRITE_HEALTH_EVIDENCE = (
    "WRITE_STATUS_EVENT", "WRITE_CONTEXT", "WRITE_GATEWAY_BINDING", "WRITE_HEALTH_EVIDENCE")
WRITE_QUEUE_METADATA, WRITE_REPLAY_READ_MODEL, READ_CANONICAL = "WRITE_QUEUE_METADATA", "WRITE_REPLAY_READ_MODEL", "READ_CANONICAL"
WRITE_ACCEPTANCE_EVIDENCE = "WRITE_ACCEPTANCE_EVIDENCE"   # Tracker-side label for R7 s3 'produces authorized acceptance evidence' (label is not source text)

# Capabilities exactly as E-06 states them. Nothing is inferred; a capability not listed is denied.
E06 = {
    "composer-builder": frozenset({WRITE_CANDIDATE}),
    "composer-refitter": frozenset({WRITE_CANDIDATE}),
    "tracker-materializer": frozenset({WRITE_PENDING_CANDIDATE}),
    "tracker-verifier": frozenset({READ_CANONICAL, WRITE_VERIFICATION_EVIDENCE}),
    "tracker-acceptor": frozenset({WRITE_HEAD_TRANSITION, WRITE_STATUS_EVENT}),
    "context-writer": frozenset({WRITE_CONTEXT}),
    "gateway-writer": frozenset({WRITE_GATEWAY_BINDING}),
    "health-writer": frozenset({WRITE_HEALTH_EVIDENCE}),
    "scheduler": frozenset({WRITE_QUEUE_METADATA}),
    "replay-reader": frozenset({READ_CANONICAL, WRITE_REPLAY_READ_MODEL}),
}
# R7 section 3 replica-only role names. They are NOT E-06 principals, so the E-06 lookup refuses them by name (use replica_capabilities).
R7_REPLICA_ONLY = frozenset({"acceptance-origin", "replica-commit-service"})
_REPLICA_CARRIED = frozenset(E06) - {"tracker-acceptor"}      # R7 s3 table maps these eight to the existing E-06 principals unchanged
REPLICA_ROLES = {**{k: E06[k] for k in _REPLICA_CARRIED},
                 "acceptance-origin": frozenset({WRITE_ACCEPTANCE_EVIDENCE}),
                 "replica-commit-service": frozenset({WRITE_HEAD_TRANSITION})}
# WRITE_STATUS_EVENT (E-06 tracker-acceptor) is deliberately assigned to NEITHER replica role: R7 is silent on who writes status events after the split.
DESIGN_LOOKUP_NOT_AUTHORIZATION = True
# Pairs a single holder must never combine (E-06 'may not merge prohibited principals'; materializer/acceptor and
# builder/acceptor separations are stated in E-06 least-privilege text). Pair list is the minimal stated set, not an invention of policy.
PROHIBITED_MERGES = (("tracker-acceptor", "tracker-materializer"), ("tracker-acceptor", "composer-builder"),
                     ("tracker-acceptor", "composer-refitter"), ("tracker-acceptor", "tracker-verifier"))

def capabilities(principal: str) -> frozenset:
    if principal in R7_REPLICA_ONLY:
        raise Refusal(principal, code="REPLICA_ONLY_ROLE_NOT_IN_E06")
    if principal not in E06:
        raise Refusal(str(principal), code="UNKNOWN_PRINCIPAL")
    return E06[principal]

def replica_capabilities(principal: str) -> frozenset:
    """R7 s3 isolated-replica DESIGN lookup. tracker-acceptor is refused: the replica splits it, and a rename must not carry HEAD-write rights."""
    if principal == "tracker-acceptor":
        raise Refusal(principal, code="REPLICA_ACCEPTOR_SPLIT_REQUIRED")
    if principal not in REPLICA_ROLES:
        raise Refusal(str(principal), code="UNKNOWN_PRINCIPAL")
    return REPLICA_ROLES[principal]

REPLICA_PROHIBITED_MERGES = tuple(sorted({
    ("acceptance-origin", "replica-commit-service"),                              # R7 s1/s3 origin/commit split
    *[(r, o) for r in ("acceptance-origin", "replica-commit-service")             # E-06 acceptor separations carried to BOTH refinements
      for o in ("tracker-materializer", "composer-builder", "composer-refitter", "tracker-verifier")]}))

def replica_check_no_prohibited_merge(held: Iterable[str]) -> None:
    held = set(held)
    for p in held: replica_capabilities(p)
    for a, b in REPLICA_PROHIBITED_MERGES:
        if a in held and b in held:
            raise Refusal("%s + %s" % (a, b), code="PROHIBITED_PRINCIPAL_MERGE")

def authorize(principal: str, capability: str) -> None:
    if capability not in capabilities(principal):
        raise Refusal("%s lacks %s" % (principal, capability), code="CAPABILITY_NOT_GRANTED")

def check_no_prohibited_merge(held: Iterable[str]) -> None:
    held = set(held)
    for p in held: capabilities(p)                          # unknown / R7 names refuse first
    for a, b in PROHIBITED_MERGES:
        if a in held and b in held:
            raise Refusal("%s + %s" % (a, b), code="PROHIBITED_PRINCIPAL_MERGE")

# ---- D2 evidence shape (R09). A role lookup above is NOT authentication and NOT a grant. -------------------------------------------
LOOKUP_ONLY_NOT_AUTHENTICATION = True
GRANT_EVIDENCE_FIELDS = ("principal_id", "role", "grant_generation", "bootstrap_trust_anchor_ref", "namespace_id", "operation_scope",
                         "issued_by_record_ref", "validity/supersession")      # PROPOSED field set (R7 s3 'authority evidence'); not a source-defined schema

def check_grant_evidence_shape(rec: dict, scope: str = "E06") -> dict:
    """Shape check of a candidate grant-evidence record. It appoints nobody and verifies nothing (no signature/anchor check exists):
    passing means only that the record is complete enough to be submitted to the governed record for appointment."""
    if not isinstance(rec, dict):
        raise Refusal(type(rec).__name__, code="GRANT_EVIDENCE_NOT_A_RECORD")
    for f in GRANT_EVIDENCE_FIELDS:
        v = rec.get(f)
        if type(v) is not str or not v.strip():
            raise Refusal(f, code="GRANT_EVIDENCE_FIELD_MISSING")
    if set(rec) - set(GRANT_EVIDENCE_FIELDS):
        raise Refusal("extra", code="GRANT_EVIDENCE_UNKNOWN_FIELD")
    if scope == "E06": capabilities(rec["role"])               # role must be an E-06 principal (replica-only names refused)
    elif scope == "REPLICA": replica_capabilities(rec["role"]) # role must have an R7 s3 replica design lookup
    else: raise Refusal(str(scope), code="GRANT_EVIDENCE_SCOPE_UNKNOWN")
    return rec
