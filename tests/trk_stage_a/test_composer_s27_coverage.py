"""Composer V9 §27 BUILD_OUTPUT_PACKAGE field coverage against stage_a.tracker.quant_intake_adapter.BuildPackage (D6).
Source: Composer V9 export §27 line 797 (field list read in full). This is a COVERAGE MAP, not a conformance claim:
DIRECT = same-named concept, CANDIDATE = plausible but unconfirmed mapping (needs Composer owner confirmation), ABSENT = no field."""
import dataclasses
from stage_a.tracker.quant_intake_adapter import BuildPackage

S27_FIELDS = [
 "CREATION_REQUEST_ID", "ORDER_ID", "CLAIM_ID", "REQUEST_SCHEMA_VERSION", "BUILDER_BUILD_ID", "request context",
 "purpose/hypothesis", "research mode", "PURPOSE_PROFILE_ID/HASH", "SIMULATION_OR_AUTHORITY_CLASS",
 "INSTRUMENT_PROFILE_ID/HASH", "SOURCE_CONFIG_ID/HASH", "BUILDER_VERSION/HASH", "TRACKER_CATALOG_SNAPSHOT_ID/HASH",
 "CATALOG_WATERMARK", "construction graph ID/hash", "exact input IDs/versions/hashes", "resolved feature identities/versions",
 "dependency graph/closures", "source/vintage/time semantics", "operation/grammar versions", "parameters",
 "search/candidate set/exclusions", "OUTCOME_INFORMATION_ACCESS declaration and fitting/holdout contract reference",
 "bounded materialization/query policy reference", "intermediate nodes/hashes", "fitted/learned state",
 "UPSTREAM_MODEL_ID and UPSTREAM_GENERATION_ID plus generation authority class", "missingness and quality behavior",
 "environment/code/config", "manifest ID/hash", "output hash", "BUILT_AT", "TEST/EVIDENCE REFERENCES",
 "warnings/unresolved constraints"]

DIRECT = {"CREATION_REQUEST_ID": "creation_request_id", "ORDER_ID": "order_id",
          "construction graph ID/hash": "declared_graph_hash", "manifest ID/hash": "declared_manifest_hash"}
CANDIDATE = {"BUILDER_BUILD_ID": "attempt_id",                  # R7 RD4a: per-attempt build id; R7 is NOT operative, V1 governs
             "purpose/hypothesis": "semantic_definition",        # unconfirmed
             "INSTRUMENT_PROFILE_ID/HASH": "expected_instrument",  # carries instrument/timeframe only, no profile id/hash
             "request context": "request_id"}                    # unconfirmed
ABSENT = [f for f in S27_FIELDS if f not in DIRECT and f not in CANDIDATE]

def test_map_covers_exactly_the_s27_list_and_names_real_attributes():
    assert len(S27_FIELDS) == 35 and len(set(S27_FIELDS)) == 35
    assert set(DIRECT) | set(CANDIDATE) <= set(S27_FIELDS) and not (set(DIRECT) & set(CANDIDATE))
    attrs = {f.name for f in dataclasses.fields(BuildPackage)}
    for src, a in {**DIRECT, **CANDIDATE}.items(): assert a in attrs, (src, a)

def test_absent_set_is_explicit_so_adding_a_field_forces_this_map_to_be_revisited():
    assert len(ABSENT) == 35 - len(DIRECT) - len(CANDIDATE) == 27
    for needed in ("CLAIM_ID", "TRACKER_CATALOG_SNAPSHOT_ID/HASH", "CATALOG_WATERMARK", "dependency graph/closures",
                   "OUTCOME_INFORMATION_ACCESS declaration and fitting/holdout contract reference",
                   "UPSTREAM_MODEL_ID and UPSTREAM_GENERATION_ID plus generation authority class", "BUILT_AT"):
        assert needed in ABSENT
    attrs = {f.name for f in dataclasses.fields(BuildPackage)}
    assert not ({"claim_id", "catalog_watermark", "upstream_model_id", "outcome_information_access"} & attrs)
