"""News Hub Event/Context V2 legality rules (sections 1-2, 9.0, 9.2A) as pure validators. Field lists come from the operative
document (Drive 1GSaxvVSkRmJDOgr7SqbPO2vHmuWEASVHzmn6Nuc5Ehw, read read-only). Ingestion/coverage production is NOT built: that is the
News Hub component's implementation, which is not in this repository. Byte encodings are not defined by the source (D13)."""
from typing import Optional
from ..errors import Refusal

REQ = ("REQUIRED", "OPTIONAL", "NOT_REQUESTED")
SRC = ("AVAILABLE", "UNAVAILABLE", "NOT_EVALUATED")
COV = ("COMPLETE", "PARTIAL", "DELAYED", "UNKNOWN", "NOT_EVALUATED")
PRES = ("EVENTS_PRESENT", "NO_EVENT_RECORDED", "UNKNOWN", "NOT_EVALUATED")

def actual_available_asof(actual_present: bool, publicly_available_at: Optional[int], salix_received_at: Optional[int],
                          decision_cutoff: int) -> Optional[int]:
    """ACTUAL_AVAILABLE_ASOF = max(public, SALIX receipt). Missing either while ACTUAL present => fail closed. Consumable only
    when <= decision cutoff (the document states <=, not the Gateway's half-open <; the difference is recorded as D14)."""
    if not actual_present:
        return None
    if publicly_available_at is None or salix_received_at is None:
        raise Refusal("ACTUAL present without both availability timestamps", code="ACTUAL_NOT_CAUSALLY_CONSUMABLE")
    asof = max(publicly_available_at, salix_received_at)
    if asof > decision_cutoff:
        raise Refusal("ACTUAL after decision cutoff", code="ACTUAL_AFTER_CUTOFF")
    return asof

def check_dimensions(req, src, cov, pres, coverage_basis=None, optional_degraded_policy_ref=None,
                     prior_coverage_contains_window: Optional[bool] = None, prior_coverage_issued_at: Optional[int] = None,
                     decision_cutoff: Optional[int] = None) -> str:
    """Returns USABLE or raises. Encodes the section-2 LEGALITY lines and the section-9.3 test matrix."""
    for v, dom in ((req, REQ), (src, SRC), (cov, COV), (pres, PRES)):
        if v not in dom:
            raise Refusal(str(v), code="BAD_CONTEXT_DIMENSION")
    if pres == "NO_EVENT_RECORDED" and cov != "COMPLETE":
        raise Refusal("NO_EVENT_RECORDED requires COMPLETE", code="NO_EVENT_WITHOUT_COMPLETE")
    if cov == "COMPLETE" and coverage_basis is None:
        raise Refusal("COMPLETE requires exact COVERAGE_BASIS", code="COMPLETE_WITHOUT_BASIS")
    if src == "UNAVAILABLE" and cov == "COMPLETE":
        ok = prior_coverage_contains_window is True and prior_coverage_issued_at is not None and decision_cutoff is not None \
             and prior_coverage_issued_at <= decision_cutoff
        if not ok:
            raise Refusal("UNAVAILABLE+COMPLETE needs a prior immutable coverage object containing the window",
                          code="UNAVAILABLE_COMPLETE_INVALID")
    if req == "NOT_REQUESTED":
        return "USABLE"
    if req == "REQUIRED":
        # PROPOSED (source gives only UNKNOWN => fail closed): anything short of AVAILABLE + COMPLETE fails closed for REQUIRED.
        # PARTIAL/DELAYED are legal objects but not a satisfied REQUIREMENT; the contract is silent, so fail closed (D14).
        # (UNAVAILABLE + COMPLETE reaches here only after the prior-coverage-object check above passed.)
        if cov != "COMPLETE" or pres in ("UNKNOWN", "NOT_EVALUATED") or src == "NOT_EVALUATED" or (src == "UNAVAILABLE" and cov != "COMPLETE"):
            raise Refusal("REQUIRED context not AVAILABLE+COMPLETE", code="REQUIRED_CONTEXT_FAIL_CLOSED")
        return "USABLE"
    degraded = pres in ("UNKNOWN", "NOT_EVALUATED") or cov != "COMPLETE" or src != "AVAILABLE"
    if degraded and optional_degraded_policy_ref is None:
        raise Refusal("OPTIONAL alone is not permission to degrade", code="OPTIONAL_DEGRADED_WITHOUT_POLICY")
    return "USABLE"

def daily_record_joinable(issued_at: int, bar_or_decision_time: int) -> bool:
    """A DAILY_EVENT_STATE_RECORD may not join to any time earlier than ISSUED_AT."""
    return bar_or_decision_time >= issued_at

def missing_daily_record() -> str:
    """A missing DAILY_EVENT_STATE_RECORD is UNKNOWN / alarm, never a quiet-day inference."""
    return "UNKNOWN"

