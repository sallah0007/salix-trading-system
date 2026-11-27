"""CANDIDATE D25 protocol (Tracker lifecycle subjects only) — PROPOSED, NOT ADOPTED. Source-owner adoption is required before this is
cited as a safety/liveness claim. It selects no retry timer, no new status enum and no cross-component authority.

A quarantine/withdrawal decided under epoch E_req is re-resolved against CURRENT identity/state/epoch. Exactly three outcomes:
  ALREADY_FENCED      the target is already effectively fail-closed under the current epoch -> record, no mutation
  ACTION_REQUIRED     the target is still eligible -> only a NEW authorized action bound to the CURRENT epoch/state may fence it
  UNRESOLVED          ownership/state unknown (cannot be read) -> explicit unresolved outcome, never completion
A stale-epoch mutation is always refused; REFUSE + REVIEW alone is never reported as completed protection while eligible."""
from dataclasses import dataclass
from typing import Optional
from ..errors import Refusal

ALREADY_FENCED, ACTION_REQUIRED, UNRESOLVED = "ALREADY_FENCED", "ACTION_REQUIRED", "UNRESOLVED"
FENCED_STATES = {"HALTED", "WITHDRAWN", "SUPERSEDED", "QUARANTINED", "REVOKED"}   # states that are effectively non-eligible

@dataclass(frozen=True)
class Resolution:
    outcome: str
    current_epoch: Optional[int]
    current_state: Optional[str]
    protection_effective: bool

def re_resolve(request_epoch: int, current_epoch: Optional[int], current_state: Optional[str]) -> Resolution:
    if current_epoch is None or current_state is None:
        return Resolution(UNRESOLVED, current_epoch, current_state, False)
    if current_state in FENCED_STATES:
        return Resolution(ALREADY_FENCED, current_epoch, current_state, True)
    return Resolution(ACTION_REQUIRED, current_epoch, current_state, False)

def apply(request_epoch: int, current_epoch: int, expected_state: str, current_state: str):
    """A mutation may only proceed bound to the CURRENT epoch and the state it was decided against."""
    if request_epoch != current_epoch:
        raise Refusal("%d != %d" % (request_epoch, current_epoch), code="STALE_EPOCH_MUTATION")
    if expected_state != current_state:
        raise Refusal("%s != %s" % (expected_state, current_state), code="STATE_CHANGED")
    return True
