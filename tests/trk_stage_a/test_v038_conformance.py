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
