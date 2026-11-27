"""R10: R7 s3 isolated-replica role lookup (R7 s1-6 CURRENT conditional design source, Matrix change set 01). Design lookup only."""
import pytest
from stage_a.errors import Refusal
from stage_a.security import principals as P
def code(fn, *a):
    with pytest.raises(Refusal) as e: fn(*a)
    return e.value.code
def test_origin_cannot_write_head_and_commit_service_cannot_originate():
    o, c = P.replica_capabilities("acceptance-origin"), P.replica_capabilities("replica-commit-service")
    assert P.WRITE_HEAD_TRANSITION not in o and P.WRITE_HEAD_TRANSITION in c
    assert c == {P.WRITE_HEAD_TRANSITION} and o == {P.WRITE_ACCEPTANCE_EVIDENCE}
    assert not (o & c)
    for forbidden in (P.WRITE_PENDING_CANDIDATE, P.WRITE_VERIFICATION_EVIDENCE, P.WRITE_ACCEPTANCE_EVIDENCE):   # materialize / verify / originate
        assert forbidden not in c
    assert P.WRITE_PENDING_CANDIDATE not in o
def test_no_replica_role_inherits_acceptor_head_write_by_rename_and_status_event_is_unassigned():
    holders = [r for r, caps in P.REPLICA_ROLES.items() if P.WRITE_HEAD_TRANSITION in caps]
    assert holders == ["replica-commit-service"]
    assert all(P.WRITE_STATUS_EVENT not in caps for caps in P.REPLICA_ROLES.values())      # R7 silent: open decision, not invented
    assert code(P.replica_capabilities, "tracker-acceptor") == "REPLICA_ACCEPTOR_SPLIT_REQUIRED"
    assert code(P.replica_capabilities, "root") == "UNKNOWN_PRINCIPAL"
def test_carried_principals_equal_e06_and_e06_acceptor_unchanged_outside_replica():
    for k in set(P.E06) - {"tracker-acceptor"}: assert P.replica_capabilities(k) == P.E06[k]
    assert P.E06["tracker-acceptor"] == {P.WRITE_HEAD_TRANSITION, P.WRITE_STATUS_EVENT} and len(P.E06) == 10
    assert P.DESIGN_LOOKUP_NOT_AUTHORIZATION is True
def test_replica_merge_prohibitions():
    assert code(P.replica_check_no_prohibited_merge, ["acceptance-origin", "replica-commit-service"]) == "PROHIBITED_PRINCIPAL_MERGE"
    for r in ("acceptance-origin", "replica-commit-service"):
        for o in ("tracker-materializer", "composer-builder", "composer-refitter", "tracker-verifier"):
            assert code(P.replica_check_no_prohibited_merge, [r, o]) == "PROHIBITED_PRINCIPAL_MERGE"
    assert code(P.replica_check_no_prohibited_merge, ["tracker-acceptor"]) == "REPLICA_ACCEPTOR_SPLIT_REQUIRED"
    P.replica_check_no_prohibited_merge(["acceptance-origin", "scheduler"])
    P.replica_check_no_prohibited_merge(["tracker-materializer", "tracker-verifier"])

# ---- Composer s7A APPEND request record -----------------------------------------------------------------------------------------------
from stage_a.composer import request_record as RR
REC = {"REQUEST_SCHEMA_VERSION": "1", "REQUESTER_TYPE": "OWNER", "REQUESTER_ID": "r1", "REQUEST_CLASS": "GOVERNED_INTAKE_REQUEST",
       "TARGET_CONSUMER": "FORWARD_WALK", "REQUEST_CONTEXT": "MANUAL_CHECKUP", "PURPOSE_STATEMENT": "p", "OUTCOME_INFORMATION_ACCESS": "FORBIDDEN"}
def test_request_record_ok_and_enum_refusals():
    assert RR.check_request_record(dict(REC), "ORDER") == "OK"
    for k, bad in (("REQUESTER_TYPE", "ROOT"), ("REQUEST_CLASS", "ML_DATASET_OR_MODEL_REQUEST"), ("REQUEST_CLASS", "DIAGNOSTIC_REQUEST"),
                   ("TARGET_CONSUMER", "ANY"), ("REQUEST_CONTEXT", "SIMULATION_OR_TEST"), ("REQUEST_CONTEXT", "UNKNOWN")):
        assert code(RR.check_request_record, {**REC, k: bad}, "ORDER") == "REQUEST_ENUM_VALUE_NOT_IN_SOURCE_LIST"
    assert code(RR.check_request_record, dict(REC), "LATER") == "REQUEST_STAGE_UNKNOWN"
    assert code(RR.check_request_record, [], "ORDER") == "REQUEST_NOT_A_RECORD"
def test_request_record_field_rules():
    for k in ("REQUEST_SCHEMA_VERSION", "REQUESTER_ID"):
        assert code(RR.check_request_record, {**REC, k: " "}, "PROPOSAL") == "REQUEST_FIELD_MISSING"
    sb = {**REC, "REQUEST_CLASS": "STREAM_B_EXPLORATION_REQUEST"}
    assert code(RR.check_request_record, sb, "ORDER") == "STREAM_B_ORIGIN_NOT_FORWARD_WALK"
    assert code(RR.check_request_record, {**sb, "REQUEST_ORIGIN": "OWNER"}, "ORDER") == "STREAM_B_ORIGIN_NOT_FORWARD_WALK"
    assert RR.check_request_record({**sb, "REQUEST_ORIGIN": "FORWARD_WALK"}, "ORDER") == "OK"
    assert code(RR.check_request_record, {**REC, "REQUEST_CONTEXT": "OTHER"}, "PROPOSAL") == "REQUEST_OTHER_WITHOUT_GOVERNED_REASON"
    assert code(RR.check_request_record, {**REC, "REQUESTER_TYPE": "OTHER_GOVERNED_PROCESS"}, "PROPOSAL") == "REQUEST_OTHER_WITHOUT_GOVERNED_REASON"
    assert RR.check_request_record({**REC, "REQUEST_CONTEXT": "OTHER", "GOVERNED_REASON": "r"}, "PROPOSAL") == "OK"
    assert code(RR.check_request_record, {**REC, "REQUEST_CONTEXT": "CORRECTION"}, "PROPOSAL") == "REQUEST_CORRECTION_WITHOUT_EVIDENCE_REF"
    assert RR.check_request_record({**REC, "REQUEST_CONTEXT": "CORRECTION", "DEFECT_EVIDENCE_REF": "d"}, "PROPOSAL") == "OK"
def test_request_record_stage_rules():
    unk = {**REC, "TARGET_CONSUMER": "UNKNOWN"}
    assert RR.check_request_record(unk, "PROPOSAL") == "OK"                      # permitted at PROPOSAL
    assert RR.check_request_record(unk, "ORDER") == "REVIEW_REQUIRED"            # REVIEW_REQUIRED at ORDER
    r = dict(REC); del r["PURPOSE_STATEMENT"]
    assert RR.check_request_record(r, "PROPOSAL") == "OK"
    assert code(RR.check_request_record, r, "ORDER") == "REQUEST_PURPOSE_STATEMENT_MISSING"
