"""AVAILABLE_ASOF resolution. Two query modes that must never be confused (Q21-Q23):
  AS_KNOWN : only transitions accepted at or before asof_seq (what the system knew then)
  EVENTUAL : every accepted transition (what is now known to have been true)
Technical latest object/row is never authority; only the verified accepted chain."""
from dataclasses import dataclass
from typing import Optional, Tuple
from .errors import Refusal
from .replay import replay

AS_KNOWN = "AS_KNOWN"
EVENTUAL = "EVENTUAL"

@dataclass(frozen=True)
class Resolution:
    mode: str
    asof_seq: Optional[int]
    available_version: Optional[str]
    statuses: Tuple[Tuple[str, str], ...]

def resolve_asof(namespace: str, records, *, mode: str, asof_seq: Optional[int] = None) -> Resolution:
    if mode not in (AS_KNOWN, EVENTUAL):
        raise Refusal(str(mode), code="UNKNOWN_QUERY_MODE")
    if mode == AS_KNOWN:
        if not isinstance(asof_seq, int) or isinstance(asof_seq, bool) or asof_seq < 0:
            raise Refusal("AS_KNOWN needs integer asof_seq", code="ASOF_REQUIRED")
        records = [r for r in records if r.seq <= asof_seq]
    elif asof_seq is not None:
        raise Refusal("EVENTUAL takes no asof_seq", code="ASOF_FORBIDDEN_FOR_EVENTUAL")
    states = replay(namespace, list(records))
    avail = [s for s in states.values() if s.status == "PUBLISHABLE"]
    avail.sort(key=lambda s: s.publishable_seq)
    return Resolution(mode, asof_seq, avail[-1].version if avail else None,
                      tuple(sorted((s.version, s.status) for s in states.values())))
