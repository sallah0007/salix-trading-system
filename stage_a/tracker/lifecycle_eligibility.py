"""R42: historical eligibility / present trust computed over the ACTUAL `LifecycleFramework` journal (the authoritative append-only ledger) and a lagging DERIVED INDEX, instead of caller booleans (MLCore native p313/p319/p361; A07 NL0030/0034/0250/0258/0262/0266).
  * required_through_seq  = the authoritative journal HEAD now (never supplied);
  * resolved_through_seq  = what the derived index/resolver has actually resolved (`index_resolved_through()`, e.g. the E05 meta head of a lifecycle source) - a lagging index is therefore DETECTED;
  * slice closure         = derived from the ledger's own ordering: positions up to an event time T are CLOSED only when the authoritative ledger already holds an entry with event_time STRICTLY AFTER T (event times are monotonic in sequence, enforced); a head whose latest entry is at or before T may still receive entries at T, so the slice is NOT closed. This is a generic rule; the source-owner's own closure producer, if different, is a held input.
  * `time_of(record)` (the event time of a lifecycle record) and `epoch_of(record)` are SUPPLIED: the lifecycle journal records no per-record time or epoch, so none is fabricated (epoch None = unavailable historical binding, explicit).
No lifecycle graph or state names are defined: eligible/revoked states are caller-supplied; there is no input for the currently authoritative generation, so no current-generation fallback can be expressed."""
import json
from ..errors import Refusal
from tracker_component.journal_port import GENESIS_HEAD
from . import historical_eligibility as H
def ledger_entries(journal, time_of, epoch_of=None):
    if not callable(time_of): raise Refusal("time_of", code="LIFECYCLE_ELIG_TIME_SOURCE_UNBOUND")
    head = journal.head(); recs = journal.read_from(1) if head != GENESIS_HEAD else []; out = []
    for r in recs:
        b = json.loads(r.body_json); t = time_of(r)
        if type(t) is not int or t < 0: raise Refusal(str(r.seq), code="LIFECYCLE_ELIG_EVENT_TIME_NOT_SUPPLIED")
        out.append(H.Entry(None if epoch_of is None else epoch_of(r), r.seq, t, b["subject"], b["to"]))
    return head.seq, out
def reconstruct(journal, *, time_of, event_time, index_resolved_through, eligible_states, epoch_of=None):
    head_seq, es = ledger_entries(journal, time_of, epoch_of)
    if not callable(index_resolved_through): raise Refusal("index", code="LIFECYCLE_ELIG_INDEX_UNBOUND")
    closed = max((e.event_time for e in es), default=-1)
    later = any(e.event_time > event_time for e in es)
    return H.reconstruct_eligibility(es, event_time=event_time, required_through_seq=head_seq, resolved_through_seq=index_resolved_through(), slice_closed_through_time=event_time if later else min(closed, event_time - 1) if event_time > 0 else 0, eligible_states=eligible_states) if es else H.Decision(H.MISSED, "", ("NO_LEDGER_ENTRIES",), 0)
def trust(journal, generation_id, *, time_of, index_resolved_through, revoked_states):
    head_seq, es = ledger_entries(journal, time_of); return H.present_trust(es, generation_id, required_through_seq=head_seq, resolved_through_seq=index_resolved_through(), revoked_states=revoked_states)
