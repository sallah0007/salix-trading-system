"""Connected Contract V0.38 delivery-failure rules (read from the operative document). Field-level + pure-rule checks only;
the resolver is still the simulation. FINAL_RESOLUTION_HASH / PACKAGE_HASH bytes are NOT covered (D13)."""
import pytest
from stage_a.errors import Refusal
from stage_a.gateway import v038 as V, contracts as G
from tests.trk_stage_a.test_boundaries import _gw, _entry, _health, I, R, T

KEY = V.ExpectedDependencyKey("f1", "STEP_INDEX", 3, "ORIGINAL_AS_OBSERVED")
IDN = V.FinalResolutionIdentity("FW", "man1", "EURUSD", "w1")
WM = V.VisibilityWatermark(50, 12)

def test_status_set_is_exactly_three_and_superseded_is_not_one():
    assert set(V.NON_DELIVERY_STATUSES) == {"NOT_READY_REQUIRED_DEPENDENCY", "REJECTED_FAIL_CLOSED", "REQUEST_AFTER_CUTOFF"}
    with pytest.raises(Refusal): V.NonDeliveryResolutionV038("r", IDN, "SUPERSEDED", "FW", 10, "c", "p", "t", WM, (), (), 1)

def test_status_mapping_fails_closed_on_unknown_reason():
    assert V.status_for_reason("REQUIRED_DEPENDENCY_ABSENT") == V.NOT_READY
    assert V.status_for_reason("CHAIN_STATUS_NOT_CURRENT:CATCHING_UP") == V.NOT_READY
    assert V.status_for_reason("STALE_WATERMARK") == V.REJECTED
    assert V.status_for_reason("SOMETHING_NEW") == V.REJECTED

def test_omission_must_be_structured_with_expected_key():
    with pytest.raises(Refusal): V.StructuredOmission(I, "f1", "", KEY)
    with pytest.raises(Refusal): V.StructuredOmission(I, "f1", "X", None)
    with pytest.raises(Refusal): V.StructuredOmission(I, "f2", "X", KEY)           # key for another feature version
    with pytest.raises(Refusal): V.ExpectedDependencyKey("f1", "WALL_CLOCK", 3, "m")
    with pytest.raises(Refusal): V.ExpectedDependencyKey("f1", "STEP_INDEX", 3, "")
    assert V.StructuredOmission(I, "f1", "X", KEY).expected_key is KEY

def test_not_ready_requires_omissions_and_health_pair_and_issuer():
    base = ("r", IDN, V.NOT_READY, "FW", 10, "c", "p", "t", WM)
    with pytest.raises(Refusal): V.NonDeliveryResolutionV038(*base, (), (), 1)
    om = (V.StructuredOmission(I, "f1", "X", KEY),)
    with pytest.raises(Refusal): V.NonDeliveryResolutionV038(*base, om, ("X",), 1, bound_health_resolved_at=3)
    with pytest.raises(Refusal): V.NonDeliveryResolutionV038(*base, om, ("X",), 1, issuer="FW")
    assert V.NonDeliveryResolutionV038(*base, om, ("X",), 1).status == V.NOT_READY

def test_to_v038_from_simulated_nondelivery():
    nd = _gw(avail=10).resolve("a", _entry(), I, I, 3, 10, _health())
    out = V.to_v038(nd, IDN, KEY, WM, "FW", "c", "p", "t", 11)
    assert out.status == V.NOT_READY and out.omissions[0].reason_code == "NOT_AVAILABLE_BEFORE_FENCE"

def test_settlement_delay_visibility_not_causality():
    obs = V.check_settlement(10, 5, 4, 15)
    assert obs == 15
    with pytest.raises(Refusal): V.check_settlement(10, 5, None, 15)                 # unknown bound -> fail closed
    with pytest.raises(Refusal): V.check_settlement(10, 3, 4, 15)                    # delay below certified lag
    with pytest.raises(Refusal): V.check_settlement(10, 5, 4, 14)                    # resolving before the settlement point
    # a pre-fence row that becomes visible inside the delay IS delivered; the same row visible after it is not
    assert isinstance(_gw(avail=4, visible=12).resolve("ok", _entry(), I, I, 3, 10, _health(), observed_at=obs), G.Binding)
    assert _gw(avail=4, visible=16).resolve("no", _entry(), I, I, 3, 10, _health(), observed_at=obs).reason == "LATE_VISIBILITY"
    # the delay never widens causality: equality/post-fence availability stays excluded even when visible in time
    assert _gw(avail=10, visible=11).resolve("eq", _entry(), I, I, 3, 10, _health(), observed_at=obs).reason == "NOT_AVAILABLE_BEFORE_FENCE"

