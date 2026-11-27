"""R08: E-06 principal table, routing-name reconciliation, Health aggregate/attribution invariants. Each protection has a mutant in
mutation_sweep_r08.py."""
import pytest
from stage_a.errors import Refusal
from stage_a.security import principals as P
from stage_a.composer import request_classification as R
from stage_a.tracker import quant_intake_adapter as A
from stage_a.health import envelope as H

def code(fn, *a):
    with pytest.raises(Refusal) as e: fn(*a)
    return e.value.code

def test_e06_has_exactly_the_ten_principals():
    assert set(P.E06) == {"composer-builder", "composer-refitter", "tracker-materializer", "tracker-verifier", "tracker-acceptor",
                          "context-writer", "gateway-writer", "health-writer", "scheduler", "replay-reader"}

def test_least_privilege_and_unknowns_fail_closed():
    P.authorize("tracker-acceptor", P.WRITE_HEAD_TRANSITION)
    assert code(P.authorize, "tracker-acceptor", P.WRITE_PENDING_CANDIDATE) == "CAPABILITY_NOT_GRANTED"     # cannot materialize
    assert code(P.authorize, "composer-builder", P.WRITE_HEAD_TRANSITION) == "CAPABILITY_NOT_GRANTED"
    assert code(P.authorize, "tracker-verifier", P.WRITE_HEAD_TRANSITION) == "CAPABILITY_NOT_GRANTED"
    assert code(P.authorize, "scheduler", P.WRITE_CANDIDATE) == "CAPABILITY_NOT_GRANTED"
    assert code(P.authorize, "root", P.READ_CANONICAL) == "UNKNOWN_PRINCIPAL"
    assert code(P.authorize, "tracker-acceptor", "ANYTHING_ELSE") == "CAPABILITY_NOT_GRANTED"

def test_r7_principals_are_refused_because_r7_is_not_operative():
    for p in ("acceptance-origin", "replica-commit-service"):
        assert code(P.capabilities, p) == "R7_PRINCIPAL_NOT_OPERATIVE"
        assert code(P.check_no_prohibited_merge, ["scheduler", p]) == "R7_PRINCIPAL_NOT_OPERATIVE"

def test_prohibited_merges_refused_and_allowed_bundles_pass():
    for a, b in P.PROHIBITED_MERGES:
        assert code(P.check_no_prohibited_merge, [a, b]) == "PROHIBITED_PRINCIPAL_MERGE"
    P.check_no_prohibited_merge(["tracker-materializer", "tracker-verifier"])      # not stated as prohibited
    P.check_no_prohibited_merge(["replay-reader", "scheduler"])
    assert code(P.check_no_prohibited_merge, ["tracker-acceptor", "nobody"]) == "UNKNOWN_PRINCIPAL"

def test_routing_names_reconcile_adapter_outcomes_and_tr06_never_maps_failure_to_none():
    assert R.route_from_adapter(A.QUANT_FEATURE) == R.COMPOSER_BUILT_QUANT_FEATURE
    assert R.route_from_adapter(A.NO_QUANT_FEATURE) == R.NO_QUANT_FEATURE
    assert code(R.route_from_adapter, A.FAILED_REQUESTED_BUILD) == "FAILED_BUILD_NOT_ROUTABLE"
    assert code(R.route_from_adapter, "SOMETHING") == "UNKNOWN_CLASSIFICATION"
    assert R.ROUTES == ("DIRECT_TRACKER_FEATURE", "COMPOSER_BUILT_QUANT_FEATURE", "NO_QUANT_FEATURE")

def test_aggregate_healthy_cannot_mask_a_critical_member():
    assert H.aggregate_state([("HEALTHY", True), ("HEALTHY", False)]) == "AGGREGATE_HEALTHY"
    assert H.aggregate_state([("HEALTHY", False), ("STALE", True)]) == "BLOCKED_BY_CRITICAL_MEMBER"
    assert H.aggregate_state([("STALE", False), ("HEALTHY", True)]) == "NON_CRITICAL_MEMBER_NOT_HEALTHY"
    assert H.aggregate_state([(None, True)]) == "BLOCKED_BY_CRITICAL_MEMBER"            # missing state is not healthy
    assert H.aggregate_state([("healthy", True)]) == "BLOCKED_BY_CRITICAL_MEMBER"       # no case-folding to HEALTHY
    assert H.aggregate_state([("healthy", False)]) == "NON_CRITICAL_MEMBER_NOT_HEALTHY"   # case drift is not HEALTHY
    assert H.aggregate_state([]) == "UNKNOWN"

def test_upstream_problem_is_not_a_local_failure_without_local_evidence():
    assert H.attribute_failure(False, True) == ("BLOCKED_BY_UPSTREAM",)
    assert H.attribute_failure(True, False) == ("LOCAL_FAILURE",)
    assert H.attribute_failure(True, True) == ("LOCAL_FAILURE", "BLOCKED_BY_UPSTREAM")      # coexisting causes are not merged (ML Health V2 s4)
    assert H.attribute_failure(False, False) == ("NO_FAILURE_ATTRIBUTED",)

from stage_a.fw import descriptor_crosswalk as X
GOOD = {"scope": "s", "interface_id": "i", "version": "1", "content_hash": "a" * 64, "source_authority": "a", "acceptance_record": "r",
        "validity/supersession": "v"}
def test_fw_descriptor_crosswalk_ten_fields_all_unbound_and_fail_closed():
    assert len(X.FIELDS) == 10 and set(X.FIELDS) == set(X.SOURCE_STATUS)
    for f in X.FIELDS: assert code(X.require_real_binding, f) == "UNDECLARED_REAL_PAYLOAD_BINDING"
    assert code(X.require_all) == "UNDECLARED_REAL_PAYLOAD_BINDING"
    assert code(X.source_status, "NOT_A_FIELD") == "UNKNOWN_DESCRIPTOR_FIELD"

def test_missing_or_internal_mappings_refused_even_if_a_binding_is_supplied_direct_ones_pass():
    b = {f: GOOD for f in X.FIELDS}
    for f in ("SEGMENT_REF", "KNOWABLE_AT", "ADMISSIBILITY_STATE"):
        assert code(X.require_real_binding, f, b) == "DERIVATION_NOT_VERIFIABLE"
    assert X.require_real_binding("HORIZON_ID", b) == GOOD and X.require_real_binding("OBSERVATION_REF", b) == GOOD
    assert code(X.require_all, b) == "DERIVATION_NOT_VERIFIABLE"
    assert code(X.require_real_binding, "HORIZON_ID", {**b, "HORIZON_ID": None}) == "UNDECLARED_REAL_PAYLOAD_BINDING"