# ---- R13: EVENT_RECORD (9.0) and DAILY_EVENT_STATE_RECORD (9.2A) validators + a deterministic context resolver ---------------------------------------------
# Source: News Hub V2 (Drive 1GSaxvVSkRmJDOgr7SqbPO2vHmuWEASVHzmn6Nuc5Ehw) sections 1-6, 9.0, 9.2A, 9.3; the pre-union list 9.1 and legacy 9.2 are historical and are not used
# except 9.2 as the legacy->V2 input mapping. 'A / B' entries in the source are modelled as 'either name'. Prose-only entries ('MISSINGNESS / STALENESS STATE',
# 'REVISION / CORRECTION LINEAGE', 'GOVERNING_MANIFEST_OR_PACKAGE_ID / HASH') have no token key names and are NOT enforced (no key invented).
# This is the market Event/Context resolver; it is NOT Decision Context (governance) and grants no authority. The Gateway's strict AVAILABLE_ASOF < SNAPSHOT_FENCE_TS
# binding rule is untouched: this resolver applies the document's own '<= decision cutoff' wording to ITS causal view only (D14 records the difference).
KNOWABILITY = ("OBSERVED", "MODELED_VALIDATED", "MODELED_EXPLORATORY", "UNKNOWN")
EVENT_REQUIRED = (("EVENT_ID", "EVENT_RECORD_ID"), ("EVENT_TYPE", "EVENT_CLASS"), ("SOURCE_ID",), ("SOURCE_PROVIDER_ID", "PROVIDER_ID"),
                  ("SOURCE_VERSION", "SOURCE_VINTAGE"), ("SOURCE_CONTRACT_VERSION",), ("INSTRUMENT", "MARKET", "CONTEXT_SCOPE"), ("EVENT_SCHEDULED_AT",),
                  ("SCHEDULE_VINTAGE",), ("SCHEDULE_CLOCK_DOMAIN",), ("VALUE_VINTAGE",), ("RELEASE_NUMBER",), ("REVISION_ID", "REVISION_SEQ"),
                  ("REVISION_AVAILABLE_AT",), ("PUBLICLY_AVAILABLE_AT",), ("SALIX_RECEIVED_AT",), ("AVAILABLE_ASOF",), ("SOURCE_TIMEZONE",),
                  ("TIME_NORMALISATION_ID",), ("KNOWABILITY_MODE",), ("FACTUAL_PAYLOAD_HASH",), ("QUALITY_STATE",), ("SOURCE_CONTRACT_STATE",), ("CAUSAL_AVAILABILITY",))
DAILY_REQUIRED = ("DAILY_EVENT_STATE_ID", "GOVERNED_SCOPE", "GOVERNED_DAY", "ISSUED_AT", "CONTEXT_REQUIREMENT_CLASS", "SOURCE_AVAILABILITY_STATE", "COVERAGE_STATE",
                  "EVENT_PRESENCE_STATE", "COVERAGE_BASIS", "RECORD_HASH")
LEGACY_COVERAGE = {"COVERED_WITH_EVENTS": ("AVAILABLE", "COMPLETE", "EVENTS_PRESENT", True), "COVERED_NO_EVENTS": ("AVAILABLE", "COMPLETE", "NO_EVENT_RECORDED", True)}

def _has(rec, names): return any(rec.get(n) is not None for n in names)

def check_event_record(rec: dict) -> None:
    missing = [("/".join(g)) for g in EVENT_REQUIRED if not _has(rec, g)]
    if missing:
        raise Refusal(",".join(missing), code="EVENT_RECORD_FIELD_MISSING")
    if rec["KNOWABILITY_MODE"] not in KNOWABILITY:
        raise Refusal(str(rec["KNOWABILITY_MODE"]), code="BAD_KNOWABILITY_MODE")
    if _has(rec, ("ACTUAL_VALUE", "ACTUAL")):
        need = [k for k in ("ACTUAL_PUBLICLY_AVAILABLE_AT", "ACTUAL_SALIX_RECEIVED_AT", "ACTUAL_AVAILABLE_ASOF") if rec.get(k) is None]
        if need:
            raise Refusal(",".join(need), code="ACTUAL_NOT_CAUSALLY_CONSUMABLE")             # fail closed for authority-bearing use
        if rec["ACTUAL_AVAILABLE_ASOF"] != max(rec["ACTUAL_PUBLICLY_AVAILABLE_AT"], rec["ACTUAL_SALIX_RECEIVED_AT"]):
            raise Refusal("ACTUAL_AVAILABLE_ASOF", code="ACTUAL_AVAILABLE_ASOF_NOT_MAX_OF_PUBLIC_AND_RECEIPT")
    if rec.get("IMPACT_RATING") is not None and rec.get("IMPACT_RATING_VINTAGE") is None:
        raise Refusal("IMPACT_RATING", code="IMPACT_RATING_WITHOUT_VINTAGE")

