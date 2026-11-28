"""R50: the SHADOW PUBLICATION CALLER (generic candidate) that drives `ShadowLedger` from a model-publication path (the named R45/R46 residual: no caller existed). Source: MLCore shadow-live evidence contract p325-329 (cited by role/paragraph, not copied).
What this owns: the ORDER of effects for one expected logical trigger, over four SUPPLIED source slots, each HELD (None => refuse; nothing is defaulted):
  schedule   (iterable of (logical_key, trigger_id))   the governed calendar/schedule's logical triggers - source-owned, cadence/key field list undefined here
  fence      (callable (logical_key, trigger_id) -> bool)  the lifecycle-fence probe; with no probe a trigger can never be PUBLISHED or ABSTAINED (we cannot claim "not fenced")
  event_id   (callable (logical_key, trigger_id) -> str)   the prediction-event-id derivation - source-owned, not invented
  model (callable) model(trigger) -> ("PUBLISH", payload) | ("ABSTAIN", reason); sink: an IDEMPOTENT publication interface `commit(event_id, payload)` + `readback(event_id) -> payload|None` (R51: a bare callable is refused; `AtomicRecordSink` adapts the existing owning `tracker.atomic_publication.AtomicRecordStore`, MLCore p323/p324 immutable prospective record + idempotent single record + different-payload integrity)
Sequence per trigger: terminal already recorded => return it, call NOTHING (retries never count, never re-publish); fence probed BEFORE the model, a fence => LIFECYCLE_FENCED; model raises => no terminal (the trigger stays in the denominator as missing/in-progress, a retry may succeed);
ABSTAIN => provisional abstention, fence re-probed, then MODEL_ABSTAINED or (fence beats provisional, p327) LIFECYCLE_FENCED; PUBLISH => fence probed AGAIN after compute and before the sink, sink commits, THEN PUBLISHED is recorded; sink raises => no PUBLISHED.
Counts come only from the ledger (coverage = published / EXPECTED, missing and fenced stay in the denominator). No coverage threshold, sufficiency verdict or gate is defined or advanced here."""
from ..errors import Refusal
from tracker_component.canonical import canonical_json, sha256_hex
from .shadow_ledger import ShadowLedger


# R51 ordering: EVERY load-bearing ledger constraint (expected slot, sealed key, global event id, provisional) is pre-validated with the ledger's own read-only `check_record` BEFORE any side effect; the sink is read back BEFORE a (re)publication (an already-committed event is RECORDED, never re-committed) and AFTER an exception from `commit`:
# absent => the exception stands (retry allowed); present with the same payload => recovered and recorded; present with a different payload => refuse SHADOW_SINK_DIFFERENT_PAYLOAD; readback itself failing => the slot stays UNKNOWN (SHADOW_PUBLICATION_OUTCOME_UNKNOWN) and neither model nor sink is called again until it resolves.

def _h(payload):
    try: return sha256_hex(canonical_json(payload))
    except Exception: raise Refusal("payload", code="SHADOW_PAYLOAD_NOT_CANONICAL")


class AtomicRecordSink:
    """Adapter from the existing owning atomic publication store (`tracker.atomic_publication.AtomicRecordStore`: body at a content address, visible only through ONE put_if_absent pointer under the idempotency key = the event id)."""
    def __init__(self, atomic_store): self._a = atomic_store
    def commit(self, event_id, payload): return self._a.publish(event_id, {"event_id": event_id, "payload": payload})
    def readback(self, event_id):
        r = self._a.read(event_id); return None if r is None else r["payload"]


