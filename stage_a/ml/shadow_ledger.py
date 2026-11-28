"""ML shadow-live evidence ledger (R45, corrected R46). Source: MLCore shadow-live evidence contract (cited by role/paragraph, not copied):
 p325 the EXPECTED count is the governed calendar/schedule's logical triggers, counted ONCE, BEFORE any disposition; p326 each expected trigger has ONE terminal
 disposition {PUBLISHED, MODEL_ABSTAINED, LIFECYCLE_FENCED}; p327 a lifecycle fence beats a PROVISIONAL abstention; p328 retries do not count; p329 coverage = published / EXPECTED.
SOURCE-OWNED, UNBOUND here (held, not invented): the schedule/calendar and its cadence, the logical-event key field list, the prediction-event-id derivation, any coverage threshold or
sufficiency verdict, window cadence. The expected triggers are SUPPLIED by the caller (`expect`); with none supplied coverage is HELD (None).
Coverage is an exact (published, expected) pair. An expected trigger with no disposition (missing / in progress) stays in the denominator. Nothing here advances any gate.
NO CALLER integrates this yet: the model-publication path that would call it does not exist in this repository (named residual)."""
from ..errors import Refusal

OUTCOMES = ("PUBLISHED", "MODEL_ABSTAINED", "LIFECYCLE_FENCED")

class ShadowLedger:
    def __init__(self):
        self._expected = {}      # (logical_key, trigger_id) -> None until a terminal exists, else (prediction_event_id, outcome, detail)
        self._provisional = {}   # (logical_key, trigger_id) -> prediction_event_id of a PROVISIONAL abstention (not terminal)
        self._ids = {}           # prediction_event_id -> (logical_key, trigger_id, kind)  kind in OUTCOMES|"PROVISIONAL"
        self._sealed = set()

    @staticmethod
    def _str(**kw):
        for k, v in kw.items():
            if not isinstance(v, str) or not v: raise Refusal(k, code="SHADOW_FIELD_INVALID")

    def expect(self, logical_key, trigger_id):
        """Register one governed logical trigger BEFORE any disposition (idempotent; never counted twice). Refused after the key is sealed (no retroactive denominators)."""
        self._str(logical_key=logical_key, trigger_id=trigger_id)
        if logical_key in self._sealed and (logical_key, trigger_id) not in self._expected: raise Refusal(logical_key, code="SHADOW_RETROACTIVE_BACKFILL_PROHIBITED")
        self._expected.setdefault((logical_key, trigger_id), None)

    def _slot(self, logical_key, trigger_id, prediction_event_id):
        self._str(prediction_event_id=prediction_event_id, logical_key=logical_key, trigger_id=trigger_id)
        if (logical_key, trigger_id) not in self._expected: raise Refusal("%s/%s" % (logical_key, trigger_id), code="SHADOW_TRIGGER_NOT_EXPECTED_HELD_UNBOUND")

    def provisional_abstain(self, logical_key, trigger_id, prediction_event_id):
        """A PROVISIONAL abstention is not a terminal disposition; it is replaced by a lifecycle fence or confirmed as MODEL_ABSTAINED (p327)."""
        self._slot(logical_key, trigger_id, prediction_event_id)
        if self._expected[(logical_key, trigger_id)] is not None: raise Refusal(trigger_id, code="SHADOW_TERMINAL_ALREADY_RECORDED")
        if logical_key in self._sealed: raise Refusal(logical_key, code="SHADOW_RETROACTIVE_BACKFILL_PROHIBITED")
        old = self._provisional.get((logical_key, trigger_id))
        if old is not None and old != prediction_event_id: raise Refusal(trigger_id, code="SHADOW_EVENT_ID_CONFLICT")
        self._provisional[(logical_key, trigger_id)] = prediction_event_id; self._ids[prediction_event_id] = (logical_key, trigger_id, "PROVISIONAL")
        return "PROVISIONAL"

    def record(self, logical_key, trigger_id, prediction_event_id, outcome, detail=""):
        """The ONE terminal disposition of an expected trigger. Exact repeat (a retry) = no-op, never a second count; a different outcome/id for a finalized trigger is refused (immutable)."""
        self._slot(logical_key, trigger_id, prediction_event_id)
        if outcome not in OUTCOMES: raise Refusal(str(outcome), code="SHADOW_OUTCOME_NOT_ADMITTED")
        slot = (logical_key, trigger_id); cur = self._expected[slot]; row = (prediction_event_id, outcome, detail)
        if cur is not None:
            if cur == row: return "DUPLICATE_NOOP"
            raise Refusal(trigger_id, code="SHADOW_EVENT_ID_CONFLICT" if cur[0] != prediction_event_id else "SHADOW_TERMINAL_IMMUTABLE")
        prev = self._ids.get(prediction_event_id)
        if prev is not None and prev[:2] != slot: raise Refusal(prediction_event_id, code="SHADOW_EVENT_ID_CONFLICT")
        if logical_key in self._sealed: raise Refusal(logical_key, code="SHADOW_RETROACTIVE_BACKFILL_PROHIBITED")
        prov = self._provisional.get(slot)
        if prov is not None and prov != prediction_event_id and outcome != "LIFECYCLE_FENCED": raise Refusal(trigger_id, code="SHADOW_EVENT_ID_CONFLICT")
        # a PROVISIONAL abstention may be finalized as MODEL_ABSTAINED or superseded by LIFECYCLE_FENCED (fence wins); PUBLISHED after a provisional abstention is not defined by source: refused
        if prov is not None and outcome == "PUBLISHED": raise Refusal(trigger_id, code="SHADOW_PUBLISHED_AFTER_PROVISIONAL_ABSTENTION_NOT_DEFINED")
        self._expected[slot] = row; self._provisional.pop(slot, None); self._ids[prediction_event_id] = (logical_key, trigger_id, outcome)
        return "RECORDED"

    def seal(self, logical_key): self._sealed.add(logical_key)

    def counters(self, logical_key):
        c = {o: 0 for o in OUTCOMES}; c["EXPECTED"] = 0; c["MISSING_OR_IN_PROGRESS"] = 0
        for (k, _), v in self._expected.items():
            if k != logical_key: continue
            c["EXPECTED"] += 1
            if v is None: c["MISSING_OR_IN_PROGRESS"] += 1
            else: c[v[1]] += 1
        return c

    def coverage(self, logical_key):
        """(published, EXPECTED) or None when no trigger was supplied (HELD: the schedule is source-owned and unbound). Missing and fenced opportunities stay in the denominator."""
        c = self.counters(logical_key); return None if c["EXPECTED"] == 0 else (c["PUBLISHED"], c["EXPECTED"])

    def missing(self, logical_key): return sorted(t for (k, t), v in self._expected.items() if k == logical_key and v is None)
    def fenced(self, logical_key): return sorted(t for (k, t), v in self._expected.items() if k == logical_key and v is not None and v[1] == "LIFECYCLE_FENCED")
