"""Contract V0.38 H3 (operative V0.37 field list) OUTCOME_SERIES / TARGET_LABEL_SERIES delivery validator. Source-present candidate: required fields, the five conditional references, and the RULE that the ENTIRE dependency
interval must lie inside currently authorized consumer segments and must not touch a sealed holdout without a HOLDOUT_UNSEAL_EVENT_REF; otherwise delivery is WITHHELD.
Inputs that are NOT defined here and are therefore supplied by the caller and labelled unadmitted: the authorized segment set itself (who authorizes, stage vocabulary), which regions are sealed holdout / unopened outer-test, and
which conditional references apply to a consumer's validation contract (the *_applies flags). Interval endpoints are CLOSED integer timestamps (the unit/closure convention is not source-given beyond 'entire interval'); a gap
between authorized segments is unauthorized. A consumer that skips this validator receives nothing from the Gateway path: no Binding-like object is built here, only a decision."""
from dataclasses import dataclass
from typing import Optional, Tuple
from ..errors import Refusal

REQUIRED = ("consumer_binding_id", "series_id", "series_version_or_hash", "observation_time_origin", "horizon_id", "horizon_version", "authorized_segment_set_or_stage", "consumer_stage", "outcome_package_hash")
CONDITIONAL = (("stage_advance_applies", "stage_advance_event_ref"), ("research_exposure_material", "research_family_reference"), ("family_state_evaluated", "family_ledger_state_ref"),
               ("purge_embargo_required", "dependence_purge_embargo_ref"))

@dataclass(frozen=True)
class OutcomeSeriesPackage:
    consumer_binding_id: Optional[str]; series_id: Optional[str]; series_version_or_hash: Optional[str]; observation_time_origin: Optional[str]
    horizon_id: Optional[str]; horizon_version: Optional[str]; dependency_interval_start: Optional[int]; dependency_interval_end: Optional[int]
    authorized_segment_set_or_stage: Optional[str]; consumer_stage: Optional[str]; outcome_package_hash: Optional[str]; available_asof: Optional[int]; delivery_decision_ts: Optional[int]
    stage_advance_event_ref: Optional[str] = None; holdout_unseal_event_ref: Optional[str] = None; research_family_reference: Optional[str] = None
    family_ledger_state_ref: Optional[str] = None; dependence_purge_embargo_ref: Optional[str] = None

@dataclass(frozen=True)
class DeliveryContext:
    """Caller-supplied, UNADMITTED: the currently authorized segments (closed [start, end] intervals) and sealed-holdout regions, plus which conditional references apply."""
    authorized_segments: tuple; sealed_holdout_intervals: tuple = ()
    stage_advance_applies: bool = False; research_exposure_material: bool = False; family_state_evaluated: bool = False; purge_embargo_required: bool = False

@dataclass(frozen=True)
class H3Decision:
    delivered: bool; reasons: tuple; admission: str = "AUTHORIZED_SEGMENTS_AND_APPLICABILITY_CALLER_SUPPLIED_UNADMITTED"

def _s(x): return isinstance(x, str) and bool(x)
def _i(x): return type(x) is int and x >= 0
def _ivs(xs):
    out = []
    for iv in xs:
        if not (isinstance(iv, tuple) and len(iv) == 2 and _i(iv[0]) and _i(iv[1]) and iv[0] <= iv[1]): raise Refusal(repr(iv), code="H3_CONTEXT_INTERVAL_MALFORMED")
        out.append(iv)
    return out

def _covered(start, end, segs) -> bool:
    """Whole [start,end] inside the union of closed segments with NO gap (adjacent integer segments touch: next.start <= cur.end + 1)."""
    cur = start
    for s, e in sorted(segs):
        if s > cur: break
        if e >= cur: cur = e + 1
        if cur > end: return True
    return cur > end

def evaluate(pkg, ctx) -> H3Decision:
    if not isinstance(pkg, OutcomeSeriesPackage) or not isinstance(ctx, DeliveryContext): raise Refusal("types", code="H3_NOT_TYPED_PACKAGE_OR_CONTEXT")
    segs = _ivs(ctx.authorized_segments); sealed = _ivs(ctx.sealed_holdout_intervals); w = []
    for f in REQUIRED:
        if not _s(getattr(pkg, f)): w.append("MISSING_REQUIRED:" + f)
    for f in ("dependency_interval_start", "dependency_interval_end", "available_asof", "delivery_decision_ts"):
        if not _i(getattr(pkg, f)): w.append("MISSING_REQUIRED:" + f)
    for flag, ref in CONDITIONAL:
        if getattr(ctx, flag) not in (True, False): raise Refusal(flag, code="H3_APPLICABILITY_NOT_BOOLEAN")
        if getattr(ctx, flag) and not _s(getattr(pkg, ref)): w.append("MISSING_CONDITIONAL:" + ref)
    s, e = pkg.dependency_interval_start, pkg.dependency_interval_end
    if _i(s) and _i(e):
        if s > e: w.append("INTERVAL_INVERTED")
        else:
            if not _covered(s, e, segs): w.append("INTERVAL_OUTSIDE_AUTHORIZED_SEGMENTS")
            if any(s <= se and hs <= e for hs, se in sealed) and not _s(pkg.holdout_unseal_event_ref): w.append("SEALED_HOLDOUT_WITHOUT_UNSEAL_EVENT_REF")      # independent of the segment test
    if _i(pkg.available_asof) and _i(pkg.delivery_decision_ts) and pkg.available_asof >= pkg.delivery_decision_ts: w.append("AVAILABLE_ASOF_NOT_BEFORE_DECISION")       # same strict-before rule as Gateway G1
    w = tuple(sorted(set(w))); return H3Decision(not w, w)

def require_delivery(pkg, ctx) -> H3Decision:
    d = evaluate(pkg, ctx)
    if not d.delivered: raise Refusal(",".join(d.reasons), code="H3_DELIVERY_WITHHELD")
    return d
