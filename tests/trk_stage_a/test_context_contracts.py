"""News Hub V2 legality + Decision Context V4 envelope rules (pure validators; no ingestion/storage producer exists here)."""
import pytest
from stage_a.errors import Refusal
from stage_a.context import news_hub_v2 as N, decision_context as D

def test_actual_availability_is_max_and_fails_closed():
    assert N.actual_available_asof(False, None, None, 10) is None
    assert N.actual_available_asof(True, 5, 8, 10) == 8
    assert N.actual_available_asof(True, 9, 3, 10) == 9
    assert N.actual_available_asof(True, 5, 9, 10) == 9                         # strictly before the fence
    with pytest.raises(Refusal): N.actual_available_asof(True, 5, 10, 10)       # equality EXCLUDED (frozen Blueprint s28 NEWS-02: half-open fence)
    for a, b in ((None, 5), (5, None)):
        with pytest.raises(Refusal): N.actual_available_asof(True, a, b, 10)
    with pytest.raises(Refusal): N.actual_available_asof(True, 5, 11, 10)

def test_legality_lines():
    ok = lambda *a, **k: N.check_dimensions(*a, **k)
    assert ok("REQUIRED", "AVAILABLE", "COMPLETE", "EVENTS_PRESENT", coverage_basis="b") == "USABLE"
    assert ok("REQUIRED", "AVAILABLE", "COMPLETE", "NO_EVENT_RECORDED", coverage_basis="b") == "USABLE"
    with pytest.raises(Refusal): ok("REQUIRED", "AVAILABLE", "PARTIAL", "NO_EVENT_RECORDED", coverage_basis="b")   # needs COMPLETE
    with pytest.raises(Refusal): ok("OPTIONAL", "AVAILABLE", "PARTIAL", "NO_EVENT_RECORDED", optional_degraded_policy_ref="p")  # even with policy
    with pytest.raises(Refusal): ok("REQUIRED", "AVAILABLE", "COMPLETE", "EVENTS_PRESENT")                         # basis missing
    for pres in ("UNKNOWN", "NOT_EVALUATED"):
        with pytest.raises(Refusal): ok("REQUIRED", "AVAILABLE", "COMPLETE", pres, coverage_basis="b")
    with pytest.raises(Refusal): ok("REQUIRED", "AVAILABLE", "PARTIAL", "EVENTS_PRESENT")                          # legal object, not satisfied
    with pytest.raises(Refusal): ok("REQUIRED", "UNAVAILABLE", "UNKNOWN", "UNKNOWN")
    assert ok("NOT_REQUESTED", "NOT_EVALUATED", "NOT_EVALUATED", "NOT_EVALUATED") == "USABLE"
    for bad in ("MAYBE",):
        with pytest.raises(Refusal): ok(bad, "AVAILABLE", "COMPLETE", "EVENTS_PRESENT", coverage_basis="b")

def test_unavailable_complete_needs_prior_object_containing_window():
    base = ("REQUIRED", "UNAVAILABLE", "COMPLETE", "EVENTS_PRESENT")
    with pytest.raises(Refusal): N.check_dimensions(*base, coverage_basis="b")
    with pytest.raises(Refusal): N.check_dimensions(*base, coverage_basis="b", prior_coverage_contains_window=False, prior_coverage_issued_at=1, decision_cutoff=5)
    with pytest.raises(Refusal): N.check_dimensions(*base, coverage_basis="b", prior_coverage_contains_window=True, prior_coverage_issued_at=6, decision_cutoff=5)
    assert N.check_dimensions(*base, coverage_basis="b", prior_coverage_contains_window=True, prior_coverage_issued_at=4, decision_cutoff=5) == "USABLE"
    with pytest.raises(Refusal): N.check_dimensions(*base, coverage_basis="b", prior_coverage_contains_window=True, prior_coverage_issued_at=5, decision_cutoff=5)     # equality excluded

def test_optional_degraded_needs_policy_and_joins_respect_issued_at():
    with pytest.raises(Refusal): N.check_dimensions("OPTIONAL", "AVAILABLE", "PARTIAL", "UNKNOWN")
    assert N.check_dimensions("OPTIONAL", "AVAILABLE", "PARTIAL", "UNKNOWN", optional_degraded_policy_ref="p") == "USABLE"
    assert N.check_dimensions("OPTIONAL", "AVAILABLE", "COMPLETE", "EVENTS_PRESENT", coverage_basis="b") == "USABLE"
    assert N.daily_record_joinable(10, 11) and not N.daily_record_joinable(10, 10) and not N.daily_record_joinable(10, 9)       # NEWS-03: issued exactly at the fence is excluded
    assert N.missing_daily_record() == "UNKNOWN"

def _env(**kw):
    o = {k: "x" for k in D.ENVELOPE_REQUIRED}; o.update(CONTEXT_DOMAIN="TRACKER_LIFECYCLE", ORIGIN="SYSTEM"); o.update(kw); return o
def test_envelope_rules():
    D.check_envelope(_env())
    for k in D.ENVELOPE_REQUIRED:
        with pytest.raises(Refusal): D.check_envelope(_env(**{k: None}))
    with pytest.raises(Refusal): D.check_envelope(_env(CONTEXT_DOMAIN="MY_DOMAIN"))
    with pytest.raises(Refusal): D.check_envelope(_env(ORIGIN="BOT"))
    with pytest.raises(Refusal): D.check_envelope(_env(NEXT_PERMITTED_ACTION="PROMOTE"))
    with pytest.raises(Refusal): D.check_envelope(_env(ORIGIN="HUMAN_GOVERNANCE"))                  # mirror fields missing
    h = {k: "x" for k in D.HUMAN_MIRROR}; D.check_envelope(_env(ORIGIN="HUMAN_GOVERNANCE", **h))
    for k in D.HUMAN_MIRROR:
        with pytest.raises(Refusal): D.check_envelope(_env(ORIGIN="HUMAN_GOVERNANCE", **dict(h, **{k: None})))

def test_event_domain_mapping_and_status_event_rules():
    assert D.domain_for_event("holdout_unseal") == "CONSUMER_STAGE_GOVERNANCE"
    assert D.domain_for_event("construction_order") == "TRACKER_CONSTRUCTION"
    with pytest.raises(Refusal): D.domain_for_event("something_else")
    e = {k: 1 for k in D.STATUS_EVENT_REQUIRED}
    D.check_status_event(e, True)
    with pytest.raises(Refusal): D.check_status_event(e, False)                                       # status without context
    for k in D.STATUS_EVENT_REQUIRED:
        with pytest.raises(Refusal): D.check_status_event(dict(e, **{k: None}), True)
    ev = dict(CREATED_AT=5, AVAILABLE_ASOF=7, EFFECTIVE_AT=1)
    assert not D.as_of_visible(ev, 6) and D.as_of_visible(ev, 7) and not D.as_of_visible(dict(ev, CREATED_AT=9, AVAILABLE_ASOF=1), 5)

def test_fail_closed_safety_rule():
    r = D.fail_closed_transition("TRACKER", True, False)
    assert r["apply"] and r["review"] == "CONTEXT_DOMAIN_RESOLUTION_FAILURE" and not r["restoration_allowed"]
    assert D.fail_closed_transition("TRACKER", True, True)["restoration_allowed"]
    with pytest.raises(Refusal): D.fail_closed_transition("TRACKER", False, False)                    # non-risk-reducing is refused
    assert D.fail_closed_transition("ML", False, True)["apply"]
