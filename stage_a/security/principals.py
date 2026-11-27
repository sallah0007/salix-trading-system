"""E-06 principal capability table (Build Plan E-06, OPERATIVE) and the R7 proposed refinement (NOT OPERATIVE).

This module APPOINTS NOBODY and holds no credentials, grants or trust anchors (D2/D1: those are evidence + Owner/Manager actions).
It is a Tracker-owned fail-closed interface: capability lookup for a named principal, and a no-prohibited-merge check on a bundle.
Source: Build Plan E-06 ten principals + least-privilege rules; R7 section 3 refinement is approved DESIGN text, not operative
(Composer Binding V1 and E-06 stay operative until a separately verified successor switch), so R7 principals are refused here."""
from typing import Iterable
from ..errors import Refusal

WRITE_CANDIDATE, WRITE_PENDING_CANDIDATE, WRITE_VERIFICATION_EVIDENCE, WRITE_HEAD_TRANSITION = (
    "WRITE_CANDIDATE", "WRITE_PENDING_CANDIDATE", "WRITE_VERIFICATION_EVIDENCE", "WRITE_HEAD_TRANSITION")
WRITE_STATUS_EVENT, WRITE_CONTEXT, WRITE_GATEWAY_BINDING, WRITE_HEALTH_EVIDENCE = (
    "WRITE_STATUS_EVENT", "WRITE_CONTEXT", "WRITE_GATEWAY_BINDING", "WRITE_HEALTH_EVIDENCE")
WRITE_QUEUE_METADATA, WRITE_REPLAY_READ_MODEL, READ_CANONICAL = "WRITE_QUEUE_METADATA", "WRITE_REPLAY_READ_MODEL", "READ_CANONICAL"

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
# R7 section 3 proposed names (replica only). Listed ONLY so they can be refused by name, never granted.
R7_PROPOSED_NOT_OPERATIVE = frozenset({"acceptance-origin", "replica-commit-service"})
# Pairs a single holder must never combine (E-06 'may not merge prohibited principals'; materializer/acceptor and
# builder/acceptor separations are stated in E-06 least-privilege text). Pair list is the minimal stated set, not an invention of policy.
PROHIBITED_MERGES = (("tracker-acceptor", "tracker-materializer"), ("tracker-acceptor", "composer-builder"),
                     ("tracker-acceptor", "composer-refitter"), ("tracker-acceptor", "tracker-verifier"))

def capabilities(principal: str) -> frozenset:
    if principal in R7_PROPOSED_NOT_OPERATIVE:
        raise Refusal(principal, code="R7_PRINCIPAL_NOT_OPERATIVE")
    if principal not in E06:
        raise Refusal(str(principal), code="UNKNOWN_PRINCIPAL")
    return E06[principal]

def authorize(principal: str, capability: str) -> None:
    if capability not in capabilities(principal):
        raise Refusal("%s lacks %s" % (principal, capability), code="CAPABILITY_NOT_GRANTED")

def check_no_prohibited_merge(held: Iterable[str]) -> None:
    held = set(held)
    for p in held: capabilities(p)                          # unknown / R7 names refuse first
    for a, b in PROHIBITED_MERGES:
        if a in held and b in held:
            raise Refusal("%s + %s" % (a, b), code="PROHIBITED_PRINCIPAL_MERGE")
