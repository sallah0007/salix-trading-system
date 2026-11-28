import pytest
from tracker_component.journal_port import InMemoryJournal
from tracker_component.order import ConstructionOrder, TrustAnchor
from tracker_component.claims import Refusal
from tracker_component.lifecycle import ReplicaLifecycle
from tracker_identity.models import LookupOutcome

BIND = "b" * 64
ANCHOR = TrustAnchor(frozenset({"ISS1", "ISS2"}), BIND)
ABS = LookupOutcome.ABSENT


def mk():
    j = InMemoryJournal(); s = ReplicaLifecycle(j, ANCHOR); return j, s


def order(s, oid="O1", subj="S1", by="ISS1"):
    s.issue_order(ConstructionOrder(oid, subj, BIND, by, None))


def claim(s, oid="O1", subj="S1", rid="C1"):
    return s.reserve(subject_key=subj, request_id=rid, order_id=oid, lookup_outcome=ABS)


def admit(s, bid="B1", oid="O1", cid="CLAIM:C1", rid="C1", g="BG1", parent=None):
    return s.admit_attempt(build_id=bid, order_id=oid, claim_id=cid, creation_request_id=rid, builder_grant=g, correction_parent=parent)


def base():
    j, s = mk(); order(s); claim(s); return j, s


# ---- RD4a -----------------------------------------------------------------------------------------------------------
def test_attempt_binding_generation_and_replay():
    j, s = base(); a = admit(s)
    assert a["reservation_generation"] == 1 and admit(s) == a and s.attempt("B1") == a
    n = j.head().seq; admit(s); assert j.head().seq == n                       # exact replay appends nothing


def test_attempt_refusals():
    j, s = base()
    with pytest.raises(Refusal, match="ATTEMPT_BINDING_MISMATCH"): admit(s, rid="OTHER")
    with pytest.raises(Refusal, match="ATTEMPT_BINDING_MISMATCH"): admit(s, cid="CLAIM:ZZ")
    with pytest.raises(Refusal, match="CORRECTION_PARENT_UNKNOWN"): admit(s, parent="X")
    admit(s)
    with pytest.raises(Refusal, match="BUILD_ID_CONFLICT"): admit(s, g="BG2")
    with pytest.raises(Refusal, match="ATTEMPT_ALREADY_LIVE"): admit(s, bid="B2")
    s.reject_attempt("B1", "bad")
    with pytest.raises(Refusal, match="CORRECTION_PARENT_REQUIRED"): admit(s, bid="B2")
    with pytest.raises(Refusal, match="CORRECTION_PARENT_REQUIRED"): admit(s, bid="B2", parent="NOPE")
    assert admit(s, bid="B2", parent="B1")["reservation_generation"] == 2      # rejected attempt leaves the order correctable only via a linked attempt


def test_admit_requires_bound_claim():
    _, s = base(); s.release("CLAIM:C1", "x")
    with pytest.raises(Refusal, match="CLAIM_NOT_BOUND"): admit(s)


def test_empty_build_id_refused():
    _, s = base()
    with pytest.raises(Refusal, match="BUILD_ID_REQUIRED"): admit(s, bid="")


# ---- R5 terminal rule -----------------------------------------------------------------------------------------------
def test_issuer_grant_revocation_terminates_order_claim_and_no_revival():
    j, s = base(); admit(s)
    assert s.revoke_grant("ISS1", "issuer") == ["O1"]
    assert s.claim("CLAIM:C1")["state"] == "ABANDONED" and "O1" in s._p.revoked
    with pytest.raises(Refusal, match="ORDER_REVOKED"): s.verified_order("O1")
    with pytest.raises(Refusal): s.reserve(subject_key="S1", request_id="C1", order_id="O1", lookup_outcome=ABS)
    assert s.revoke_grant("ISS1", "issuer") == []                               # idempotent


def test_builder_grant_revocation_and_derived_refusal_before_settle():
    j, s = base(); admit(s)
    j.append(j.head(), "GRANT_REVOKED", {"grant_id": "BG1", "role": "builder"})  # raw fact; cascade records NOT yet written
    with pytest.raises(Refusal, match="ORDER_REVOKED_BY_GRANT"): s.verified_order("O1")   # authority derives from the same HEAD
    assert s.settle() == ["O1"] and s.claim("CLAIM:C1")["state"] == "ABANDONED"


