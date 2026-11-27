import dataclasses, pytest
from stage_a.gateway import outcome_series as H
from stage_a.errors import Refusal

def pkg(**k):
    d = dict(consumer_binding_id="B1", series_id="S", series_version_or_hash="v1", observation_time_origin="O", horizon_id="H", horizon_version="1", dependency_interval_start=10, dependency_interval_end=20,
             authorized_segment_set_or_stage="SEG1", consumer_stage="TRAIN", outcome_package_hash="h", available_asof=5, delivery_decision_ts=30); d.update(k); return H.OutcomeSeriesPackage(**d)
def ctx(**k):
    d = dict(authorized_segments=((0, 25),), sealed_holdout_intervals=(), valid_unseal_event_refs=frozenset(), stage_advance_applies=False, research_exposure_material=False, family_state_evaluated=False, purge_embargo_required=False); d.update(k); return H.DeliveryContext(**d)
st = lambda p, c: H.evaluate(p, c).status

def test_positive_control_and_never_authorized_delivery():
    d = H.evaluate(pkg(), ctx()); assert d.status == H.PASS_STRUCTURAL and d.structurally_passes and d.authorized_delivery is False
def test_missing_knowledge_is_never_read_as_not_applicable_or_no_sealed_region():
    assert st(pkg(), H.DeliveryContext(authorized_segments=((0, 25),), sealed_holdout_intervals=())) == H.UNDETERMINED                         # applicability flags unknown
    r = H.evaluate(pkg(), ctx(sealed_holdout_intervals=None)).reasons; assert "SEALED_REGIONS_NOT_SUPPLIED" in r
    r = H.evaluate(pkg(), ctx(authorized_segments=None)).reasons; assert "AUTHORIZED_SEGMENTS_NOT_SUPPLIED" in r
    for flag, _ in H.CONDITIONAL: assert "APPLICABILITY_UNKNOWN:" + flag in H.evaluate(pkg(), ctx(**{flag: None})).reasons
def test_every_required_field_missing_withholds():
    for f in H.REQUIRED + ("dependency_interval_start", "dependency_interval_end", "available_asof", "delivery_decision_ts"):
        d = H.evaluate(dataclasses.replace(pkg(), **{f: None}), ctx()); assert d.status == H.WITHHELD and any(f in r for r in d.reasons), f
def test_boundary_convention_is_not_selected_by_the_implementation():
    adj = ctx(authorized_segments=((0, 14), (15, 25)))                          # adjacent segments: contiguous only under DISCRETE_TICK
    d = H.evaluate(pkg(), adj); assert d.status == H.UNDETERMINED and "UNDETERMINED_BOUNDARY_CONVENTION:segments" in d.reasons
    assert st(pkg(), dataclasses.replace(adj, boundary_convention="DISCRETE_TICK")) == H.PASS_STRUCTURAL                 # caller-labelled convention used, never defaulted
    assert st(pkg(), dataclasses.replace(adj, boundary_convention="CLOSED_CONTINUOUS")) == H.WITHHELD
    assert st(pkg(), ctx(authorized_segments=((0, 100),))) == H.PASS_STRUCTURAL                                          # convention-independent inside: positive
    assert st(pkg(dependency_interval_end=40), ctx()) == H.WITHHELD                                                      # convention-independent outside
    assert "INTERVAL_INVERTED" in H.evaluate(pkg(dependency_interval_start=20, dependency_interval_end=10), ctx()).reasons
    with pytest.raises(Refusal): H.evaluate(pkg(), ctx(boundary_convention="MINE"))
def test_interval_ending_exactly_at_segment_end_is_boundary_dependent_not_silently_closed():
    assert st(pkg(dependency_interval_end=25), ctx(authorized_segments=((0, 25),))) == H.PASS_STRUCTURAL                 # covered under every convention (reach >= e)
    assert st(pkg(dependency_interval_end=26), ctx(authorized_segments=((0, 25),))) == H.WITHHELD
def test_sealed_holdout_needs_a_resolved_unseal_event_not_a_string():
    c = ctx(authorized_segments=((0, 100),), sealed_holdout_intervals=((50, 80),))
    p = pkg(dependency_interval_start=40, dependency_interval_end=55)
    assert "SEALED_HOLDOUT_WITHOUT_UNSEAL_EVENT_REF" in H.evaluate(p, c).reasons
    pu = pkg(dependency_interval_start=40, dependency_interval_end=55, holdout_unseal_event_ref="U1")
    assert H.evaluate(pu, c).reasons == ("UNSEAL_EVENT_REF_NOT_RESOLVED",)                                               # 'U1' is not in the (empty) resolver set
    assert st(pu, dataclasses.replace(c, valid_unseal_event_refs=frozenset({"U1"}))) == H.PASS_STRUCTURAL
    assert "UNSEAL_RESOLUTION_INPUT_NOT_SUPPLIED" in H.evaluate(pu, dataclasses.replace(c, valid_unseal_event_refs=None)).reasons
    assert st(pkg(), c) == H.PASS_STRUCTURAL                                                                             # does not touch the holdout: unrelated positive
    edge = pkg(dependency_interval_start=30, dependency_interval_end=50)                                                   # touches the sealed start only at the boundary
    assert st(edge, c) == H.UNDETERMINED                                                                                 # half-open says no overlap, closed says overlap
def test_conditional_references_only_where_applicable():
    for flag, ref in H.CONDITIONAL:
        assert st(pkg(), ctx()) == H.PASS_STRUCTURAL
        assert "MISSING_CONDITIONAL:" + ref in H.evaluate(pkg(), ctx(**{flag: True})).reasons
        assert st(pkg(**{ref: "R"}), ctx(**{flag: True})) == H.PASS_STRUCTURAL
def test_available_asof_and_malformed_inputs():
    assert "AVAILABLE_ASOF_NOT_BEFORE_DECISION" in H.evaluate(pkg(available_asof=30), ctx()).reasons
    with pytest.raises(Refusal): H.evaluate(pkg(), ctx(authorized_segments=((5, 1),)))
    with pytest.raises(Refusal): H.evaluate(pkg(), ctx(stage_advance_applies="yes"))
    with pytest.raises(Refusal): H.evaluate({}, ctx())
def test_fw_receipt_is_structural_only_and_raises_on_withheld_or_undetermined():
    from stage_a.fw import receiver as FW
    assert FW.receive_outcome_series(pkg(), ctx()).authorized_delivery is False
    for p, c in ((pkg(dependency_interval_end=40), ctx()), (pkg(), ctx(authorized_segments=((0, 14), (15, 25)))), (pkg(), H.DeliveryContext())):
        with pytest.raises(Refusal) as e: FW.receive_outcome_series(p, c)
        assert e.value.code == "H3_DELIVERY_WITHHELD_OR_UNDETERMINED"
