"""H3 OUTCOME_SERIES / TARGET_LABEL_SERIES delivery decision (R46). SOURCE: Connected Contract V0.38 H3 (Drive 1neiQsQ9AG-QKdyMgOqJxXE026D0uY___yhfGaTlIJ8Y; field list and the RULE read R46; cited by ID, not copied).
REQUIRED fields (closed set + the conditional ones). RULE: the ENTIRE dependency interval must lie inside currently authorized consumer segments; any part crossing an unauthorized next segment, an unopened outer-test region or a sealed
holdout without a valid HOLDOUT_UNSEAL_EVENT_REF => delivery WITHHELD.
CANDIDATE CHOICES (named, not source): intervals are half-open [start, end) integers (the repository's D14 reading); start < end; AVAILABLE_ASOF <= DELIVERY_DECISION_TS (as-of causality); segments / sealed holdouts / unopened regions are SUPPLIED
interval sets (the segment model is source-owned and unbound); a conditional ref is checked for PRESENCE/shape only (its resolution against a governed event is source-owned and unbound). Result is never a gate or an acceptance."""
from dataclasses import dataclass
from typing import Tuple
from ..errors import Refusal

REQUIRED = ("consumer_binding_id", "outcome_or_target_series_id", "series_version_or_hash", "observation_time_origin", "horizon_id", "horizon_version", "dependency_interval_start",
            "dependency_interval_end", "authorized_segment_set", "consumer_stage", "outcome_package_hash", "available_asof", "delivery_decision_ts")
CONDITIONAL = ("stage_advance_event_ref", "holdout_unseal_event_ref", "research_family_reference", "family_ledger_state_ref", "dependence_purge_embargo_ref")
def _s(x): return isinstance(x, str) and bool(x)
def _i(x): return type(x) is int and x >= 0

@dataclass(frozen=True)
class OutcomeDecision:
    delivered: bool
    reasons: Tuple[str, ...]
    qualified: bool = False

def _covered(start, end, ivs):
    """is [start,end) inside the union of the half-open intervals `ivs`?"""
    cur = start
    for a, b in sorted(ivs):
        if a <= cur < b: cur = b
        if cur >= end: return True
    return cur >= end

def decide(record, *, sealed_holdout=(), unopened_regions=(), segments_by_name=None):
    """record: dict with REQUIRED keys (+ optional CONDITIONAL). authorized_segment_set: list of segment names resolved through `segments_by_name` {name: [(start,end)...]} (SUPPLIED). Raises Refusal on a malformed record (fail closed)."""
    if not isinstance(record, dict): raise Refusal(type(record).__name__, code="H3_RECORD_NOT_AN_OBJECT")
    miss = [k for k in REQUIRED if k not in record]; extra = sorted(set(record) - set(REQUIRED) - set(CONDITIONAL))
    if miss or extra: raise Refusal("missing=%s extra=%s" % (miss, extra), code="H3_FIELD_SET")
    for k in REQUIRED:
        if k in ("dependency_interval_start", "dependency_interval_end", "available_asof", "delivery_decision_ts", "observation_time_origin"):
            if not _i(record[k]): raise Refusal(k, code="H3_FIELD_INVALID")
        elif k == "authorized_segment_set":
            if not (isinstance(record[k], list) and record[k] and all(_s(x) for x in record[k]) and len(set(record[k])) == len(record[k])): raise Refusal(k, code="H3_FIELD_INVALID")
        elif not _s(record[k]): raise Refusal(k, code="H3_FIELD_INVALID")
    for k in CONDITIONAL:
        if k in record and not _s(record[k]): raise Refusal(k, code="H3_FIELD_INVALID")
    s, e = record["dependency_interval_start"], record["dependency_interval_end"]
    if not s < e: raise Refusal("%d>=%d" % (s, e), code="H3_INTERVAL_EMPTY_OR_REVERSED")
    if record["available_asof"] > record["delivery_decision_ts"]: raise Refusal("available_asof after decision", code="H3_AVAILABLE_AFTER_DECISION")
    if segments_by_name is None: raise Refusal("segments", code="H3_SEGMENT_MODEL_UNSUPPLIED_HELD")
    ivs = []
    for n in record["authorized_segment_set"]:
        if n not in segments_by_name: raise Refusal(n, code="H3_SEGMENT_UNKNOWN")
        ivs += list(segments_by_name[n])
    reasons = []
    if not _covered(s, e, ivs): reasons.append("INTERVAL_NOT_INSIDE_AUTHORIZED_SEGMENTS")
    def hits(regions): return any(a < e and s < b for a, b in regions)
    if hits(unopened_regions): reasons.append("INTERVAL_TOUCHES_UNOPENED_REGION")
    if hits(sealed_holdout) and "holdout_unseal_event_ref" not in record: reasons.append("SEALED_HOLDOUT_WITHOUT_UNSEAL_EVENT_REF")
    return OutcomeDecision(not reasons, tuple(reasons))