def test_forensic_classification_three_ways():
    assert V.classify_late(10, 10, 99, WM) == V.GENUINE_LATE                          # equality is late
    assert V.classify_late(9, 10, 51, WM) == V.SETTLEMENT_BREACH                      # visible only after watermark
    assert V.classify_late(9, 10, 50, WM) == V.RESOLVER_FAULT                         # at/before watermark but omitted
    with pytest.raises(Refusal): V.classify_late(9, 10, 50, WM, omitted_by_resolver=False)

def test_one_final_outcome_per_identity_retries_reuse_and_never_reevaluate():
    s, calls = V.FinalResolutionStore(), []
    def ev(): calls.append(1); return object()
    a = s.resolve("r1", IDN, ev); b = s.resolve("r2", IDN, ev); c = s.resolve("r1", IDN, ev)
    assert a is b is c and len(calls) == 1 and s.evaluations == 1
    other = V.FinalResolutionIdentity("FW", "man1", "EURUSD", "w2")
    assert s.resolve("r3", other, ev) is not a and s.evaluations == 2               # distinct window evaluates separately
    with pytest.raises(Refusal): s.resolve("r1", other, ev)                           # request id cannot hop identities
    with pytest.raises(Refusal): s.late_dependency_mutates(IDN)                       # expired window is immutable
    s.late_dependency_mutates(V.FinalResolutionIdentity("FW", "man1", "EURUSD", "w9"))  # an unresolved window is not

def _h1(**kw):
    f = {k: "x" for k in V.H1_REQUIRED}; f.update(ISSUER="TRACKER_CONSUMER_GATEWAY", PACKAGE_CLASS="FW_PACKAGE",
                                                   RESOLUTION_VISIBILITY_WATERMARK="w"); f.update(kw); return f
def test_h1_presence_conditionals_and_package_class():
    V.check_h1(_h1())
    for k in V.H1_REQUIRED + ("RESOLUTION_VISIBILITY_WATERMARK",):
        with pytest.raises(Refusal): V.check_h1(_h1(**{k: None}))
    with pytest.raises(Refusal): V.check_h1(_h1(), consumer_is_ml=True)               # ML needs manifest + generation class
    V.check_h1(_h1(ML_MANIFEST_CLASS="m", GENERATION_AUTHORITY_CLASS="g"), consumer_is_ml=True)
    with pytest.raises(Refusal): V.check_h1(_h1(PACKAGE_CLASS="BASELINE"))            # a lane name is not a PACKAGE_CLASS
    with pytest.raises(Refusal): V.check_h1(_h1(ISSUER="FW"))
    V.check_h1(_h1(RESOLUTION_VISIBILITY_WATERMARK=None), decision_window=False)      # range deliveries do not need it

# ---------- review R04: concurrency / re-entrancy / failure controls (single-process contract) ---------------------------
import threading, time
def test_concurrent_callers_get_one_evaluation_and_one_object():
    s, calls, outs = V.FinalResolutionStore(), [], []
    gate = threading.Barrier(16)
    def ev():
        calls.append(1); time.sleep(0.01); return object()
    def worker(i):
        gate.wait(); outs.append(s.resolve("r%d" % i, IDN, ev))
    ts = [threading.Thread(target=worker, args=(i,)) for i in range(16)]
    [t.start() for t in ts]; [t.join() for t in ts]
    assert len(calls) == 1 and s.evaluations == 1 and len({id(o) for o in outs}) == 1 and len(outs) == 16

def test_reentrant_call_for_same_identity_is_refused_not_double_evaluated():
    s = V.FinalResolutionStore(); calls = []
    def ev():
        calls.append(1)
        with pytest.raises(Refusal): s.resolve("inner", IDN, ev)                         # re-entry refused
        return "final"
    assert s.resolve("outer", IDN, ev) == "final" and len(calls) == 1
    assert s.resolve("again", IDN, ev) == "final" and len(calls) == 1

def test_failed_or_none_evaluation_stores_nothing_and_is_not_a_final_outcome():
    s = V.FinalResolutionStore()
    def boom(): raise RuntimeError("x")
    with pytest.raises(RuntimeError): s.resolve("r", IDN, boom)
    s.late_dependency_mutates(IDN)                                                       # nothing stored: window still open
    with pytest.raises(Refusal): s.resolve("r", IDN, lambda: None)                       # None is refused, not stored
    s.late_dependency_mutates(IDN)
    assert s.resolve("r", IDN, lambda: "ok") == "ok" and s.evaluations == 3              # a later good call can still resolve
    assert s.resolve("r2", IDN, lambda: "other") == "ok"

