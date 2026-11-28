"""R50: the SHADOW PUBLICATION CALLER (generic candidate) that drives `ShadowLedger` from a model-publication path (the named R45/R46 residual: no caller existed). Source: MLCore shadow-live evidence contract p325-329 (cited by role/paragraph, not copied).
What this owns: the ORDER of effects for one expected logical trigger, over four SUPPLIED source slots, each HELD (None => refuse; nothing is defaulted):
  schedule   (iterable of (logical_key, trigger_id))   the governed calendar/schedule's logical triggers - source-owned, cadence/key field list undefined here
  fence      (callable (logical_key, trigger_id) -> bool)  the lifecycle-fence probe; with no probe a trigger can never be PUBLISHED or ABSTAINED (we cannot claim "not fenced")
  event_id   (callable (logical_key, trigger_id) -> str)   the prediction-event-id derivation - source-owned, not invented
  model/sink (callables)  model(trigger) -> ("PUBLISH", payload) | ("ABSTAIN", reason); sink(event_id, payload) commits the publication (commit BEFORE the ledger records PUBLISHED)
Sequence per trigger: terminal already recorded => return it, call NOTHING (retries never count, never re-publish); fence probed BEFORE the model, a fence => LIFECYCLE_FENCED; model raises => no terminal (the trigger stays in the denominator as missing/in-progress, a retry may succeed);
ABSTAIN => provisional abstention, fence re-probed, then MODEL_ABSTAINED or (fence beats provisional, p327) LIFECYCLE_FENCED; PUBLISH => fence probed AGAIN after compute and before the sink, sink commits, THEN PUBLISHED is recorded; sink raises => no PUBLISHED.
Counts come only from the ledger (coverage = published / EXPECTED, missing and fenced stay in the denominator). No coverage threshold, sufficiency verdict or gate is defined or advanced here."""
from ..errors import Refusal
from .shadow_ledger import ShadowLedger


class ShadowPublisher:
    def __init__(self, ledger, *, schedule=None, fence=None, event_id=None, model=None, sink=None):
        if not isinstance(ledger, ShadowLedger): raise Refusal("ledger", code="SHADOW_PUBLISHER_LEDGER_INVALID")
        for n, f in (("fence", fence), ("event_id", event_id), ("model", model), ("sink", sink)):
            if f is not None and not callable(f): raise Refusal(n, code="SHADOW_PUBLISHER_SLOT_INVALID")
        self._l, self._sched, self._fence, self._eid, self._model, self._sink = ledger, schedule, fence, event_id, model, sink
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
    def trigger(self, logical_key, trigger_id):
        self._need(); slot = (logical_key, trigger_id)
        cur = self._l._expected.get(slot, "ABSENT")
        if cur == "ABSENT": raise Refusal("%s/%s" % slot, code="SHADOW_TRIGGER_NOT_EXPECTED_HELD_UNBOUND")
        if cur is not None: return cur[1]                                                                 # terminal exists: a retry calls neither model nor sink
        eid = self._eid(logical_key, trigger_id)
        if self._fenced(logical_key, trigger_id): self._l.record(logical_key, trigger_id, eid, "LIFECYCLE_FENCED"); return "LIFECYCLE_FENCED"
        verdict = self._model(slot)
        if not (isinstance(verdict, tuple) and len(verdict) == 2 and verdict[0] in ("PUBLISH", "ABSTAIN")): raise Refusal("model", code="SHADOW_MODEL_VERDICT_MALFORMED")
        if verdict[0] == "ABSTAIN":
            self._l.provisional_abstain(logical_key, trigger_id, eid)
            out = "LIFECYCLE_FENCED" if self._fenced(logical_key, trigger_id) else "MODEL_ABSTAINED"
            self._l.record(logical_key, trigger_id, eid, out, str(verdict[1])); return out
        if self._fenced(logical_key, trigger_id): self._l.record(logical_key, trigger_id, eid, "LIFECYCLE_FENCED"); return "LIFECYCLE_FENCED"          # fence after compute, before the commit
        self._sink(eid, verdict[1])                                                                        # commit FIRST; an exception here records nothing
        self._l.record(logical_key, trigger_id, eid, "PUBLISHED"); return "PUBLISHED"
