"""B02 time-family LOGIC (R24): causal/completeness invariants that do NOT need a calendar instance. The governed timeframe registry INSTANCE (M15/H1/H4 definitions), segmentation rules, DST/session calendar and
broker-time rule are source-owned and UNBOUND; nothing here defaults, derives or invents them. Every operation that would need them returns the typed UNDETERMINED_CALENDAR_UNBOUND / refuses.

What IS source-present and therefore implemented: (a) an unregistered timeframe is refused, never assumed; (b) a parent bar is COMPLETE only against an explicitly SUPPLIED segmentation (parent -> exact child ids)
and only when every listed child is present, no extra child exists, and no child is duplicated - completeness is never inferred from counts or labels; (c) cross-timeframe as-of: a parent value is visible at a
query time only when its availability is STRICTLY before it (half-open, equality excluded), i.e. a parent bar is never back-projected onto an earlier child time."""
from dataclasses import dataclass
from ..errors import Refusal

COMPLETE, INCOMPLETE, UNDETERMINED = "COMPLETE", "INCOMPLETE", "UNDETERMINED_CALENDAR_UNBOUND"
def _int(x): return isinstance(x, int) and not isinstance(x, bool)

class TimeframeRegistry:
    """Holds ONLY governed entries handed to it (empty by default: every timeframe is unknown). Entry = (timeframe name, child timeframe name or None). It never ships M15/H1/H4 as defaults."""
    def __init__(self, entries=()):
        self._e = {}
        for tf, child in entries:
            if not isinstance(tf, str) or not tf or (child is not None and not isinstance(child, str)) or tf in self._e: raise Refusal(str(tf), code="TIMEFRAME_ENTRY_INVALID")
            self._e[tf] = child
    def require(self, tf: str) -> str:
        if tf not in self._e: raise Refusal(str(tf), code="UNKNOWN_TIMEFRAME")
        return tf
    def child_of(self, tf: str):
        self.require(tf); return self._e[tf]

def parent_completeness(registry: TimeframeRegistry, parent_tf: str, parent_id: str, segmentation, observed_children) -> tuple:
    """segmentation: {parent_id: [child ids]} SUPPLIED by the governed calendar source (never derived here). Returns (state, detail)."""
    registry.require(parent_tf)
    if registry.child_of(parent_tf) is None: raise Refusal(parent_tf, code="TIMEFRAME_HAS_NO_CHILD_LEVEL")
    if not isinstance(segmentation, dict) or parent_id not in segmentation: return UNDETERMINED, "SEGMENTATION_FOR_PARENT_NOT_SUPPLIED"
    want = segmentation[parent_id]; got = list(observed_children)
    if not isinstance(want, (list, tuple)) or not want or len(set(want)) != len(want): return UNDETERMINED, "SEGMENTATION_MALFORMED"
    if len(set(got)) != len(got): raise Refusal(parent_id, code="DUPLICATE_CHILD_OBSERVATION")
    extra = sorted(set(got) - set(want))
    if extra: raise Refusal(",".join(map(str, extra)), code="CHILD_NOT_IN_PARENT_SEGMENTATION")
    missing = sorted(set(want) - set(got))
    return (INCOMPLETE, "MISSING:" + ",".join(map(str, missing))) if missing else (COMPLETE, "")

def parent_visible_asof(parent_available_asof: int, query_asof: int) -> bool:
    """No back-projection: visible iff available_asof < query_asof (equality excluded)."""
    if not _int(parent_available_asof) or not _int(query_asof) or parent_available_asof < 0 or query_asof < 0: raise Refusal("as-of", code="ASOF_MALFORMED")
    return parent_available_asof < query_asof

SELECTED, NONE_VISIBLE, MULTIPLE_CANDIDATES = "SELECTED", "NONE_VISIBLE", "MULTIPLE_CANDIDATES"
@dataclass(frozen=True)
class ParentSelection:
    state: str
    parent_id: object = None
    available_asof: object = None
    candidates: tuple = ()          # on MULTIPLE_CANDIDATES: the tied ids, sorted for display only - NOT a selection rule