class ShadowPublisher:
    def __init__(self, ledger, *, schedule=None, fence=None, event_id=None, model=None, sink=None):
        if not isinstance(ledger, ShadowLedger): raise Refusal("ledger", code="SHADOW_PUBLISHER_LEDGER_INVALID")
        for n, f in (("fence", fence), ("event_id", event_id), ("model", model)):
            if f is not None and not callable(f): raise Refusal(n, code="SHADOW_PUBLISHER_SLOT_INVALID")
        if sink is not None and not (callable(getattr(sink, "commit", None)) and callable(getattr(sink, "readback", None))): raise Refusal("sink", code="SHADOW_SINK_NOT_IDEMPOTENT_INTERFACE")
        self._l, self._sched, self._fence, self._eid, self._model, self._sink = ledger, schedule, fence, event_id, model, sink; self._pending = {}
    def declare_schedule(self):
        if self._sched is None: raise Refusal("schedule", code="SHADOW_SCHEDULE_HELD")
        items = list(self._sched)
        if not all(isinstance(x, tuple) and len(x) == 2 and all(isinstance(y, str) and y for y in x) for x in items): raise Refusal("schedule", code="SHADOW_SCHEDULE_MALFORMED")
        for k, t in items: self._l.expect(k, t)                    # BEFORE any disposition; idempotent
        return len(items)
    def _need(self):
        for n, f in (("fence", self._fence), ("event_id", self._eid), ("model", self._model), ("sink", self._sink)):
            if f is None: raise Refusal(n, code="SHADOW_%s_HELD" % n.upper())
    def _fenced(self, k, t):
        v = self._fence(k, t)
        if type(v) is not bool: raise Refusal("fence", code="SHADOW_FENCE_PROBE_NOT_BOOLEAN")           # an unreadable probe is not "not fenced"
        return v
    def _readback(self, eid):
        try: return ("OK", self._sink.readback(eid))
        except Exception: return ("UNREADABLE", None)
    def trigger(self, logical_key, trigger_id):
        self._need(); slot = (logical_key, trigger_id)
        cur = self._l._expected.get(slot, "ABSENT")
        if cur == "ABSENT": raise Refusal("%s/%s" % slot, code="SHADOW_TRIGGER_NOT_EXPECTED_HELD_UNBOUND")
        if cur is not None: return cur[1]                                                                 # terminal exists: a retry calls neither model nor sink
        eid = self._eid(logical_key, trigger_id)
        st, got = self._readback(eid)                                                                      # R52: HISTORICAL publication is resolved BEFORE the current fence is consulted: a committed event (earlier unknown outcome, restart, fresh ledger) is recorded PUBLISHED and never re-decided from today's fence (the fence is current lifecycle state, annotated separately, not a rewrite of what was durably published, p323/324/327)
        if st == "UNREADABLE": raise Refusal(eid, code="SHADOW_PUBLICATION_OUTCOME_UNKNOWN")           # an unresolved receipt is neither "published" nor "never published": it cannot be FENCED either
        if got is not None:
            pend = self._pending.get(slot)
            if pend is not None and pend[1] != _h(got): raise Refusal(eid, code="SHADOW_SINK_DIFFERENT_PAYLOAD")
            self._l.check_record(logical_key, trigger_id, eid, "PUBLISHED"); self._l.record(logical_key, trigger_id, eid, "PUBLISHED"); self._pending.pop(slot, None); return "PUBLISHED"
        if self._fenced(logical_key, trigger_id): self._l.record(logical_key, trigger_id, eid, "LIFECYCLE_FENCED"); return "LIFECYCLE_FENCED"          # genuine fence BEFORE any first commit: no model, no sink write
        verdict = self._model(slot)
        if not (isinstance(verdict, tuple) and len(verdict) == 2 and verdict[0] in ("PUBLISH", "ABSTAIN")): raise Refusal("model", code="SHADOW_MODEL_VERDICT_MALFORMED")
        if verdict[0] == "ABSTAIN":
            self._l.provisional_abstain(logical_key, trigger_id, eid)
            out = "LIFECYCLE_FENCED" if self._fenced(logical_key, trigger_id) else "MODEL_ABSTAINED"
            self._l.record(logical_key, trigger_id, eid, out, str(verdict[1])); return out
        if self._fenced(logical_key, trigger_id): self._l.record(logical_key, trigger_id, eid, "LIFECYCLE_FENCED"); return "LIFECYCLE_FENCED"          # fence after compute, before the commit
        self._l.check_record(logical_key, trigger_id, eid, "PUBLISHED")                                    # R51: every ledger constraint is known BEFORE the side effect (sealed key, global event id, provisional, terminal)
        h = _h(verdict[1]); self._pending[slot] = (eid, h)
        try: self._sink.commit(eid, verdict[1])                                                            # commit FIRST; PUBLISHED is recorded only after it is known to have landed
        except Exception:
            st, got = self._readback(eid)
            if st == "UNREADABLE": raise Refusal(eid, code="SHADOW_PUBLICATION_OUTCOME_UNKNOWN")           # slot stays UNKNOWN (pending kept)
            if got is None: self._pending.pop(slot, None); raise                                          # confirmed absent: the original failure stands, a retry may succeed
            if _h(got) != h: raise Refusal(eid, code="SHADOW_SINK_DIFFERENT_PAYLOAD")
        self._l.record(logical_key, trigger_id, eid, "PUBLISHED"); self._pending.pop(slot, None); return "PUBLISHED"
