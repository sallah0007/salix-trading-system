"""Per-CAS-attempt acceptance time PROTOCOL (Build Plan E01-M1; R52 finding E03-F1). Source duties: CANONICAL_ACCEPTED_AT is minted for the SPECIFIC CAS attempt and becomes authoritative only if that CAS succeeds; a failed CAS never reuses the old
transition object or its accepted_at (a retry is a freshly constructed transition: fresh time, fresh hash, fresh key); UNKNOWN_COMMIT is resolved by rereading the authoritative HEAD/chain (no blind retry).
This module is ONLY the generic protocol over a SUPPLIED time port. It does not provide a clock, does not choose units/domain/precision, does not reuse the identity/report clock (a `clocks.Clock` is refused), and
is not wired into `tracker/pipeline` (whose CANONICAL_ACCEPTED body has no time field; adding one changes the candidate body schema and needs a version bump: held). QUALIFIED use is held until an admitted trusted clock and a time-aware atomic
primitive exist: with no port the protocol refuses. A time value is an opaque non-negative int here; nothing about its meaning is asserted."""
from ..errors import Refusal, UnknownCommit
from ..clocks import Clock
from tracker_component.journal_port import HeadMismatch
from tracker_component.canonical import canonical_json

TIME_KEY = "canonical_accepted_at"     # candidate name (schema/objects.canonical_accepted_at); a candidate, versioned by whoever wires it

def port_ok(port):
    if port is None: raise Refusal("attempt-time port", code="ATTEMPT_TIME_PORT_UNBOUND_HELD")
    if isinstance(port, Clock): raise Refusal(type(port).__name__, code="ATTEMPT_TIME_PORT_IS_IDENTITY_CLOCK")
    if not callable(getattr(port, "mint", None)): raise Refusal("attempt-time port", code="ATTEMPT_TIME_PORT_INVALID")

def _t(v):
    if type(v) is not int or v < 0 or v > 2**63 - 1: raise Refusal(repr(v), code="ATTEMPT_TIME_INVALID")          # must be encodable by the typed schema's timestamp_utc (i64, schema/encoding.py); no unit/domain is inferred
    return v

def mint_fresh(port, seen):
    """Mint ONE attempt time and require it to be DISTINCT from every time already minted for earlier attempts of this call. Freshness beyond distinctness (ordering, units, precision, clock domain) is NOT decided here: it is an explicit obligation of the supplied port/owner (held). A port that repeats a value is refused, not silently accepted."""
    t = _t(port.mint())
    if t in seen: raise Refusal(repr(t), code="ATTEMPT_TIME_NOT_FRESH")
    seen.add(t); return t

def find_attempt(journal, head, kind, body_json):
    """Resolve an UnknownCommit for the SPECIFIC attempted transition: the record that sits at the position this attempt targeted (seq = head.seq+1, prev_hash = head.hash) with exactly this kind and body. Not a chain-wide kind+body match. Returns the record or None (not committed AT THAT POSITION). A byte-identical transition from a rival at the same position is indistinguishable from ours and is the same idempotent fact."""
    for r in journal.read_from(head.seq + 1):
        if r.seq == head.seq + 1 and r.prev_hash == head.hash and r.kind == kind and r.body_json == body_json: return r
    return None

def append_with_attempt_time(journal, kind, build_body, port, *, max_attempts=8):
    """Returns (record, accepted_at). Each attempt: read HEAD, mint a FRESH (distinct) time, build the body FROM that time, append. HeadMismatch -> next attempt re-mints (old body/time discarded).
    UnknownCommit -> reread; if THAT attempt (position + body) landed, return that SAME record and time (no re-mint); if not landed at that position, mint anew. StaleFence propagates."""
    port_ok(port); seen = set()
    for _ in range(max_attempts):
        head = journal.head(); t = mint_fresh(port, seen); body = build_body(t)
        if not isinstance(body, dict) or body.get(TIME_KEY) != t: raise Refusal(kind, code="ATTEMPT_BODY_DOES_NOT_CARRY_ITS_TIME")
        try:
            return journal.append(head, kind, body), t
        except HeadMismatch:
            continue
        except UnknownCommit:
            r = find_attempt(journal, head, kind, canonical_json(body))
            if r is not None: return r, t
            continue
    raise Refusal(kind, code="ATTEMPT_TIME_RETRY_EXHAUSTED")

def accepted_time_of(record):
    """The accepted time a record carries, or None for a LEGACY record that has none. Never fabricates a historical time."""
    import json
    b = json.loads(record.body_json); v = b.get(TIME_KEY)
    return v if type(v) is int and v >= 0 else None
