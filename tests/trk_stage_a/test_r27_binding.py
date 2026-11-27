import dataclasses, pytest
from stage_a.gateway import binding as B
from stage_a.schema import objects as O
from stage_a.errors import Refusal

def test_owner_reexports_exact_schema_object():
    assert B.DeliveredFeatureEntry is O.DeliveredFeatureEntry
    assert tuple(O.DeliveredFeatureEntry.__dataclass_fields__) == B.ANNEX_XII_FIELDS

def test_lookalike_entry_refused():
    @dataclasses.dataclass(frozen=True)
    class Look: feature_id: int = 1
    with pytest.raises(Refusal) as e: B.verify_delivered(None, Look(), b"")
    assert e.value.code == "NOT_THE_FROZEN_DELIVERED_ENTRY"

from tests.trk_stage_a.test_boundaries import _bound, T, I, J, H, R
from stage_a.fw import receiver as FW
from stage_a.ml import receiver as ML

def test_every_field_corruption_is_caught_by_independent_verification():
    gw, b = _bound(); B.verify_delivered(T, b.entry, b.delivered_feature_hash)       # positive control
    muts = dict(feature_id=J, feature_version="zz", quant_manifest_hash=bytes(32), instrument_id=J, timeframe_id=J, materialization_version="zz", step_index=99, event_time=12345,
                logical_encoding_version="zz", published_projection_name="zz", published_projection_bits=b"\x09" * 8, published_projection_hash=bytes(32), data_vintage_mode="EVENTUAL",
                available_asof=777, chain_status_at_bind="CATCHING_UP", bound_health_resolved_at=b.entry.bound_health_resolved_at + 1, omissions_exclusions_reason_codes=(("ENUM", "REASON", "NONE"),))
    for f, v in muts.items():
        if getattr(b.entry, f) == v: continue
        with pytest.raises(Refusal): B.verify_delivered(T, dataclasses.replace(b.entry, **{f: v}), b.delivered_feature_hash)
    with pytest.raises(Refusal): B.verify_delivered(T, b.entry, bytes(32))

def test_unknown_code_or_ref_type_is_refused_not_hashed():
    gw, b = _bound()
    with pytest.raises(Refusal) as e: B.verify_delivered(T, dataclasses.replace(b.entry, chain_status_at_bind="NOPE"), b.delivered_feature_hash)
    assert e.value.code == "ENUM_SYMBOL_NOT_IN_SUPPLIED_TABLE"

def test_ml_without_tables_fails_closed_unless_explicitly_unverified():
    gw, b = _bound()
    from tests.trk_stage_a.test_boundaries import _entry, NONE_
    with pytest.raises(Refusal) as e: ML.build_row("r", R("gen"), [_entry()], [b], gw, "ORIGINAL_AS_OBSERVED", NONE_, lambda o: NONE_)
    assert e.value.code == "DELIVERED_HASH_NOT_VERIFIABLE"
    assert ML.build_row("r", R("gen"), [_entry()], [b], gw, "ORIGINAL_AS_OBSERVED", NONE_, lambda o: NONE_, tables=T).included
    bad = dataclasses.replace(b, entry=dataclasses.replace(b.entry, available_asof=b.entry.available_asof + 1))
    with pytest.raises(Refusal) as e: FW.receive(bad, _entry(), I, I, T)               # shape-only path, no gateway: the hash check itself must catch it
    assert e.value.code == "HASH_MISMATCH"

def test_ml_verifies_hash_of_a_gateway_stored_binding_with_corrupt_entry():
    from tests.trk_stage_a.test_boundaries import _entry, NONE_
    gw, b = _bound(); bad = dataclasses.replace(b, entry=dataclasses.replace(b.entry, available_asof=b.entry.available_asof + 1)); gw._outcomes[bad.request_id] = bad   # the Gateway really stores this object
    with pytest.raises(Refusal) as e: ML.build_row("r", R("gen"), [_entry()], [bad], gw, "ORIGINAL_AS_OBSERVED", NONE_, lambda o: NONE_, tables=T)
    assert e.value.code == "HASH_MISMATCH"

def test_schema_drift_and_independent_refusal_are_refused():
    gw, b = _bound()
    old = B.ANNEX_XII_FIELDS
    try:
        B.ANNEX_XII_FIELDS = old[:-1]
        with pytest.raises(Refusal) as e: B.verify_delivered(T, b.entry, b.delivered_feature_hash)
        assert e.value.code == "DELIVERED_ENTRY_FIELDS_DIFFER_FROM_ANNEX"
    finally: B.ANNEX_XII_FIELDS = old
    with pytest.raises(Refusal) as e: B.verify_delivered(T, dataclasses.replace(b.entry, published_projection_bits=b"\x01"), b.delivered_feature_hash)     # wrong fixed width: the independent side refuses
    assert e.value.code == "DELIVERED_ENTRY_NOT_INDEPENDENTLY_COMPOSABLE"

def test_independent_composition_is_actually_the_verifier_path_under_producer_fault_injection(monkeypatch):
    """R29 E: if verify_delivered used the producer composition, faulting the producer would break (or, mirrored, mask) it. A genuine entry still verifies through the independent X path while the producer
    returns wrong bytes, and a changed bound-Health time still fails with HASH_MISMATCH."""
    gw, b = _bound(); good = b.delivered_feature_hash
    monkeypatch.setattr(O, "delivered_hash", lambda tables, d: b"\xde\xad" * 16)             # producer composition is now WRONG everywhere
    B.verify_delivered(T, b.entry, good)                                                       # independent path unaffected
    with pytest.raises(Refusal) as e: B.verify_delivered(T, dataclasses.replace(b.entry, bound_health_resolved_at=b.entry.bound_health_resolved_at + 1), good)
    assert e.value.code == "HASH_MISMATCH"
    with pytest.raises(Refusal) as e: B.verify_delivered(T, b.entry, b"\xde\xad" * 16)         # and the faulty producer's bytes are not accepted as the claimed hash
    assert e.value.code == "HASH_MISMATCH"
