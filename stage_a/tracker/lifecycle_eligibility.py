"""R43 (supersedes R42's rules): historical eligibility / present trust over the ACTUAL `LifecycleFramework` journal and a lagging DERIVED INDEX, on ONE coherent read basis.
  * entries and the read basis come from ONE chain-verified `read_from(1)`: the basis is that read's own last (seq, record_hash), never a separate `head()` callback; the authoritative head is read AGAIN afterwards and becomes `required_through_seq`, so an append during the read is a visible staleness (the index cannot have resolved through it), not a silent mix of two heads;
  * the derived index supplies its BASIS as (seq, hash) (e.g. the E05 meta row of a `ledger_source`); a basis whose hash is not the owning chain's record hash at that seq is on another history and counts as resolved through 0 (reason INDEX_BASIS_NOT_ON_THE_OWNING_CHAIN); a bare sequence number is not accepted;
  * slice CLOSURE has no governed producer in the sources. It is an explicit SOURCE-OWNED SLOT `closure_rule(entries, event_time, head_seq) -> closed_through_time | None`; without it the decision is HELD (`HISTORICAL_SLICE_CLOSURE_PRODUCER_UNBOUND_HELD`). `LATER_ENTRY_CANDIDATE_CLOSURE` is a GENERIC CANDIDATE rule (closed only when the ledger already holds an entry strictly after T), offered for rehearsal and NOT a governed rule: a caller must pass it explicitly;
  * the claimed closure endpoint must equal the resolved basis and the entries must be exactly positions 1..basis (missing tail / gap / empty => MISSED, trust => UNKNOWN_STALE);
  * no lifecycle graph or state names are defined; epoch/time are supplied callbacks (the lifecycle journal records neither; none is fabricated); there is no input for a currently authoritative generation, so no current-generation fallback can be expressed."""
import json
from ..errors import Refusal
from tracker_component.journal_port import GENESIS_HEAD, GENESIS_HASH
from . import historical_eligibility as H
CLOSURE_HELD = "HISTORICAL_SLICE_CLOSURE_PRODUCER_UNBOUND_HELD"
def LATER_ENTRY_CANDIDATE_CLOSURE(entries, event_time, head_seq):
    """GENERIC CANDIDATE, not governed: T is closed only when an entry with event_time strictly after T is already in the ledger."""
    return event_time if any(e.event_time > event_time for e in entries) else None
def _read(journal, time_of, epoch_of=None):
    if not callable(time_of): raise Refusal("time_of", code="LIFECYCLE_ELIG_TIME_SOURCE_UNBOUND")
    recs = journal.read_from(1); out = []                                  # chain-verified from the head recorded by THIS read
    for r in recs:
        b = json.loads(r.body_json); t = time_of(r)
        if type(t) is not int or t < 0: raise Refusal(str(r.seq), code="LIFECYCLE_ELIG_EVENT_TIME_NOT_SUPPLIED")
        out.append(H.Entry(None if epoch_of is None else epoch_of(r), r.seq, t, b["subject"], b["to"]))
    basis = (recs[-1].seq, recs[-1].record_hash) if recs else (0, GENESIS_HASH)
    now = journal.head(); now = (now.seq, now.hash)                         # read AFTER the records: an append during the read makes required > basis
    if now[0] < basis[0]: raise Refusal(str(now), code="LIFECYCLE_ELIG_READ_BASIS_INCOHERENT")
    if now[0] == basis[0] and now[1] != basis[1]: raise Refusal(str(now), code="LIFECYCLE_ELIG_READ_BASIS_INCOHERENT")
    return out, basis, now
def ledger_entries(journal, time_of, epoch_of=None):
    out, basis, now = _read(journal, time_of, epoch_of); return now[0], out
def _index(index_basis, basis, recs):
    if not callable(index_basis): raise Refusal("index", code="LIFECYCLE_ELIG_INDEX_UNBOUND")
    b = index_basis()
    if not (isinstance(b, tuple) and len(b) == 2 and type(b[0]) is int and b[0] >= 0): raise Refusal("index basis", code="LIFECYCLE_ELIG_INDEX_BASIS_MUST_BE_SEQ_AND_HASH")
    if b[0] == 0: return 0, None
    if b[0] > basis[0] or recs[b[0] - 1][1] != b[1]: return 0, "INDEX_BASIS_NOT_ON_THE_OWNING_CHAIN"
    return b[0], None
def _hashes(journal):
    return [(r.seq, r.record_hash) for r in journal.read_from(1)]
def reconstruct(journal, *, time_of, event_time, index_basis, eligible_states, closure_rule=None, epoch_of=None, epoch_bound=None):
    es, basis, now = _read(journal, time_of, epoch_of)
    if not es: return H.Decision(H.MISSED, "", ("NO_LEDGER_ENTRIES",), 0)
    resolved, bad = _index(index_basis, basis, _hashes(journal))
    if bad: return H.Decision(H.MISSED, "", (bad,), 0)
    if closure_rule is None: return H.Decision(H.MISSED, "", (CLOSURE_HELD,), resolved)
    closed = closure_rule(es, event_time, now[0])
    if closed is None: return H.Decision(H.MISSED, "", (("CURRENT_READ_FRESHNESS_FAIL",) if resolved < now[0] else ()) + ("HISTORICAL_SLICE_COMPLETENESS_FAIL:NOT_CLOSED_THROUGH_EVENT_TIME",), resolved)
    if type(closed) is not int or closed < 0: raise Refusal("closure", code="LIFECYCLE_ELIG_CLOSURE_INVALID")
    return H.reconstruct_eligibility(es, event_time=event_time, required_through_seq=now[0], resolved_through_seq=resolved, slice_closed_through_time=closed, slice_closed_at_seq=basis[0], eligible_states=eligible_states, epoch_bound=epoch_bound)
def trust(journal, generation_id, *, time_of, index_basis, revoked_states, epoch_of=None):
    es, basis, now = _read(journal, time_of, epoch_of); resolved, bad = _index(index_basis, basis, _hashes(journal))
    if bad: return "UNKNOWN_STALE"
    return H.present_trust(es, generation_id, required_through_seq=now[0], resolved_through_seq=resolved, revoked_states=revoked_states)