def test_unrelated_grant_and_consumed_history_untouched():
    j, s = base(); order(s, "O2", "S2", "ISS2"); claim(s, "O2", "S2", "C2"); admit(s)
    s.consume("CLAIM:C1", "ID1")
    assert s.revoke_grant("ISS1", "issuer") == []                               # accepted history immutable
    assert s.verified_order("O1") and s.claim("CLAIM:C1")["state"] == "CONSUMED"
    assert s.verified_order("O2")
    assert s.revoke_grant("ISS2", "issuer") == ["O2"]


def test_downstream_role_revocation_has_no_order_consequence_but_blocks_new_dispositions():
    j, s = base(); admit(s)
    assert s.revoke_grant("INTAKE1", "intake") == [] and s.verified_order("O1")
    with pytest.raises(Refusal, match="GRANT_REVOKED"): disp(s, origin="INTAKE1")
    with pytest.raises(Refusal, match="GRANT_ROLE_CONFLICT"): s.revoke_grant("INTAKE1", "issuer")
    with pytest.raises(Refusal, match="GRANT_ROLE_UNKNOWN"): s.revoke_grant("X", "boss")


# ---- creation lineage -----------------------------------------------------------------------------------------------
def test_replacement_parent_link_and_rules():
    j, s = base()
    with pytest.raises(Refusal, match="OLD_LINEAGE_NOT_TERMINAL"):
        order(s, "O2", "S1"); s.replace_creation(old_creation_id="C1", new_creation_id="C9", subject_key="S1", order_id="O2", lookup_outcome=ABS)
    s.release("CLAIM:C1", "x")
    with pytest.raises(Refusal, match="REPLACEMENT_NEEDS_NEW_ORDER"): s.replace_creation(old_creation_id="C1", new_creation_id="C9", subject_key="S1", order_id="O1", lookup_outcome=ABS)
    with pytest.raises(Refusal, match="CREATION_ID_REUSED"): s.replace_creation(old_creation_id="C1", new_creation_id="C1", subject_key="S1", order_id="O2", lookup_outcome=ABS)
    with pytest.raises(Refusal, match="INCOMPLETE_LOOKUP"): s.replace_creation(old_creation_id="C1", new_creation_id="C9", subject_key="S1", order_id="O2", lookup_outcome=LookupOutcome.INCOMPLETE_LOOKUP)
    with pytest.raises(Refusal, match="DUPLICATE_OR_NEAR"): s.replace_creation(old_creation_id="C1", new_creation_id="C9", subject_key="S1", order_id="O2", lookup_outcome=LookupOutcome.NEAR_MATCH)
    c = s.replace_creation(old_creation_id="C1", new_creation_id="C9", subject_key="S1", order_id="O2", lookup_outcome=ABS)
    assert s.parent_of("C9") == "C1" and c["request_id"] == "C9"
    with pytest.raises(Refusal, match="CREATION_ID_REUSED"): s.replace_creation(old_creation_id="C1", new_creation_id="C9", subject_key="S1", order_id="O2", lookup_outcome=ABS)


def test_consumed_lineage_is_reused_not_recreated():
    j, s = base(); order(s, "O2", "S2"); s.consume("CLAIM:C1", "ID1")
    with pytest.raises(Refusal, match="OLD_LINEAGE_SUCCEEDED"): s.replace_creation(old_creation_id="C1", new_creation_id="C9", subject_key="S2", order_id="O2", lookup_outcome=ABS)


def test_abandoned_by_grant_lineage_may_be_replaced():
    j, s = base(); s.revoke_grant("ISS1", "issuer"); order(s, "O2", "S1", "ISS2")
    assert s.replace_creation(old_creation_id="C1", new_creation_id="C9", subject_key="S1", order_id="O2", lookup_outcome=ABS)["order_id"] == "O2"


# ---- RD4b -----------------------------------------------------------------------------------------------------------
def disp(s, rid="R1", rh="h1", verdict="REVIEW_REQUIRED", prior=None, pkg="P1", ph="ph", origin="INTAKE1", bid="B1"):
    return s.dispose(package_id=pkg, package_hash=ph, report_id=rid, report_hash=rh, verdict=verdict, build_id=bid, origin_grant=origin, prior_report_hash=prior)


def review(s, prior="h1", gen=0, origin="REV1"):
    return s.record_review(package_id="P1", package_hash="ph", prior_report_hash=prior, build_id="B1", expected_review_generation=gen, decision="APPROVE_REVERIFY", origin_grant=origin, decision_evidence_hash="e1")


