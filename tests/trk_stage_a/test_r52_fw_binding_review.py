"""R52: the reviewable statement of what each FW ten-field real binding still needs. Documentary; produces no value."""
from stage_a.fw import descriptor_crosswalk as X
def test_every_field_is_reviewable_and_none_is_declared():
    rows = X.binding_declaration_review(); assert [r["field"] for r in rows] == list(X.FIELDS) and len(rows) == 10
    assert all(r["actual_payload_binding"] == "NULL" and r["missing"] and r["source_relation"] for r in rows)
def test_held_fields_are_not_closable_by_a_binding():
    by = {r["field"]: r for r in X.binding_declaration_review()}
    for f in ("SEGMENT_REF", "KNOWABLE_AT", "ADMISSIBILITY_STATE"): assert by[f]["classification"] == "NOT_CLOSABLE_BY_BINDING", f
    for f in ("OBSERVATION_REF", "VINTAGE_REF", "DEPENDENCY_INTERVAL_START", "HORIZON_ID", "AUTHORIZED_SEGMENT_SET"): assert by[f]["classification"] == "CLOSABLE_BY_BINDING_DECLARATION", f
def test_a_supplied_binding_never_closes_a_held_field_and_shape_is_not_admission():
    good = {k: "x" for k in ("scope", "interface_id", "version", "source_authority", "acceptance_record", "validity/supersession")}; good["content_hash"] = "a" * 64
    rows = {r["field"]: r for r in X.binding_declaration_review({f: good for f in X.FIELDS})}
    assert rows["KNOWABLE_AT"]["classification"] == "NOT_CLOSABLE_BY_BINDING" and rows["KNOWABLE_AT"]["actual_payload_binding"] == "NULL"
    assert rows["HORIZON_ID"]["actual_payload_binding"] == "DECLARED_SHAPE_ONLY" and rows["HORIZON_ID"]["missing"] == ["exact payload key naming where the value lives in the delivered payload"]
def test_review_can_fail_if_a_status_is_reclassified():
    old = X.SOURCE_STATUS["KNOWABLE_AT"]
    try:
        X.SOURCE_STATUS["KNOWABLE_AT"] = X.DIRECT_SCHEMA_FIELD_NOT_INSTANCE
        assert {r["field"]: r for r in X.binding_declaration_review()}["KNOWABLE_AT"]["classification"] == "CLOSABLE_BY_BINDING_DECLARATION"      # the control: the classification follows the status, so the test above can fail
    finally: X.SOURCE_STATUS["KNOWABLE_AT"] = old
