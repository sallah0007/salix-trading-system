"""ML shadow-live evidence ledger (R45). Source: MLCore shadow-live evidence contract (read R45; cited by role, not copied): PREDICTION_EVENT_ID
idempotency; outcome in {PUBLISHED, MODEL_ABSTAINED, LIFECYCLE_FENCED}; per-logical-event counters; coverage rate; fencing misses stay visible;
retroactive backfill prohibited.
Not decided here (named, not invented): any coverage THRESHOLD, any sufficiency verdict, window cadence, the logical-event key's field list. Coverage is
returned as an exact (numerator, denominator) pair; an empty denominator is None, never 1 and never 0. Nothing here advances any gate."""
from ..errors import Refusal

OUTCOMES = ("PUBLISHED", "MODEL_ABSTAINED", "LIFECYCLE_FENCED")

class ShadowLedger:
    def __init__(self):
        self._rows = {}          # prediction_event_id -> (logical_key, outcome, detail)
        self._sealed = set()     # logical keys closed to new events

    def record(self, prediction_event_id, logical_key, outcome, detail=""):
        for k, v in (("prediction_event_id", prediction_event_id), ("logical_key", logical_key)):
            if not isinstance(v, str) or not v:
                raise Refusal(k, code="SHADOW_FIELD_INVALID")
        if outcome not in OUTCOMES:
            raise Refusal(str(outcome), code="SHADOW_OUTCOME_NOT_ADMITTED")
        row = (logical_key, outcome, detail)
        old = self._rows.get(prediction_event_id)
        if old is not None:
            if old != row:
                raise Refusal(prediction_event_id, code="SHADOW_EVENT_ID_CONFLICT")   # same id, different content: never overwritten
            return "DUPLICATE_NOOP"
        if logical_key in self._sealed:
            raise Refusal(logical_key, code="SHADOW_RETROACTIVE_BACKFILL_PROHIBITED")
        self._rows[prediction_event_id] = row
        return "RECORDED"

    def seal(self, logical_key):
        self._sealed.add(logical_key)

    def counters(self, logical_key):
        c = {o: 0 for o in OUTCOMES}
        for k, o, _ in self._rows.values():
            if k == logical_key:
                c[o] += 1
        return c

    def coverage(self, logical_key):
        """(published, total) or None when no event exists. Fenced events are in the denominator: a fencing miss lowers coverage visibly."""
        c = self.counters(logical_key); n = sum(c.values())
        return None if n == 0 else (c["PUBLISHED"], n)

    def fenced(self, logical_key):
        return sorted(i for i, (k, o, _) in self._rows.items() if k == logical_key and o == "LIFECYCLE_FENCED")