def check_daily_record(rec: dict) -> None:
    if "NO_EVENT_RECORDED" in rec:
        raise Refusal("NO_EVENT_RECORDED", code="NO_EVENT_RECORDED_IS_A_VALUE_NOT_A_BOOLEAN_FIELD")
    missing = [k for k in DAILY_REQUIRED if rec.get(k) is None]
    if missing:
        raise Refusal(",".join(missing), code="DAILY_RECORD_FIELD_MISSING")
    if not (rec.get("SOURCE_SET") is not None or rec.get("SOURCE_POLICY_VERSION") is not None):
        raise Refusal("SOURCE_SET/SOURCE_POLICY_VERSION", code="DAILY_RECORD_FIELD_MISSING")
    req = rec["CONTEXT_REQUIREMENT_CLASS"]
    # Record legality only (section 2 lines + conditional OPTIONAL_DEGRADED_POLICY_REF). 'Is this usable for a REQUIRED consumer' is a consumer decision (resolve_context).
    check_dimensions("OPTIONAL" if req == "OPTIONAL" else "NOT_REQUESTED", rec["SOURCE_AVAILABILITY_STATE"], rec["COVERAGE_STATE"], rec["EVENT_PRESENCE_STATE"],
                     rec["COVERAGE_BASIS"], rec.get("OPTIONAL_DEGRADED_POLICY_REF"), rec.get("PRIOR_COVERAGE_OBJECT_REF") is not None,
                     rec.get("PRIOR_COVERAGE_ISSUED_AT"), rec["ISSUED_AT"])
    if req not in REQ:
        raise Refusal(str(req), code="BAD_CONTEXT_DIMENSION")

def event_consumable(ev: dict, cutoff: int):
    """(consumable: bool, reason). ACTUAL and revisions are consumable only when their own availability <= the decision cutoff."""
    if ev["REVISION_AVAILABLE_AT"] > cutoff:
        return False, "REVISION_NOT_YET_AVAILABLE"
    if _has(ev, ("ACTUAL_VALUE", "ACTUAL")) and ev["ACTUAL_AVAILABLE_ASOF"] > cutoff:
        return False, "ACTUAL_NOT_YET_AVAILABLE"
    return True, ""

def resolve_context(requirement: str, daily_record, event_records, decision_cutoff: int) -> dict:
    """Deterministic view of context at a decision cutoff. Never infers a quiet day: a missing or not-yet-issued daily record is UNKNOWN, and for REQUIRED it refuses.
    Revisions: of the records sharing an event id, the highest revision sequence available <= cutoff is used; two different payloads at the same revision are returned as
    MULTIPLE_CANDIDATES (a deterministic-tie rule taken from the native Tracker reference, which is NAVIGATION ONLY until the exact frozen clause is compared)."""
    if requirement not in REQ:
        raise Refusal(str(requirement), code="BAD_CONTEXT_DIMENSION")
    if requirement == "NOT_REQUESTED":
        return {"verdict": "USABLE", "coverage": "NOT_REQUESTED", "exhaustive": False, "events": [], "withheld": [], "multiple_candidates": []}
    joinable = daily_record is not None and daily_record_joinable(daily_record["ISSUED_AT"], decision_cutoff)
    if not joinable:
        if requirement == "REQUIRED":
            raise Refusal("daily record missing or not yet issued", code="REQUIRED_CONTEXT_FAIL_CLOSED")
        raise Refusal("OPTIONAL with no joinable daily record", code="OPTIONAL_DEGRADED_WITHOUT_POLICY")     # UNKNOWN is never quiet-day inference
    check_dimensions(requirement, daily_record["SOURCE_AVAILABILITY_STATE"], daily_record["COVERAGE_STATE"], daily_record["EVENT_PRESENCE_STATE"],
                     daily_record.get("COVERAGE_BASIS"), daily_record.get("OPTIONAL_DEGRADED_POLICY_REF"),
                     daily_record.get("PRIOR_COVERAGE_OBJECT_REF") is not None, daily_record.get("PRIOR_COVERAGE_ISSUED_AT"), decision_cutoff)
    by_id = {}
    for ev in event_records:
        check_event_record(ev)
        by_id.setdefault(ev.get("EVENT_ID") or ev.get("EVENT_RECORD_ID"), []).append(ev)
    used, withheld, multi = [], [], []
    for eid in sorted(by_id):
        avail = []
        for ev in by_id[eid]:
            ok, why = event_consumable(ev, decision_cutoff)
            (avail if ok else withheld).append(ev if ok else (eid, why))
        if not avail:
            continue
        top = max(e.get("REVISION_SEQ", 0) for e in avail)
        cands = [e for e in avail if e.get("REVISION_SEQ", 0) == top]
        if len({e["FACTUAL_PAYLOAD_HASH"] for e in cands}) > 1:
            multi.append(eid)
        else:
            used.append(cands[0])
    return {"verdict": "USABLE", "coverage": daily_record["COVERAGE_STATE"], "exhaustive": daily_record["COVERAGE_STATE"] == "COMPLETE",
            "events": used, "withheld": withheld, "multiple_candidates": multi}