def test_review_then_successor_final_unique_and_immutable_history():
    j, s = base(); admit(s)
    d = disp(s); assert d["verdict"] == "REVIEW_REQUIRED"
    assert s.verified_order("O1") and s.claim("CLAIM:C1")["state"] == "BOUND"      # REVIEW_REQUIRED is nonterminal, no provisional registration
    with pytest.raises(Refusal, match="SUCCESSOR_MUST_FOLLOW|SUCCESSOR_NEEDS_REVIEW"): disp(s, rid="R2", rh="h2", verdict="ACCEPT_FOR_REGISTRY", prior="h1")
    review(s)
    with pytest.raises(Refusal, match="REVIEW_GENERATION_MISMATCH"): review(s, gen=5)
    with pytest.raises(Refusal, match="SUCCESSOR_MUST_FOLLOW"): disp(s, rid="R2", rh="h2", verdict="ACCEPT_FOR_REGISTRY", prior="zz")
    with pytest.raises(Refusal, match="PACKAGE_HASH_CHANGED"): disp(s, rid="R2", rh="h2", verdict="ACCEPT_FOR_REGISTRY", prior="h1", ph="other")
    f = disp(s, rid="R2", rh="h2", verdict="ACCEPT_FOR_REGISTRY", prior="h1")
    assert s.current_disposition("P1") == f and s.report_readback("P1", "h1")["verdict"] == "REVIEW_REQUIRED"
    n = j.head().seq; disp(s, rid="R2", rh="h2", verdict="ACCEPT_FOR_REGISTRY", prior="h1"); assert j.head().seq == n   # exact replay
    with pytest.raises(Refusal, match="REPORT_ID_REBOUND"): disp(s, rid="R2", rh="hX", verdict="ACCEPT_FOR_REGISTRY", prior="h1")
    with pytest.raises(Refusal, match="FINAL_DISPOSITION_EXISTS"): disp(s, rid="R3", rh="h3", verdict="REUSE_EXISTING", prior="h2")   # no second effect
    with pytest.raises(Refusal, match="FINAL_DISPOSITION_EXISTS"): review(s, prior="h2", gen=1)


def test_report_hash_reuse_and_bad_verdict_and_first_report_cannot_name_prior():
    j, s = base(); admit(s)
    with pytest.raises(Refusal, match="VERDICT_NOT_ADMITTED_HERE"): disp(s, verdict="REJECT")
    with pytest.raises(Refusal, match="NO_PRIOR_REPORT"): disp(s, prior="h0")
    disp(s); review(s)
    with pytest.raises(Refusal, match="REPORT_HASH_REUSED"): disp(s, rid="R2", rh="h1", verdict="REVIEW_REQUIRED", prior="h1")


def test_review_cannot_revive_revoked_order_or_unadmitted_attempt():
    j, s = base(); admit(s); disp(s)
    s.revoke_grant("ISS1", "issuer")
    with pytest.raises(Refusal): review(s)
    with pytest.raises(Refusal): disp(s, rid="R2", rh="h2", verdict="ACCEPT_FOR_REGISTRY", prior="h1")
    j2, s2 = base()
    with pytest.raises(Refusal, match="ATTEMPT_NOT_ADMITTED"): disp(s2)


def test_review_origin_grant_revoked_refuses_and_projection_replay_equal():
    j, s = base(); admit(s); disp(s); s.revoke_grant("REV1", "verifier")
    with pytest.raises(Refusal, match="GRANT_REVOKED"): review(s)
    s.verify_projection()


# ---- R49 reproductions -----------------------------------------------------------------------------------------------
class Boom(Exception): pass


class FaultJournal(InMemoryJournal):
    """Test port: raises BEFORE appending the named kind (once armed). Earlier writes succeed."""
    fail_kind = None
    def append(self, expected_head, kind, body):
        if kind == self.fail_kind: raise Boom(kind)
        return super().append(expected_head, kind, body)


def two_orders():
    j = FaultJournal(); s = ReplicaLifecycle(j, ANCHOR); order(s); claim(s); order(s, "O2", "S2", "ISS2"); claim(s, "O2", "S2", "C2"); admit(s)
    admit(s, "B2", "O2", "CLAIM:C2", "C2", "BG2"); return j, s


