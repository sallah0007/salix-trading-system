"""Contract V0.38 H3 (operative V0.37 field list) OUTCOME_SERIES / TARGET_LABEL_SERIES: STRUCTURAL candidate check. Required fields, the five conditional references and the RULE that the ENTIRE dependency interval must lie inside currently
authorized consumer segments and must not touch a sealed holdout without a valid HOLDOUT_UNSEAL_EVENT_REF, else delivery is withheld.
What this is NOT: authorized delivery. `authorized_delivery` is always False here; the segment authorization, the sealed regions, the unseal-event resolver and the applicability of each conditional reference are INPUTS that no source read
defines an owner/instance for, so they are supplied by the caller, labelled UNADMITTED, and MISSING knowledge is never read as "not applicable / no sealed region / valid":
  * the interval/segment boundary convention is NOT specified by H3. It is not selected here: with no convention supplied, every boundary-dependent case is evaluated under each candidate convention (HALF_OPEN, CLOSED_CONTINUOUS,
    DISCRETE_TICK) and a disagreement is typed UNDETERMINED_BOUNDARY_CONVENTION (held); a caller-supplied convention is used but labelled unadmitted;
  * applicability flags / sealed regions / authorized segments / unseal resolver left as None are UNKNOWN => held; an unseal ref that the supplied resolver set does not contain is WITHHELD, a bare non-empty string is not validation.
No stage vocabulary, timestamp or threshold is defined here. The only ordering rule reused is Gateway G1 (available_asof strictly before the decision timestamp)."""
from dataclasses import dataclass
from typing import Optional
from ..errors import Refusal

REQUIRED = ("consumer_binding_id", "series_id", "series_version_or_hash", "observation_time_origin", "horizon_id", "horizon_version", "authorized_segment_set_or_stage", "consumer_stage", "outcome_package_hash")
CONDITIONAL = (("stage_advance_applies", "stage_advance_event_ref"), ("research_exposure_material", "research_family_reference"), ("family_state_evaluated", "family_ledger_state_ref"),
               ("purge_embargo_required", "dependence_purge_embargo_ref"))
CONVENTIONS = ("HALF_OPEN", "CLOSED_CONTINUOUS", "DISCRETE_TICK")
PASS_STRUCTURAL, WITHHELD, UNDETERMINED = "STRUCTURAL_PASS_CANDIDATE", "WITHHELD", "UNDETERMINED_HELD"

@dataclass(frozen=True)
class OutcomeSeriesPackage:
    consumer_binding_id: Optional[str]; series_id: Optional[str]; series_version_or_hash: Optional[str]; observation_time_origin: Optional[str]
    horizon_id: Optional[str]; horizon_version: Optional[str]; dependency_interval_start: Optional[int]; dependency_interval_end: Optional[int]
    authorized_segment_set_or_stage: Optional[str]; consumer_stage: Optional[str]; outcome_package_hash: Optional[str]; available_asof: Optional[int]; delivery_decision_ts: Optional[int]
    stage_advance_event_ref: Optional[str] = None; holdout_unseal_event_ref: Optional[str] = None; research_family_reference: Optional[str] = None
    family_ledger_state_ref: Optional[str] = None; dependence_purge_embargo_ref: Optional[str] = None

@dataclass(frozen=True)
class DeliveryContext:
    """Every field is a caller-supplied UNADMITTED input; None = UNKNOWN (never defaulted to N/A, empty or valid)."""
    authorized_segments: Optional[tuple] = None; sealed_holdout_intervals: Optional[tuple] = None; valid_unseal_event_refs: Optional[frozenset] = None
    stage_advance_applies: Optional[bool] = None; research_exposure_material: Optional[bool] = None; family_state_evaluated: Optional[bool] = None; purge_embargo_required: Optional[bool] = None
    boundary_convention: Optional[str] = None

@dataclass(frozen=True)
class H3Decision:
    status: str; reasons: tuple; authorized_delivery: bool = False
    admission: str = "SEGMENTS_SEALED_REGIONS_UNSEAL_RESOLVER_APPLICABILITY_CONVENTION_CALLER_SUPPLIED_UNADMITTED"
    @property
    def structurally_passes(self): return self.status == PASS_STRUCTURAL

def _s(x): return isinstance(x, str) and bool(x)
def _i(x): return type(x) is int and x >= 0
def _ivs(xs):
    out = []
    for iv in xs:
        if not (isinstance(iv, tuple) and len(iv) == 2 and _i(iv[0]) and _i(iv[1]) and iv[0] <= iv[1]): raise Refusal(repr(iv), code="H3_CONTEXT_INTERVAL_MALFORMED")
        out.append(iv)
    return out

