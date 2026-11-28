"""Per-CAS-attempt acceptance time PROTOCOL (Build Plan E01-M1; R52 finding E03-F1). Source duties: CANONICAL_ACCEPTED_AT is minted for the SPECIFIC CAS attempt and becomes authoritative only if that CAS succeeds; a failed CAS never reuses the old
transition object or its accepted_at (a retry is a freshly constructed transition: fresh time, fresh hash, fresh key); UNKNOWN_COMMIT is resolved by rereading the authoritative HEAD/chain (no blind retry).
This module is ONLY the generic protocol over a SUPPLIED time port. It does not provide a clock, does not choose units/domain/precision, does not reuse the identity/report clock (a `clocks.Clock` is refused), and
is not wired into `tracker/pipeline` (whose CANONICAL_ACCEPTED body has no time field; adding one changes the candidate body schema and needs a version bump: held). QUALIFIED use is held until an admitted trusted clock and a time-aware atomic
primitive exist: with no port the protocol refuses. A time value is an opaque non-negative int here; nothing about its meaning is asserted."""
from ..errors import Refusal, UnknownCommit
from ..clocks import Clock
from tracker_component.journal_port import HeadMismatch
from tracker_component.canonical import canonical_json
from .recovery import resolve_unknown_commit, COMMITTED

TIME_KEY = "canonical_accepted_at"     # candidate name (schema/objects.canonical_accepted_at); a candidate, versioned by whoever wires it

def _port_ok(port):
    if port is None: raise Refusal("attempt-time port", code="ATTEMPT_TIME_PORT_UNBOUND_HELD")
    if isinstance(port, Clock): raise Refusal(type(port).__name__, code="ATTEMPT_TIME_PORT_IS_IDENTITY_CLOCK")
    if not callable(getattr(port, "mint", None)): raise Refusal("attempt-time port", code="ATTEMPT_TIME_PORT_INVALID")

def _t(v):
    if type(v) is not int or v < 0: raise Refusal(repr(v), code="ATTEMPT_TIME_INVALID")
    return v

def append_with_attempt_time(journal, kind, build_body, port, *, max_attempts=8):
    """Returns (record, accepted_at). Each attempt: read HEAD, mint a FRESH time from the port, build the body FROM that time, append. HeadMismatch -> next attempt re-mints (the old body/time is discarded).
    UnknownCommit -> reread the chain: if THAT attempt's exact body landed, return that SAME record and time (no re-mint, no re-evaluation); if proven not committed, mint anew. StaleFence propagates."""
    _port_ok(port)
    for _ in range(max_attempts):
        head = journal.head(); t = _t(port.mint()); body = build_body(t)
        if not isinstance(body, dict) or body.get(TIME_KEY) != t: raise Refusal(kind, code="ATTEMPT_BODY_DOES_NOT_CARRY_ITS_TIME")
        try:
            return journal.append(head, kind, body), t
        except HeadMismatch:
            continue
        except UnknownCommit:
            bj = canonical_json(body)
            if resolve_unknown_commit(journal, kind=kind, body_json=bj) == COMMITTED:
                for r in journal.read_from(1):
                    if r.kind == kind and r.body_json == bj: return r, t
            continue
    raise Refusal(kind, code="ATTEMPT_TIME_RETRY_EXHAUSTED")

def accepted_time_of(record):
    """The accepted time a record carries, or None for a LEGACY record that has none. Never fabricates a historical time."""
    import json
    b = json.loads(record.body_json); v = b.get(TIME_KEY)
    return v if type(v) is int and v >= 0 else None
