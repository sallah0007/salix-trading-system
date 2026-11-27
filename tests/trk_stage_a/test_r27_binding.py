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
