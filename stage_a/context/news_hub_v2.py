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