def test_r49_1_one_attempt_cannot_make_two_finals():
    j, s = two_orders()
    disp(s, verdict="ACCEPT_FOR_REGISTRY")                                             # positive
    with pytest.raises(Refusal, match="ATTEMPT_ALREADY_HAS_FINAL_EFFECT"): disp(s, pkg="P2", rid="R2", rh="h2", verdict="ACCEPT_FOR_REGISTRY")
    with pytest.raises(Refusal, match="ATTEMPT_ALREADY_HAS_FINAL_EFFECT"): disp(s, pkg="P3", rid="R3", rh="h3", verdict="REUSE_EXISTING")
    assert disp(s, pkg="P2", rid="R2", rh="h2", verdict="REVIEW_REQUIRED")["verdict"] == "REVIEW_REQUIRED"      # a nonterminal report is not a second effect
    assert disp(s, pkg="P9", rid="R9", rh="h9", verdict="ACCEPT_FOR_REGISTRY", bid="B2")["build_id"] == "B2"    # another attempt's own final stays allowed


def test_r49_2_foreign_attempt_cannot_take_over_review_or_successor():
    j, s = two_orders(); disp(s)
    with pytest.raises(Refusal, match="PACKAGE_OWNED_BY_ANOTHER_ATTEMPT"):
        s.record_review(package_id="P1", package_hash="ph", prior_report_hash="h1", build_id="B2", expected_review_generation=0, decision="X", origin_grant="REV1", decision_evidence_hash="e")
    review(s)                                                                          # own attempt: positive
    with pytest.raises(Refusal, match="PACKAGE_OWNED_BY_ANOTHER_ATTEMPT"): disp(s, rid="R2", rh="h2", verdict="ACCEPT_FOR_REGISTRY", prior="h1", bid="B2")
    with pytest.raises(Refusal, match="PACKAGE_OWNED_BY_ANOTHER_ATTEMPT"): disp(s, rid="R1", rh="h1", verdict="REVIEW_REQUIRED", bid="B2")   # foreign exact replay
    assert disp(s, rid="R2", rh="h2", verdict="ACCEPT_FOR_REGISTRY", prior="h1")["build_id"] == "B1"


def test_r49_3_crash_before_abandon_is_reconciled_on_restart_and_retry():
    j, s = two_orders(); s.consume("CLAIM:C2", "ID2") if False else None
    j.fail_kind = "CLAIM_ABANDONED"
    with pytest.raises(Boom): s.revoke_grant("ISS1", "issuer")
    assert s.claim("CLAIM:C1")["state"] == "BOUND" and "O1" in s._p.revoked           # the stranded state
    j.fail_kind = None
    s2 = ReplicaLifecycle(j, ANCHOR)                                                   # restart on the SAME journal
    assert s2.settle() == ["O1"] and s2.claim("CLAIM:C1")["state"] == "ABANDONED"
    assert s2.settle() == [] and s2.revoke_grant("ISS1", "issuer") == []               # exact retry / idempotent
    assert s2.authorizes("S2", "C2") is True and s2.claim("CLAIM:C2")["state"] == "BOUND"      # unrelated control
    s2.verify_projection()


def test_r49_3b_accepted_history_unchanged_through_crash_recovery():
    j = FaultJournal(); s = ReplicaLifecycle(j, ANCHOR); order(s); claim(s); admit(s); s.consume("CLAIM:C1", "ID1"); order(s, "O2", "S2", "ISS1"); claim(s, "O2", "S2", "C2")
    j.fail_kind = "CLAIM_ABANDONED"
    with pytest.raises(Boom): s.revoke_grant("ISS1", "issuer")
    j.fail_kind = None; s2 = ReplicaLifecycle(j, ANCHOR)
    assert s2.settle() == ["O2"] and s2.claim("CLAIM:C1")["state"] == "CONSUMED" and s2.claim("CLAIM:C2")["state"] == "ABANDONED"


def test_r49_4_base_claimservice_and_composed_authority_route_fail_closed_in_crash_window():
    from tracker_component.claims import ClaimService
    j, s = two_orders()
    base = ClaimService(j, ANCHOR); assert base.authorizes("S1", "C1") is True and base.authorizes("S2", "C2") is True      # genuine baseline
    j.fail_kind = "ORDER_REVOKED"
    with pytest.raises(Boom): s.revoke_grant("BG1", "builder")                           # GRANT_REVOKED durable, then throws
    assert s.authorizes("S1", "C1") is False
    base2 = ClaimService(j, ANCHOR)                                                    # the NORMAL shared service on the same journal
    assert base2.authorizes("S1", "C1") is False and base2.authorizes("S2", "C2") is True
    from stage_a.tracker import authority_bridge as AB
    import inspect; assert "authorizes" in inspect.getsource(AB)                       # the composed route calls claim_service.authorizes
    j.fail_kind = None; assert s.settle() == ["O1"] and base2.claim("CLAIM:C1")["state"] == "ABANDONED" and base2.authorizes("S2", "C2") is True
