"""R09: admission-boundary controls (Codex R08 review): seven-field binding shape, descriptor crosswalk no longer accepts arbitrary objects,
grant-evidence shape, Health single-state-field rule, E-01 provider contract. Mutants in mutation_sweep_r09.py."""
import pytest
from stage_a.errors import Refusal
from stage_a.binding import producer_binding as B
from stage_a.fw import descriptor_crosswalk as X
from stage_a.security import principals as P
from stage_a.health import envelope as H
from stage_a.coordination import provider_contract as C
from stage_a.storage.object_store import InMemoryObjectStore

GOOD = {"scope": "s", "interface_id": "i", "version": "1", "content_hash": "a" * 64, "source_authority": "a", "acceptance_record": "r",
        "validity/supersession": "v"}
def code(fn, *a):
    with pytest.raises(Refusal) as e: fn(*a)
    return e.value.code

def test_seven_field_shape_accepts_complete_and_refuses_every_defect():
    assert B.check_shape(dict(GOOD)) == GOOD and len(B.SEVEN_FIELDS) == 7
    for f in B.SEVEN_FIELDS:
        r = dict(GOOD); del r[f]
        assert code(B.check_shape, r) == "BINDING_UNSATISFIED_MISSING_FIELD"
        r = dict(GOOD); r[f] = "  "
        assert code(B.check_shape, r) == "BINDING_FIELD_EMPTY_OR_NOT_TEXT"
        r = dict(GOOD); r[f] = None
        assert code(B.check_shape, r) == "BINDING_FIELD_EMPTY_OR_NOT_TEXT"
    assert code(B.check_shape, {**GOOD, "extra": "x"}) == "BINDING_UNKNOWN_FIELD"
    assert code(B.check_shape, object()) == "BINDING_NOT_A_RECORD"
    for bad in ("A" * 64, "a" * 63, "g" * 64, ("a" * 64) + "\n"):
        assert code(B.check_shape, {**GOOD, "content_hash": bad}) == "BINDING_HASH_NOT_SHA256_HEX"

def test_descriptor_lookup_refuses_arbitrary_caller_values_and_is_labelled_documentary():
    assert X.DOCUMENTARY_LOOKUP_ONLY is True
    for junk in (object(), "x", 1, {}, {"scope": "s"}):
        assert code(X.require_real_binding, "HORIZON_ID", {"HORIZON_ID": junk}) in ("BINDING_NOT_A_RECORD", "BINDING_UNSATISFIED_MISSING_FIELD")
    assert X.require_real_binding("HORIZON_ID", {"HORIZON_ID": GOOD}) == GOOD

GRANT = {"principal_id": "p", "role": "tracker-acceptor", "grant_generation": "1", "bootstrap_trust_anchor_ref": "t", "namespace_id": "n",
         "operation_scope": "o", "issued_by_record_ref": "r", "validity/supersession": "v"}
def test_grant_evidence_shape_only_and_lookup_is_labelled_not_authentication():
    assert P.LOOKUP_ONLY_NOT_AUTHENTICATION is True
    assert P.check_grant_evidence_shape(dict(GRANT)) == GRANT
    for f in P.GRANT_EVIDENCE_FIELDS:
        r = dict(GRANT); del r[f]
        assert code(P.check_grant_evidence_shape, r) == "GRANT_EVIDENCE_FIELD_MISSING"
        r = dict(GRANT); r[f] = "  "
        assert code(P.check_grant_evidence_shape, r) == "GRANT_EVIDENCE_FIELD_MISSING"
        r = dict(GRANT); r[f] = 5
        assert code(P.check_grant_evidence_shape, r) == "GRANT_EVIDENCE_FIELD_MISSING"
    assert code(P.check_grant_evidence_shape, {**GRANT, "x": "y"}) == "GRANT_EVIDENCE_UNKNOWN_FIELD"
    assert code(P.check_grant_evidence_shape, {**GRANT, "role": "root"}) == "UNKNOWN_PRINCIPAL"
    assert code(P.check_grant_evidence_shape, {**GRANT, "role": "acceptance-origin"}) == "REPLICA_ONLY_ROLE_NOT_IN_E06"
    assert P.check_grant_evidence_shape({**GRANT, "role": "acceptance-origin"}, "REPLICA")["role"] == "acceptance-origin"
    assert code(P.check_grant_evidence_shape, {**GRANT, "role": "tracker-acceptor"}, "REPLICA") == "REPLICA_ACCEPTOR_SPLIT_REQUIRED"
    assert code(P.check_grant_evidence_shape, dict(GRANT), "elsewhere") == "GRANT_EVIDENCE_SCOPE_UNKNOWN"
    assert code(P.check_grant_evidence_shape, []) == "GRANT_EVIDENCE_NOT_A_RECORD"

def test_health_envelope_refuses_second_local_state_field():
    assert code(H.check_envelope, {"ML_LOCAL_STATE": "HEALTHY"}, {"v1"}) == "SECOND_LOCAL_STATE_FIELD"

def test_e01_method_mapping_and_store_has_all_mapped_methods():
    assert set(C.E01_METHOD_TO_STORE) == {"read_head", "compare_and_swap_head", "append_transition_if_absent", "read_transition",
                                         "scan_transitions", "read_after_write_probe"}
    assert C.missing_store_methods(InMemoryObjectStore()) == []
    assert C.missing_store_methods(object()) == ["get", "list_prefix", "put_if_absent", "put_if_match"]

def test_read_after_write_probe_true_on_sim_false_on_broken_store():
    assert C.read_after_write_probe(InMemoryObjectStore(), "k") is True
    class Stale(InMemoryObjectStore):
        def get(self, key): return None
    assert C.read_after_write_probe(Stale(), "k") is False
    class Wrong(InMemoryObjectStore):
        def get(self, key): return (b"other", "e")
    assert C.read_after_write_probe(Wrong(), "k") is False

def test_provider_proof_requires_named_provider_and_all_five_classes_passing():
    ok = {"provider_id": "p", "results": {c: "PASS" for c in C.REQUIRED_CONFORMANCE}}
    C.require_provider_proof(ok)
    assert code(C.require_provider_proof, {}) == "PROVIDER_NOT_NAMED"
    for c in C.REQUIRED_CONFORMANCE:
        bad = {"provider_id": "p", "results": {**ok["results"], c: "NOT_RUN"}}
        assert code(C.require_provider_proof, bad) == "PROVIDER_CONFORMANCE_NOT_PROVEN"
    assert len(C.REQUIRED_CONFORMANCE) == 5

def test_provider_proof_is_labelled_claimed_fields_only_and_has_no_stage_a_consumer():
    import pathlib, re
    assert C.CLAIMED_FIELDS_ONLY_NOT_AUTHENTICATED is True
    root = pathlib.Path(__file__).resolve().parents[2] / "stage_a"
    users = [str(p) for p in root.rglob("*.py") if p.name != "provider_contract.py" and re.search(r"require_provider_proof", p.read_text())]
    assert users == []          # any new caller must revisit this label and the closeout's consumer statement
