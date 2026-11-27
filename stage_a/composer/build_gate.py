"""Composer build start gate (V9 s7A: COMPOSER_BUILD_AUTHORITY = TRACKER_ORDER_ONLY; DIRECT_* to Composer = PROHIBITED; s38.2 build package != registry entry). A build may start only against an order that the Tracker JOURNALED:
the gate reads the order back from Core by id. A supplied request dict, an equal copy of an order, or any non-journaled object is refused (caller-supplied request equality is not order issuance). Candidate gate: it starts no build."""
from ..errors import Refusal

def accept_build_start(core, order_id, build_request: dict) -> dict:
    if not isinstance(order_id, str) or not order_id: raise Refusal(type(order_id).__name__, code="COMPOSER_BUILD_NEEDS_TRACKER_ORDER_ID")       # an order OBJECT is not an order
    o = core.order(order_id)
    if o is None or o.get("issuer") != "TRACKER": raise Refusal(order_id, code="COMPOSER_BUILD_WITHOUT_TRACKER_ORDER")
    if not isinstance(build_request, dict): raise Refusal("build request", code="COMPOSER_BUILD_REQUEST_MALFORMED")
    for k in ("CANDIDATE_IDENTITY", "EXPECTED_DELIVERY_CONTRACT", "OUTCOME_INFORMATION_ACCESS"):
        if build_request.get(k) != o["bindings"][k]: raise Refusal(k, code="COMPOSER_BUILD_DIFFERS_FROM_ORDER")                              # the build binds exactly what the order bound
    return o
