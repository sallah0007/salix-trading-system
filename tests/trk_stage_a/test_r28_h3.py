import dataclasses, pytest
from stage_a.gateway import outcome_series as H
from stage_a.errors import Refusal

def pkg(**k):
    d = dict(consumer_binding_id="B1", series_id="S", series_version_or_hash="v1", observation_time_origin="O", horizon_id="H", horizon_version="1", dependency_interval_start=10, dependency_interval_end=20,
             authorized_segment_set_or_stage="SEG1", consumer_stage="TRAIN", outcome_package_hash="h", available_asof=5, delivery_decision_ts=30); d.update(k); return H.OutcomeSeriesPackage(**d)
def ctx(**k):
    d = dict(authorized_segments=((0, 25),)); d.update(k); return H.DeliveryContext(**d)

def test_positive_control_inside_authorized_segment():
    assert H.evaluate(pkg(), ctx()).delivered
def test_every_required_field_missing_withholds():
    for f in H.REQUIRED + ("dependency_interval_start", "dependency_interval_end", "available_asof", "delivery_decision_ts"):
        d = H.evaluate(dataclasses.replace(pkg(), **{f: None}), ctx()); assert not d.delivered and any(f in r for r in d.reasons), f
def test_interval_crossing_unauthorized_next_segment_or_gap_withholds():
    assert "INTERVAL_OUTSIDE_AUTHORIZED_SEGMENTS" in H.evaluate(pkg(dependency_interval_end=26), ctx()).reasons          # one tick into the unauthorized next segment
    assert not H.evaluate(pkg(dependency_interval_start=10, dependency_interval_end=20), ctx(authorized_segments=((0, 14), (16, 25)))).delivered   # gap at 15
    assert H.evaluate(pkg(), ctx(authorized_segments=((0, 14), (15, 25)))).delivered                                                              # adjacent segments are contiguous: positive control
    assert "INTERVAL_INVERTED" in H.evaluate(pkg(dependency_interval_start=20, dependency_interval_end=10), ctx()).reasons
def test_sealed_holdout_needs_unseal_ref_and_unrelated_interval_is_unaffected():
    c = ctx(authorized_segments=((0, 100),), sealed_holdout_intervals=((50, 80),))
    assert "SEALED_HOLDOUT_WITHOUT_UNSEAL_EVENT_REF" in H.evaluate(pkg(dependency_interval_start=40, dependency_interval_end=55), c).reasons
    assert H.evaluate(pkg(dependency_interval_start=40, dependency_interval_end=55, holdout_unseal_event_ref="U1"), c).delivered
    assert H.evaluate(pkg(dependency_interval_start=10, dependency_interval_end=20), c).delivered                       # does not touch the holdout: positive control
def test_conditional_references_only_where_applicable():
    for flag, ref in H.CONDITIONAL:
        assert H.evaluate(pkg(), ctx()).delivered                                                                          # not applicable: absent ref is fine
        assert "MISSING_CONDITIONAL:" + ref in H.evaluate(pkg(), ctx(**{flag: True})).reasons
        assert H.evaluate(pkg(**{ref: "R"}), ctx(**{flag: True})).delivered
def test_available_asof_must_precede_decision_and_malformed_context_is_refused():
    assert "AVAILABLE_ASOF_NOT_BEFORE_DECISION" in H.evaluate(pkg(available_asof=30), ctx()).reasons
    with pytest.raises(Refusal): H.evaluate(pkg(), ctx(authorized_segments=((5, 1),)))
    with pytest.raises(Refusal): H.evaluate(pkg(), H.DeliveryContext(authorized_segments=((0, 9),), stage_advance_applies="yes"))
    with pytest.raises(Refusal): H.evaluate({}, ctx())
    with pytest.raises(Refusal) as e: H.require_delivery(pkg(dependency_interval_end=26), ctx())
    assert e.value.code == "H3_DELIVERY_WITHHELD"

def test_fw_receive_outcome_series_callpath_and_sealed_independent_of_segments():
    from stage_a.fw import receiver as FW
    assert FW.receive_outcome_series(pkg(), ctx()).delivered
    with pytest.raises(Refusal): FW.receive_outcome_series(pkg(dependency_interval_end=26), ctx())
    r = H.evaluate(pkg(dependency_interval_start=40, dependency_interval_end=55), ctx(authorized_segments=((0, 100),), sealed_holdout_intervals=((50, 80),))).reasons
    assert r == ("SEALED_HOLDOUT_WITHOUT_UNSEAL_EVENT_REF",)
    both = H.evaluate(pkg(dependency_interval_start=40, dependency_interval_end=55), ctx(authorized_segments=((0, 45),), sealed_holdout_intervals=((50, 80),))).reasons
    assert set(both) == {"INTERVAL_OUTSIDE_AUTHORIZED_SEGMENTS", "SEALED_HOLDOUT_WITHOUT_UNSEAL_EVENT_REF"}
