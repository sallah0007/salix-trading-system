"""Composer build start gate (V9 s7A: COMPOSER_BUILD_AUTHORITY = TRACKER_ORDER_ONLY; s38.2 build package != registry entry). The gate reads the order from the ONE order authority (tracker_component.ClaimService journal) by id and VERIFIES it now
(anchored issuer/source binding, unrevoked, unexpired): with an unadmitted anchor a qualified deployment refuses. The build request must restate EVERY stored order constraint that governs a build (identity, contract, outcome access, consumer-local
scope/causal boundary/temporal contract/vintage/availability/allowed/forbidden inputs); an omitted or contradicting field is refused. Candidate gate: it starts no build; the order is then consumed by TrackerPipeline through ClaimService.reserve."""
from ..errors import Refusal
from tracker_component.claims import Refusal as ClaimRefusal
from .intake import CONSUMER_LOCAL_ORDER_FIELDS

BUILD_BOUND = ("CANDIDATE_IDENTITY", "EXPECTED_DELIVERY_CONTRACT", "OUTCOME_INFORMATION_ACCESS", "RESEARCH_FAMILY_REFERENCE") + CONSUMER_LOCAL_ORDER_FIELDS

def accept_build_start(claims, order_id, build_request: dict) -> dict:
    if not isinstance(order_id, str) or not order_id: raise Refusal(type(order_id).__name__, code="COMPOSER_BUILD_NEEDS_TRACKER_ORDER_ID")       # an order OBJECT is not an order
    if not hasattr(claims, "verified_order"): raise Refusal(type(claims).__name__, code="COMPOSER_BUILD_NEEDS_CLAIM_AUTHORITY")
    try: o = claims.verified_order(order_id)
    except ClaimRefusal as e: raise Refusal(order_id, code="COMPOSER_BUILD_WITHOUT_TRACKER_ORDER" if e.code == "NO_ORDER" else "COMPOSER_BUILD_ORDER_NOT_VERIFIED:" + e.code)
    cons = o.constraints
    if cons is None: raise Refusal(order_id, code="COMPOSER_BUILD_ORDER_CARRIES_NO_CONSTRAINTS")
    if not isinstance(build_request, dict): raise Refusal("build request", code="COMPOSER_BUILD_REQUEST_MALFORMED")
    for k in BUILD_BOUND:
        if k not in cons:
            if k in build_request and k != "RESEARCH_FAMILY_REFERENCE": raise Refusal(k, code="COMPOSER_BUILD_DIFFERS_FROM_ORDER")        # the build asserts a constraint the order never bound
            continue
        if k not in build_request: raise Refusal(k, code="COMPOSER_BUILD_OMITS_ORDER_CONSTRAINT")
        if build_request[k] != cons[k]: raise Refusal(k, code="COMPOSER_BUILD_DIFFERS_FROM_ORDER")
    return o