def latest_visible_parent(parents, query_asof: int) -> ParentSelection:
    """parents: [(parent_id, available_asof, complete: bool)]. Latest COMPLETE parent visible strictly before query_asof. If DISTINCT parents tie on the latest availability and no governed rule chooses, the result is
    MULTIPLE_CANDIDATES (input order, registration order or id ordering never decides a single slot; no tie-break rule, K3/CASE or outcome metric is invented). The same id listed twice with the same availability
    is one candidate; the same id with two availabilities is malformed. An incomplete parent is never exposed."""
    seen = {}
    for pid, asof, complete in parents:
        if pid in seen and seen[pid][0] != asof: raise Refusal(str(pid), code="PARENT_LISTED_WITH_TWO_AVAILABILITIES")
        if pid in seen and seen[pid][1] != complete: raise Refusal(str(pid), code="PARENT_LISTED_WITH_CONFLICTING_COMPLETENESS")      # conflicting facts are held, never last-wins/order-dependent
        seen[pid] = (asof, complete)
    vis = {pid: a for pid, (a, c) in seen.items() if c is True and parent_visible_asof(a, query_asof)}
    if not vis: return ParentSelection(NONE_VISIBLE)
    top = max(vis.values()); tied = sorted((str(p) for p, a in vis.items() if a == top))
    if len(tied) > 1: return ParentSelection(MULTIPLE_CANDIDATES, None, top, tuple(tied))
    pid = [p for p, a in vis.items() if a == top][0]; return ParentSelection(SELECTED, pid, top)

# ---- R26: multi-stream snapshot with explicit PER-TIMEFRAME resolved vintage/watermark (Registry: one common query/as-of boundary + explicit per-timeframe vintage/watermark; no false simultaneity) ----
RESOLVED, UNRESOLVED = "RESOLVED", "UNRESOLVED"
@dataclass(frozen=True)
class StreamView:
    """One timeframe's candidate sealed (COMPLETE) parents, plus the vintage and currentness watermark resolved FOR THAT timeframe. Vintage/watermark values and their freshness policy are caller/source supplied (not invented)."""
    parents: tuple; vintage: str; watermark: int
@dataclass(frozen=True)
class SnapshotEntry:
    timeframe: str; selection: ParentSelection; vintage: object; watermark: object; state: str; reasons: tuple
@dataclass(frozen=True)
class SnapshotResolution:
    query_asof: int; entries: tuple; state: str      # RESOLVED only if every timeframe is uniquely selected with its own vintage and watermark; otherwise UNRESOLVED (no partial 'simultaneous' claim)
    def entry(self, tf): return next(e for e in self.entries if e.timeframe == tf)

def resolve_snapshot(registry: TimeframeRegistry, query_asof: int, streams: dict) -> SnapshotResolution:
    """Every timeframe resolves as-of the SAME query_asof (half-open, no back-projection) but keeps its OWN vintage and watermark; a scalar vintage/watermark shared across timeframes is refused. Ambiguity, absence,
    missing vintage or malformed watermark leaves that entry and the whole snapshot UNRESOLVED; nothing is picked by order and no policy is invented."""
    if not _int(query_asof) or query_asof < 0: raise Refusal("query_asof", code="ASOF_MALFORMED")
    if not isinstance(streams, dict) or not streams: raise Refusal("streams", code="SNAPSHOT_STREAMS_INVALID")
    out = []
    for tf in sorted(streams):                        # sorted for a deterministic report only: the entry content never depends on order
        registry.require(tf); v = streams[tf]
        if not isinstance(v, StreamView): raise Refusal(tf, code="SNAPSHOT_STREAM_NOT_PER_TIMEFRAME")
        sel = latest_visible_parent(list(v.parents), query_asof); why = []
        if sel.state == NONE_VISIBLE: why.append("NO_SEALED_PARENT_VISIBLE")
        if sel.state == MULTIPLE_CANDIDATES: why.append("AMBIGUOUS_PARENT")
        if not (isinstance(v.vintage, str) and v.vintage): why.append("VINTAGE_NOT_RESOLVED")
        if not _int(v.watermark) or v.watermark < 0: why.append("WATERMARK_NOT_RESOLVED")
        out.append(SnapshotEntry(tf, sel, v.vintage if isinstance(v.vintage, str) and v.vintage else None, v.watermark if _int(v.watermark) and v.watermark >= 0 else None, UNRESOLVED if why else RESOLVED, tuple(why)))
    return SnapshotResolution(query_asof, tuple(out), RESOLVED if all(e.state == RESOLVED for e in out) else UNRESOLVED)
