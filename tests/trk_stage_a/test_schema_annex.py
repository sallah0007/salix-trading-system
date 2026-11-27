"""Annex V1.2 byte-encoding and hash-coverage tests. Code tables here are PROVISIONAL test values (D3 open)."""
import pytest
from stage_a.errors import Refusal
from stage_a.schema import encoding as E, objects as O
from stage_a.schema.encoding import CodeTables, Ref

T = CodeTables(
    enums={"PROGRAM_CAPABILITY_CLASS": {"TRANSITION": 1, "PROJECTION": 2}, "REFIT_MODE": {"NONE": 1, "SCHEDULED_REFIT": 2},
           "SPECULATION_MODE": {"NONE": 1, "GATED_ONE_STEP": 2}, "CURRENTNESS_STATE": {"CURRENT": 1},
           "TRANSITION_STATUS_EVENT": {"CANONICAL_ACCEPTANCE": 1}, "CHAIN_STATUS": {"PUBLISHABLE": 1, "WITHDRAWN": 2},
           "DATA_VINTAGE_MODE": {"ORIGINAL_AS_OBSERVED": 1}, "REASON": {"NONE": 1}},
    ref_types={"PROGRAM": 1, "RULE": 2, "ROW": 3})
H = bytes(range(32)); I = bytes(range(16))
def R(n, h=None): return Ref("RULE", n.encode(), b"v1", h)

def test_primitives_golden():
    assert E.u16(258) == b"\x01\x02" and E.u32(1) == b"\x00\x00\x00\x01"
    assert E.i64(-1) == b"\xff" * 8 and E.boolean(True) == b"\x01"
    assert E.version_id("ab") == b"\x00\x00\x00\x02ab"
    assert E.optional(None) == b"\x00" and E.optional(b"\x07") == b"\x01\x07"
    assert E.ref(T, R("x")) == b"\x00\x02" + b"\x00\x00\x00\x01x" + b"\x00\x00\x00\x02v1" + b"\x00"
    assert E.ref(T, R("x", H)).endswith(b"\x01" + H)

@pytest.mark.parametrize("bad", [True, -1, 65536, 1.0, "1"])
def test_u16_refuses(bad):
    with pytest.raises(Refusal): E.u16(bad)

def test_fixed_width_refusals():
    for f, n in ((E.id128, 15), (E.hash256, 31), (E.binary64_bits, 7)):
        with pytest.raises(Refusal): f(b"\0" * n)
    with pytest.raises(Refusal): E.version_id("")
    with pytest.raises(Refusal): E.version_id("x" * 129)
    with pytest.raises(Refusal): E.boolean(1)

def test_unknown_codes_refuse():
    with pytest.raises(Refusal): E.enum(T, "REFIT_MODE", "NOPE")
    with pytest.raises(Refusal): E.ref(T, Ref("BOGUS", b"a"))

def test_provisional_flag():
    assert T.provisional and not CodeTables({}, {}, admitted_source="X").provisional

def test_sort_keyed_orders_and_refuses_duplicates():
    assert O.sort_keyed([(b"b", 2), (b"a", 1)], "k") == [1, 2]
    with pytest.raises(Refusal): O.sort_keyed([(b"a", 1), (b"a", 2)], "k")

def manifest(**kw):
    r = lambda n: R(n)
    base = dict(quant_manifest_schema_version="1", feature_id=I, feature_version="f1", model_profile_id="p", model_profile_version="1",
        state_schema_version="s1", parameter_schema_version="ps1", arithmetic_contract_version="a1", logical_encoding_version="l1",
        shared_evaluator_operator_set_version="SQE_OPSET_V1_1", refit_mode="NONE", refit_rule_ref=None, parameter_generation_source_ref=None,
        initialization_rule_set_ref=r("init"), step_class_set_ref=r("sc"), step_classifier_ref=r("cl"),
        input_dependencies=(("in_b", r("b")), ("in_a", r("a"))), transition_program_refs=(("t1", r("t")),),
        projection_program_refs=(("p1", r("p")),), invariant_program_refs=(("i1", r("i")),),
        published_projection_set_ref=r("pps"), verification_rule_set_ref=r("vr"), golden_vector_set_ref=r("gv"),
        health_profile_ref=r("hp"), health_metric_program_refs=(), program_capability_declarations=(
            O.ProgramCapability(Ref("PROGRAM", b"p2"), "PROJECTION", (1, 2), r("rc")),
            O.ProgramCapability(Ref("PROGRAM", b"p1"), "TRANSITION", (3,), r("rc"))),
        resource_ceiling_ref=r("rc"), data_vintage_policy_ref=r("dv"))
    base.update(kw); return O.QuantManifest(**base)

def test_manifest_hash_is_order_insensitive_for_keyed_lists():
    a = manifest(); b = manifest(input_dependencies=(("in_a", R("a")), ("in_b", R("b"))),
        program_capability_declarations=tuple(reversed(a.program_capability_declarations)))
    assert O.manifest_hash(T, a) == O.manifest_hash(T, b)

def test_manifest_hash_sensitive_to_every_field_class():
    base = O.manifest_hash(T, manifest())
    assert O.manifest_hash(T, manifest(feature_version="f2")) != base
    assert O.manifest_hash(T, manifest(input_dependencies=(("in_a", R("a")), ("in_b", R("b2"))))) != base

