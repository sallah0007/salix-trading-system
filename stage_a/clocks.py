"""Identity timestamps and causal/finalisation timestamps are different things and are typed apart."""
from dataclasses import dataclass
from datetime import datetime, timezone
from .errors import Refusal

IDENTITY = "IDENTITY"
CAUSAL = "CAUSAL"

@dataclass(frozen=True)
class Stamp:
    kind: str
    iso: str
    def __post_init__(self):
        if self.kind not in (IDENTITY, CAUSAL):
            raise Refusal(self.kind, code="UNKNOWN_STAMP_KIND")
        try:
            dt = datetime.fromisoformat(self.iso)
        except (TypeError, ValueError):
            raise Refusal(str(self.iso), code="BAD_TIMESTAMP")
        if dt.tzinfo is None:
            raise Refusal(self.iso, code="NAIVE_TIMESTAMP")

def require_kind(stamp: Stamp, kind: str) -> Stamp:
    if not isinstance(stamp, Stamp) or stamp.kind != kind:
        raise Refusal("expected %s stamp" % kind, code="STAMP_KIND_CONFLATION")
    return stamp

class Clock:
    def now_iso(self) -> str:
        raise NotImplementedError

class SystemClock(Clock):
    def now_iso(self):
        return datetime.now(timezone.utc).isoformat()

class FixedClock(Clock):
    def __init__(self, iso="2026-01-01T00:00:00+00:00"):
        Stamp(IDENTITY, iso)
        self._iso = iso
    def now_iso(self):
        return self._iso
