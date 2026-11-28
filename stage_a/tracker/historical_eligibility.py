"""R41: generic candidate oracle for MLCore (native paragraphs) p313/p319/p361 and A07 NL0030/0034/0250/0258/0262/0266.
  * Historical eligibility of a generation for a past event may be reconstructed ONLY when BOTH `CURRENT_READ_FRESHNESS` (the lifecycle resolver has resolved through at least the ledger position the read requires) AND `HISTORICAL_SLICE_COMPLETENESS` (the ledger positions covering the event time are contiguous and closed through the event time) pass; otherwise the event is MISSED_QUARANTINED. There is NO input for the currently authoritative generation, so a current-generation fallback cannot be expressed.
  * Present-day trust of a historical contributor is UNKNOWN_STALE (never TRUSTED) when the resolver lags the required position (the artificial-index-lag negative).
This module defines no lifecycle graph, no eligible/revoked state names, no closure producer and no deployed resolver: `eligible_states` / `revoked_states` and the closure assertion are SUPPLIED by the source owner; it only enforces the two-part gate. Entries are (epoch or None when no per-record epoch is recorded - never fabricated, seq, event_time, generation_id, state) from an authoritative ledger reader."""
from dataclasses import dataclass
from ..errors import Refusal
READY, MISSED = "ELIGIBLE", "MISSED_QUARANTINED"
@dataclass(frozen=True)
class Entry:
    epoch: object; seq: int; event_time: int; generation_id: str; state: str
@dataclass(frozen=True)
class Decision:
    status: str; generation_id: str; reasons: tuple; resolved_through: int
    def __bool__(self): raise TypeError("Decision has no truthiness; compare .status")
def _int(x): return type(x) is int and x >= 0
def _entries(entries):
    if not (isinstance(entries, (list, tuple)) and all(isinstance(e, Entry) and (e.epoch is None or _int(e.epoch)) and _int(e.seq) and e.seq >= 1 and _int(e.event_time) and isinstance(e.generation_id, str) and e.generation_id and isinstance(e.state, str) and e.state for e in entries)): raise Refusal("entries", code="HIST_ELIG_ENTRIES_INVALID")
    out = sorted(entries, key=lambda e: e.seq)
    if len({e.seq for e in out}) != len(out) or any((a.epoch is not None and b.epoch is not None and a.epoch > b.epoch) or a.event_time > b.event_time for a, b in zip(out, out[1:])): raise Refusal("entries", code="HIST_ELIG_ENTRIES_NOT_MONOTONIC")
    return out
def _complete_through(es, resolved_through_seq):
    """R43: the supplied entries must be EXACTLY positions 1..resolved_through_seq (no gap, no missing tail, none empty while the basis is non-zero). A contiguous PREFIX shorter than the claimed endpoint is NOT complete."""
    return [e.seq for e in es if e.seq <= resolved_through_seq] == list(range(1, resolved_through_seq + 1))
def reconstruct_eligibility(entries, *, event_time, required_through_seq, resolved_through_seq, slice_closed_through_time, slice_closed_at_seq, eligible_states, epoch_bound=None):
    """`slice_closed_at_seq` is the ledger position at which the closure assertion was made; it must EQUAL the resolved basis (a closure claimed at another endpoint proves nothing about this one). Who produces the closure assertion is a source-owner slot (see lifecycle_eligibility); here it is only checked against the entries actually supplied.
    `epoch_bound` (optional): when given, every entry must record an epoch <= it; an unrecorded epoch (None) cannot be proven and is held."""
    if not all(_int(x) for x in (event_time, required_through_seq, resolved_through_seq, slice_closed_through_time, slice_closed_at_seq)) or not (isinstance(eligible_states, frozenset) and eligible_states) or not (epoch_bound is None or _int(epoch_bound)): raise Refusal("inputs", code="HIST_ELIG_INPUT_INVALID")
    es = _entries(entries); why = []
    if resolved_through_seq < required_through_seq: why.append("CURRENT_READ_FRESHNESS_FAIL")
    if slice_closed_through_time < event_time: why.append("HISTORICAL_SLICE_COMPLETENESS_FAIL:NOT_CLOSED_THROUGH_EVENT_TIME")
    if slice_closed_at_seq != resolved_through_seq: why.append("HISTORICAL_SLICE_COMPLETENESS_FAIL:CLOSURE_ENDPOINT_NOT_THE_RESOLVED_BASIS")
    if not _complete_through(es, resolved_through_seq): why.append("HISTORICAL_SLICE_COMPLETENESS_FAIL:SEQUENCE_GAP_OR_MISSING_TAIL")
    upto = [e for e in es if e.seq <= resolved_through_seq]
    if epoch_bound is not None:
        if any(e.epoch is None for e in upto): why.append("EPOCH_NOT_RECORDED_HELD")
        elif any(e.epoch > epoch_bound for e in upto): why.append("EPOCH_AFTER_BASIS")
    if why: return Decision(MISSED, "", tuple(why), resolved_through_seq)
    latest = {}
    for e in upto:
        if e.event_time <= event_time: latest[e.generation_id] = e.state
    ok = sorted(g for g, s in latest.items() if s in eligible_states)
    if len(ok) != 1: return Decision(MISSED, "", ("NO_ELIGIBLE_GENERATION" if not ok else "AMBIGUOUS_ELIGIBLE_GENERATIONS",), resolved_through_seq)
    return Decision(READY, ok[0], (), resolved_through_seq)
def present_trust(entries, generation_id, *, required_through_seq, resolved_through_seq, revoked_states):
    """-> TRUSTED | REVOKED | UNKNOWN_STALE. A lagging resolver never reports TRUSTED."""
    if not all(_int(x) for x in (required_through_seq, resolved_through_seq)) or not (isinstance(revoked_states, frozenset) and revoked_states) or not isinstance(generation_id, str) or not generation_id: raise Refusal("inputs", code="HIST_ELIG_INPUT_INVALID")
    all_es = _entries(entries); es = [e for e in all_es if e.generation_id == generation_id and e.seq <= resolved_through_seq]
    if resolved_through_seq < required_through_seq: return "UNKNOWN_STALE"
    if not _complete_through(all_es, resolved_through_seq): return "UNKNOWN_STALE"             # R43: a missing tail can hide a revocation; completeness through the resolved endpoint is part of trust
    if not es: return "UNKNOWN_STALE"
    return "REVOKED" if any(e.state in revoked_states for e in es) else "TRUSTED"