def test_inflight_marker_cleared_after_failure():
    s = V.FinalResolutionStore()
    with pytest.raises(RuntimeError): s.resolve("r", IDN, lambda: (_ for _ in ()).throw(RuntimeError("x")))
    assert s.resolve("r", IDN, lambda: 1) == 1                                           # not stuck REENTRANT

# ---------- review R05 (Codex PR#29): request-id reservation across in-flight / nested evaluation -------------------------
A_ID = V.FinalResolutionIdentity("C", "M", "S", "a")
B_ID = V.FinalResolutionIdentity("C", "M", "S", "b")

def test_nested_same_request_different_identity_is_refused_and_cannot_rebind():
    s = V.FinalResolutionStore(); seen = []
    def outer():
        try: s.resolve("same-request", B_ID, lambda: "B")
        except Refusal as e: seen.append(e.code)
        return "A"
    assert s.resolve("same-request", A_ID, outer) == "A"
    assert seen == ["REQUEST_ID_REBOUND_TO_OTHER_IDENTITY"]
    assert B_ID not in s._by_identity                                                    # inner never stored
    assert s._req_ids[("C", "same-request")] == A_ID                                            # binding not overwritten
    with pytest.raises(Refusal): s.resolve("same-request", B_ID, lambda: "B")            # retry for b still refused (a owns it)
    assert s.resolve("same-request", A_ID, lambda: "X") == "A"

def test_nested_rebind_attempt_propagating_failure_leaves_no_binding_created_by_failed_call():
    s = V.FinalResolutionStore()
    with pytest.raises(Refusal): s.resolve("rq", A_ID, lambda: s.resolve("rq", B_ID, lambda: "B"))   # inner refusal escapes outer
    assert "rq" not in s._req_ids and A_ID not in s._by_identity and B_ID not in s._by_identity
    assert s.resolve("rq", B_ID, lambda: "B") == "B"                                      # request id is usable again, by b

def test_failure_after_inner_success_on_other_request_keeps_inner_final_and_releases_outer():
    s = V.FinalResolutionStore()
    def outer():
        assert s.resolve("inner-req", B_ID, lambda: "B") == "B"                         # different request AND identity: legal
        raise RuntimeError("outer fails after inner success")
    with pytest.raises(RuntimeError): s.resolve("outer-req", A_ID, outer)
    assert s._by_identity == {B_ID: "B"} and "outer-req" not in s._req_ids               # a stored nothing; b's own final outcome stands
    assert s.resolve("outer-req", A_ID, lambda: "A2") == "A2"

def test_failure_does_not_drop_a_binding_that_pre_existed():
    s = V.FinalResolutionStore(); assert s.resolve("r", A_ID, lambda: "A") == "A"
    assert s.resolve("r", A_ID, lambda: 1 / 0) == "A"                                    # stored outcome returned, evaluator unused
    assert s._req_ids[("C", "r")] == A_ID

def test_second_thread_with_same_request_other_identity_is_refused_while_first_is_inside_evaluator():
    s = V.FinalResolutionStore(); entered, release, res = threading.Event(), threading.Event(), {}
    def ev(): entered.set(); assert release.wait(5); return "A"
    t1 = threading.Thread(target=lambda: res.setdefault("a", s.resolve("rq", A_ID, ev)))
    t1.start(); assert entered.wait(5)                                                  # evaluator-entry barrier: t1 IS inside evaluate()
    def other():
        try: s.resolve("rq", B_ID, lambda: "B")
        except Refusal as e: res["b"] = e.code
    t2 = threading.Thread(target=other); t2.start(); time.sleep(0.05); release.set(); t1.join(5); t2.join(5)
    assert res == {"a": "A", "b": "REQUEST_ID_REBOUND_TO_OTHER_IDENTITY"} and B_ID not in s._by_identity

def test_second_thread_same_identity_inside_evaluator_waits_and_gets_stored_outcome():
    s = V.FinalResolutionStore(); entered, release, outs = threading.Event(), threading.Event(), []
    def ev(): entered.set(); assert release.wait(5); return object()
    t1 = threading.Thread(target=lambda: outs.append(s.resolve("r1", A_ID, ev))); t1.start(); assert entered.wait(5)
    t2 = threading.Thread(target=lambda: outs.append(s.resolve("r2", A_ID, ev))); t2.start(); time.sleep(0.05)
    release.set(); t1.join(5); t2.join(5)
    assert s.evaluations == 1 and len(outs) == 2 and outs[0] is outs[1]
