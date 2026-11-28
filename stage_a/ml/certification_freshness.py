"""Certification freshness (MLCore V1.16 paragraph 306 and 26.O/432, native Drive 1cf1uR0w..., read R52). Source: an isolation/runtime certification PASS is bound to exact code, runtime, schema,
artifact-contract, instrument-package and test-suite identities; a change to ANY bound identity mechanically invalidates the prior certification until recertification occurs; and
INSTRUMENT_ISOLATION_STATE = PASS must identify the current valid certification, with FAIL, NOT_TESTED, stale certification, an unresolved violation or a missing certification identity blocking promotion.
Only those six identity NAMES and the blocking list come from the source. Identity values are opaque (no byte form, hash or scheme is defined or invented); equality of opaque values is the only comparison.
This is a pure check; it produces no certification, admits nothing and promotes nothing."""
from ..errors import Refusal

BOUND_IDENTITIES = ("CODE", "RUNTIME", "SCHEMA", "ARTIFACT_CONTRACT", "INSTRUMENT_PACKAGE", "TEST_SUITE")
STATES = ("PASS", "FAIL", "NOT_TESTED")

def certification_blocks_promotion(cert, current, unresolved_violation=False):
    """Returns None when the certification may count toward promotion, else the blocking code. `cert` = {CERTIFICATION_ID, STATE, BOUND: {six identities}}; `current` = the six identities now in force.
    Fails closed on every unknown or malformed input."""
    if not isinstance(cert, dict) or not isinstance(current, dict): return "CERTIFICATION_MISSING"
    cid = cert.get("CERTIFICATION_ID")
    if not (isinstance(cid, str) and cid): return "CERTIFICATION_IDENTITY_MISSING"
    st = cert.get("STATE")
    if st not in STATES: return "CERTIFICATION_STATE_UNKNOWN"
    if st == "FAIL": return "CERTIFICATION_FAIL"
    if st == "NOT_TESTED": return "CERTIFICATION_NOT_TESTED"
    bound = cert.get("BOUND")
    if not isinstance(bound, dict): return "CERTIFICATION_BINDING_MISSING"
    for n in BOUND_IDENTITIES:
        if bound.get(n) is None: return "CERTIFICATION_BINDING_INCOMPLETE"
        if current.get(n) is None: return "CURRENT_IDENTITY_UNKNOWN"
    if any(bound[n] != current[n] for n in BOUND_IDENTITIES): return "CERTIFICATION_STALE"
    if unresolved_violation is not False: return "UNRESOLVED_ISOLATION_VIOLATION"
    return None