def _covered(s, e, segs, conv) -> bool:
    """Coverage of EXACTLY the requested interval [s, e] by the union of the segments: segments entirely before the first uncovered point are irrelevant and skipped (R30: an earlier unrelated segment must not stop the scan); a real gap
    stops it. gap = 1 for DISCRETE_TICK (adjacent integer segments touch), 0 for the continuous conventions (they must share the boundary point)."""
    gap = 1 if conv == "DISCRETE_TICK" else 0
    reach = None
    for a, b in sorted(segs):
        if reach is None:
            if a > s: break                                  # sorted: no later segment can cover s either
            if b < s: continue                               # irrelevant past segment
            reach = b
        elif a <= reach + gap: reach = max(reach, b)
        else: break
        if reach >= e: return True
    return False

def _touches(s, e, hs, he, conv) -> bool:
    if conv == "HALF_OPEN": return s < he and hs < e
    return s <= he and hs <= e

def evaluate(pkg, ctx) -> H3Decision:
    if not isinstance(pkg, OutcomeSeriesPackage) or not isinstance(ctx, DeliveryContext): raise Refusal("types", code="H3_NOT_TYPED_PACKAGE_OR_CONTEXT")
    if ctx.boundary_convention is not None and ctx.boundary_convention not in CONVENTIONS: raise Refusal(str(ctx.boundary_convention), code="H3_CONVENTION_UNKNOWN")
    w, u = [], []
    for f in REQUIRED:
        if not _s(getattr(pkg, f)): w.append("MISSING_REQUIRED:" + f)
    for f in ("dependency_interval_start", "dependency_interval_end", "available_asof", "delivery_decision_ts"):
        if not _i(getattr(pkg, f)): w.append("MISSING_REQUIRED:" + f)
    for flag, ref in CONDITIONAL:
        v = getattr(ctx, flag)
        if v is None: u.append("APPLICABILITY_UNKNOWN:" + flag)
        elif v is not True and v is not False: raise Refusal(flag, code="H3_APPLICABILITY_NOT_BOOLEAN")           # strict typed booleans: 0/1 are not applicability values
        elif v and not _s(getattr(pkg, ref)): w.append("MISSING_CONDITIONAL:" + ref)
    if _i(pkg.available_asof) and _i(pkg.delivery_decision_ts) and pkg.available_asof >= pkg.delivery_decision_ts: w.append("AVAILABLE_ASOF_NOT_BEFORE_DECISION")       # Gateway G1 rule
    s, e = pkg.dependency_interval_start, pkg.dependency_interval_end
    if _i(s) and _i(e):
        if s > e: w.append("INTERVAL_INVERTED")
        else:
            if ctx.authorized_segments is None: u.append("AUTHORIZED_SEGMENTS_NOT_SUPPLIED")
            if ctx.sealed_holdout_intervals is None: u.append("SEALED_REGIONS_NOT_SUPPLIED")
            if ctx.authorized_segments is not None and ctx.sealed_holdout_intervals is not None:
                segs = _ivs(ctx.authorized_segments); sealed = _ivs(ctx.sealed_holdout_intervals)
                convs = (ctx.boundary_convention,) if ctx.boundary_convention else CONVENTIONS
                cov = {c: _covered(s, e, segs, c) for c in convs}; tou = {c: any(_touches(s, e, hs, he, c) for hs, he in sealed) for c in convs}
                if all(cov.values()): pass
                elif not any(cov.values()): w.append("INTERVAL_OUTSIDE_AUTHORIZED_SEGMENTS")
                else: u.append("UNDETERMINED_BOUNDARY_CONVENTION:segments")
                if any(tou.values()):
                    if not _s(pkg.holdout_unseal_event_ref) and all(tou.values()): w.append("SEALED_HOLDOUT_WITHOUT_UNSEAL_EVENT_REF")
                    elif not all(tou.values()): u.append("UNDETERMINED_BOUNDARY_CONVENTION:sealed")
                    elif ctx.valid_unseal_event_refs is None: u.append("UNSEAL_RESOLUTION_INPUT_NOT_SUPPLIED")
                    elif pkg.holdout_unseal_event_ref not in ctx.valid_unseal_event_refs: w.append("UNSEAL_EVENT_REF_NOT_RESOLVED")
    if w: return H3Decision(WITHHELD, tuple(sorted(set(w + u))))
    if u: return H3Decision(UNDETERMINED, tuple(sorted(set(u))))
    return H3Decision(PASS_STRUCTURAL, ())

def require_structural_pass(pkg, ctx) -> H3Decision:
    d = evaluate(pkg, ctx)
    if not d.structurally_passes: raise Refusal(",".join(d.reasons), code="H3_DELIVERY_WITHHELD_OR_UNDETERMINED")
    return d