def test_manifest_refusals():
    with pytest.raises(Refusal): O.manifest_bytes(T, manifest(shared_evaluator_operator_set_version="SQE_OPSET_V1_0"))
    with pytest.raises(Refusal): O.manifest_bytes(T, manifest(refit_mode="SCHEDULED_REFIT"))
    with pytest.raises(Refusal): O.manifest_bytes(T, manifest(refit_mode="NONE", refit_rule_ref=R("x")))
    with pytest.raises(Refusal): O.manifest_bytes(T, manifest(input_dependencies=()))
    with pytest.raises(Refusal): O.manifest_bytes(T, manifest(input_dependencies=(("a", R("a")), ("a", R("b")))))
    bad = O.ProgramCapability(Ref("PROGRAM", b"p"), "PROJECTION", (2, 1), R("rc"))
    with pytest.raises(Refusal): O.manifest_bytes(T, manifest(program_capability_declarations=(bad,)))

def row(**kw):
    base = dict(feature_id=I, feature_version="f1", quant_manifest_hash=H, instrument_id=I, timeframe_id=I, materialization_version="m1",
        step_index=0, event_time=1000, state_schema_version="s1", logical_encoding_version="l1", arithmetic_contract_version="a1",
        state_tuple=b"st", published_projection_name="p1", published_projection_bits=b"\0" * 8,
        input_refs_and_hashes=((Ref("ROW", b"i1"), H),), fit_generation_ref=None, step_class_ref=R("sc"),
        predecessor_row_hash=None, state_origin_ref=R("origin"), speculation_mode="NONE", gate_dependency_hash=None,
        materializer_implementation_id=I)
    base.update(kw); return O.PendingRow(**base)

def test_row_origin_xor_predecessor():
    O.row_content_bytes(T, row())
    O.row_content_bytes(T, row(predecessor_row_hash=H, state_origin_ref=None))
    with pytest.raises(Refusal): O.row_content_bytes(T, row(predecessor_row_hash=H))
    with pytest.raises(Refusal): O.row_content_bytes(T, row(state_origin_ref=None))

def test_row_gate_presence_and_inputs():
    with pytest.raises(Refusal): O.row_content_bytes(T, row(speculation_mode="GATED_ONE_STEP"))
    with pytest.raises(Refusal): O.row_content_bytes(T, row(gate_dependency_hash=H))
    O.row_content_bytes(T, row(speculation_mode="GATED_ONE_STEP", gate_dependency_hash=H))
    with pytest.raises(Refusal): O.row_content_bytes(T, row(input_refs_and_hashes=()))

def test_row_input_order_is_significant():
    a = ((Ref("ROW", b"1"), H), (Ref("ROW", b"2"), H))
    assert O.row_content_hash(T, row(input_refs_and_hashes=a)) != O.row_content_hash(T, row(input_refs_and_hashes=a[::-1]))

def test_row_hash_binds_every_scalar():
    b = O.row_content_hash(T, row())
    for kw in (dict(step_index=1), dict(event_time=1001), dict(state_tuple=b"sx"), dict(published_projection_bits=b"\1" * 8)):
        assert O.row_content_hash(T, row(**kw)) != b

def test_transition_asof_equals_acceptance():
    c = dict(row_content_hash=H, verification_evidence_ref=R("v"), sifp_fencing_epoch=1, canonical_commit_point_id=I,
             canonical_accepted_at=5, available_asof=5, gate_dependency_transition_ref=None,
             currentness_state_at_acceptance="CURRENT", status_event="CANONICAL_ACCEPTANCE")
    O.transition_hash(T, O.CanonicalTransition(**c))
    c["available_asof"] = 6
    with pytest.raises(Refusal): O.transition_bytes(T, O.CanonicalTransition(**c))

def status(**kw):
    base = dict(status_event_id=I, feature_version="f1", instrument_id=I, timeframe_id=I, materialization_version="m1",
        mv_status_sequence=1, status_event_type="PUBLISHABLE", effective_from=("STEP", 3), reason_code=("ENUM", "REASON", "NONE"),
        predecessor_or_successor_mv_ref=None, available_asof=9, evidence_ref=R("e"), sifp_fencing_epoch=1, correction_marked=False)
    base.update(kw); return O.StatusEvent(**base)

def test_status_effective_from_union():
    assert O.status_event_hash(T, status()) != O.status_event_hash(T, status(effective_from=("INTERVAL", 3, 4)))
    with pytest.raises(Refusal): O.status_event_bytes(T, status(effective_from=("INTERVAL", 4, 4)))
    with pytest.raises(Refusal): O.status_event_bytes(T, status(effective_from=("BAD", 1)))
    with pytest.raises(Refusal): O.status_event_bytes(T, status(reason_code=("NOPE",)))

def test_status_correction_flag_binds():
    assert O.status_event_hash(T, status()) != O.status_event_hash(T, status(correction_marked=True))

def test_delivered_entry_binds_vintage_and_reasons():
    d = dict(feature_id=I, feature_version="f1", quant_manifest_hash=H, instrument_id=I, timeframe_id=I, materialization_version="m1",
        step_index=0, event_time=1, logical_encoding_version="l1", published_projection_name="p1", published_projection_bits=b"\0" * 8,
        published_projection_hash=H, fit_generation_ref=None, data_vintage_mode="ORIGINAL_AS_OBSERVED", available_asof=2,
        chain_status_at_bind="PUBLISHABLE", source_or_causal_policy_ref=R("p"), bound_health_resolution_ref=R("h"),
        bound_health_resolved_at=2, canonical_transition_ref=R("t"), omissions_exclusions_reason_codes=())
    b = O.delivered_hash(T, O.DeliveredFeatureEntry(**d))
    d["omissions_exclusions_reason_codes"] = (("ENUM", "REASON", "NONE"),)
    assert O.delivered_hash(T, O.DeliveredFeatureEntry(**d)) != b
