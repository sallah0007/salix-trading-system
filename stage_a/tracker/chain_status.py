"""Chain / materialization status authority (Annex §IX; Q22). Tracker-owned. Pure state machine over appended events.
Visibility at a consumer fence is HALF-OPEN: an event is visible iff available_asof < fence (G1: equality is excluded)."""
from dataclasses import dataclass
from typing import Optional
from ..errors import Refusal

CURRENT, CATCHING_UP, DEGRADED, HALTED, SUPERSEDED = "CURRENT", "CATCHING_UP", "DEGRADED_NOT_CURRENT", "HALTED", "SUPERSEDED"
ALL = (CURRENT, CATCHING_UP, DEGRADED, HALTED, SUPERSEDED)

@dataclass(frozen=True)
class StatusFact:
    mv: tuple                      # (feature_id, feature_version, instrument_id, timeframe_id, materialization_version)
    sequence: int
    status: str
    available_asof: int
    correction_marked: bool
    tracker_designated: bool = False   # explicit Tracker designation (required for CATCHING_UP -> CURRENT)

class ChainStatusAuthority:
    def __init__(self):
        self._events = {}
    def append(self, f: StatusFact):
        if f.status not in ALL:
            raise Refusal(f.status, code="UNKNOWN_STATUS")
        ev = self._events.setdefault(f.mv, [])
        prev = ev[-1] if ev else None
        if prev is not None:
            if f.sequence <= prev.sequence:
                raise Refusal("sequence must strictly increase", code="SEQUENCE_NOT_INCREASING")
            if f.available_asof < prev.available_asof:
                raise Refusal("available_asof must be non-decreasing", code="ASOF_DECREASED")
            if prev.status == HALTED:
                raise Refusal("HALTED is terminal for that MV", code="HALTED_TERMINAL")
            if prev.correction_marked and not f.correction_marked:
                raise Refusal("CORRECTION_MARKED is false->true only", code="CORRECTION_UNMARKED")
            if prev.status == CATCHING_UP and f.status == CURRENT and not f.tracker_designated:
                raise Refusal("CATCHING_UP->CURRENT needs explicit Tracker designation", code="NO_TRACKER_DESIGNATION")
        if f.correction_marked and f.status == CURRENT:
            raise Refusal("CURRENT is forever invalid once correction-marked", code="CURRENT_AFTER_CORRECTION")
        if f.tracker_designated and not (prev and prev.status == CATCHING_UP and f.status == CURRENT):
            raise Refusal("designation only applies to CATCHING_UP->CURRENT", code="BAD_DESIGNATION")
        ev.append(f)
        return f
    def status_at(self, mv, fence: int) -> Optional[StatusFact]:
        vis = [e for e in self._events.get(mv, []) if e.available_asof < fence]
        return vis[-1] if vis else None
