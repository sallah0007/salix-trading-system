import pytest
from tracker_component import audit as A
from tracker_component.claims import Refusal
from .test_r48_replica_lifecycle import base, admit, disp


def test_evidence_derives_chain_fields_and_marks_unsupplied_items_unbound():
    j, s = base(); admit(s); disp(s)
    ev = A.journal_evidence(j)
    assert [e["operation"] for e in ev] == ["ORDER_ISSUED", "CLAIM_BOUND", "ATTEMPT_ADMITTED", "REPORT_DISPOSITION"]
    assert ev[0]["predecessor_hash"] == "0" * 64 and all(ev[i]["new_hash"] == ev[i + 1]["predecessor_hash"] for i in range(3))
    assert ev[2]["subject"] == "B1" and ev[3]["subject"] == "P1" and ev[0]["subject"] == "O1"
    assert all(e["actor_service_identity"] == A.UNBOUND and e["complete"] is False and e["authoritative"] is False for e in ev)      # principals are unbound: never "complete"


def test_complete_only_when_every_supplied_item_is_present_and_unknown_fields_refused():
    j, s = base(); r = j.read_from(1)[0]
    full = dict(actor_service_identity="svc-label", idempotency_key="k1", epoch_fence=3, decision_accepted_timestamp=10, available_as_of=9, evidence_refs=("e1",))
    assert A.transition_evidence(r, **full)["complete"] is True
    for f in full:
        part = {k: v for k, v in full.items() if k != f}; e = A.transition_evidence(r, **part)
        assert e[f] == A.UNBOUND and e["complete"] is False, f
    assert A.transition_evidence(r, **dict(full, evidence_refs=()))["complete"] is False
    with pytest.raises(Refusal, match="AUDIT_UNKNOWN_FIELD"): A.transition_evidence(r, **dict(full, extra="x"))


def test_predecessor_mismatch_and_unrecognised_subject_fail_closed():
    j, s = base(); r = j.read_from(2)[0]
    with pytest.raises(Refusal, match="AUDIT_PREDECESSOR_MISMATCH"): A.transition_evidence(r, prev_hash="f" * 64)
    j.append(j.head(), "ORDER_PROVENANCE", {"nothing": 1})
    with pytest.raises(Refusal, match="AUDIT_SUBJECT_NOT_DERIVABLE"): A.transition_evidence(j.read_from(1)[-1])
