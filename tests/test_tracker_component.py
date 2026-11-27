import copy, threading
import pytest
from tracker_component.canonical import canonical_json, CanonicalError
from tracker_component.journal_port import (InMemoryJournal, HeadMismatch, GENESIS_HEAD, verify_chain,
                                            JournalIntegrityError, JournalRecord)
from tracker_component.order import ConstructionOrder, TrustAnchor
from tracker_component.claims import ClaimService, Refusal
from tracker_component.projection import Projection, ProjectionDrift
from tracker_component import report as R
from tracker_identity.models import LookupOutcome

BIND = "b" * 64
ANCHOR = TrustAnchor(frozenset({"MANAGER_ROLE_1"}), BIND)

def order(oid="O1", subj="S1", by="MANAGER_ROLE_1", bind=BIND, until=None):
    return ConstructionOrder(oid, subj, bind, by, until)

def svc(j=None, anchor=ANCHOR):
    j = j or InMemoryJournal()
    return j, ClaimService(j, anchor)

def reserve(s, subj="S1", rid="R1", oid="O1", lk=LookupOutcome.ABSENT):
    return s.reserve(subject_key=subj, request_id=rid, order_id=oid, lookup_outcome=lk)

# ---- canonical -------------------------------------------------------------
def test_canonical_order_invariant_and_float_rejected():
    assert canonical_json({"b": 1, "a": [1, 2]}) == canonical_json({"a": [1, 2], "b": 1})
    with pytest.raises(CanonicalError):
        canonical_json({"a": 1.5})
    with pytest.raises(CanonicalError):
        canonical_json({1: "x"})

# ---- journal ---------------------------------------------------------------
def test_journal_cas_and_chain():
    j = InMemoryJournal()
    r1 = j.append(GENESIS_HEAD, "ORDER_ISSUED", {"x": 1})
    with pytest.raises(HeadMismatch):
        j.append(GENESIS_HEAD, "ORDER_ISSUED", {"x": 2})
    j.append(j.head(), "ORDER_ISSUED", {"x": 3})
    assert verify_chain(j.read_from(1)).seq == 2

def test_chain_tamper_detected():
    j = InMemoryJournal()
    j.append(GENESIS_HEAD, "ORDER_ISSUED", {"x": 1})
    r = j.read_from(1)[0]
    bad = JournalRecord(r.seq, r.prev_hash, r.kind, '{"x":2}', r.record_hash)
    with pytest.raises(JournalIntegrityError):
        verify_chain([bad])

def test_concurrent_append_single_winner():
    j = InMemoryJournal()
    h = j.head(); wins = []; errs = []
    def go(i):
        try:
            j.append(h, "ORDER_ISSUED", {"i": i}); wins.append(i)
        except HeadMismatch:
            errs.append(i)
    ts = [threading.Thread(target=go, args=(i,)) for i in range(16)]
    [t.start() for t in ts]; [t.join() for t in ts]
    assert len(wins) == 1 and len(errs) == 15

# ---- claims: happy path and refusals --------------------------------------
def test_happy_path_reserve_consume():
    j, s = svc(); s.issue_order(order())
    c = reserve(s); assert c["state"] == "BOUND"
    done = s.consume(c["claim_id"], "FEAT-1"); assert done["state"] == "CONSUMED"
    s.verify_projection()

def test_no_order_refused():
    _, s = svc()
    with pytest.raises(Refusal) as e: reserve(s)
    assert e.value.code == "NO_ORDER"

@pytest.mark.parametrize("kw,code", [
    (dict(by="ROGUE"), "ISSUER_NOT_ANCHORED"),
    (dict(bind="c" * 64), "SOURCE_BINDING_MISMATCH"),
])
def test_order_trust_checks(kw, code):
    _, s = svc(); s.issue_order(order(**kw))
    with pytest.raises(Refusal) as e: reserve(s)
    assert e.value.code == code

def test_subject_mismatch_and_expiry():
    _, s = svc(); s.issue_order(order(until=1))
    with pytest.raises(Refusal) as e: reserve(s, subj="OTHER")
    assert e.value.code == "ORDER_SUBJECT_MISMATCH"
    s.issue_order(order(oid="O2", subj="S2", until=1))  # head moves past seq 1
    with pytest.raises(Refusal) as e: reserve(s, subj="S2", rid="R2", oid="O2")
    assert e.value.code == "ORDER_EXPIRED"

def test_revoked_order_refused():
    _, s = svc(); s.issue_order(order()); s.revoke_order("O1", "withdrawn")
    with pytest.raises(Refusal) as e: reserve(s)
    assert e.value.code == "ORDER_REVOKED"

@pytest.mark.parametrize("lk,code", [
    (LookupOutcome.ABSENT_EXACT_STRUCTURAL_IN_ERA_1, "INCOMPLETE_LOOKUP"),
    (LookupOutcome.ABSENT_IN_ERA_1, "INCOMPLETE_LOOKUP"),
    (LookupOutcome.INCOMPLETE_LOOKUP, "INCOMPLETE_LOOKUP"),
    (LookupOutcome.ERROR_UNRESOLVED, "INCOMPLETE_LOOKUP"),
    ("garbage", "INCOMPLETE_LOOKUP"),
    (LookupOutcome.EXACT_CANONICAL_IDENTITY, "DUPLICATE_OR_NEAR"),
    (LookupOutcome.NEAR_MATCH, "DUPLICATE_OR_NEAR"),
])
def test_lookup_gate(lk, code):
    _, s = svc(); s.issue_order(order())
    with pytest.raises(Refusal) as e: reserve(s, lk=lk)
    assert e.value.code == code

def test_double_claim_and_idempotent_replay_and_request_conflict():
    j, s = svc(); s.issue_order(order())
    a = reserve(s); b = reserve(s)            # identical retry -> same claim, no second record
    assert a["claim_id"] == b["claim_id"]
    assert sum(1 for r in j.read_from(1) if r.kind == "CLAIM_BOUND") == 1
    with pytest.raises(Refusal) as e: reserve(s, rid="R2")
    assert e.value.code == "SUBJECT_ALREADY_CLAIMED"
    s.issue_order(order(oid="O2", subj="S2"))
    with pytest.raises(Refusal) as e: reserve(s, subj="S2", rid="R1", oid="O2")
    assert e.value.code == "REQUEST_ID_CONFLICT"

def test_release_frees_subject_consumed_does_not():
    _, s = svc(); s.issue_order(order())
    c = reserve(s); s.release(c["claim_id"], "abandon")
    c2 = reserve(s, rid="R2"); s.consume(c2["claim_id"], "F")
    with pytest.raises(Refusal) as e: reserve(s, rid="R3")
    assert e.value.code == "SUBJECT_ALREADY_CLAIMED"

def test_consume_twice_refused():
    _, s = svc(); s.issue_order(order())
    c = reserve(s); s.consume(c["claim_id"], "F")
    with pytest.raises(Refusal) as e: s.consume(c["claim_id"], "F")
    assert e.value.code == "CLAIM_NOT_BOUND"

# ---- seam 2: revocation between verify and commit --------------------------
class RacingJournal(InMemoryJournal):
    """Appends an ORDER_REVOKED just before the first matching append, simulating an
    external revocation landing after verification but before commit."""
    def __init__(self, trigger_kind):
        super().__init__(); self.trigger = trigger_kind; self.armed = False; self.fired = False
    def append(self, expected_head, kind, body):
        if self.armed and not self.fired and kind == self.trigger:
            self.fired = True
            super().append(self.head(), "ORDER_REVOKED", {"order_id": "O1", "reason": "external"})
        return super().append(expected_head, kind, body)

def test_revocation_between_verify_and_consume_fails_closed():
    j = RacingJournal("CLAIM_CONSUMED"); s = ClaimService(j, ANCHOR)
    s.issue_order(order()); c = reserve(s)
    j.armed = True
    with pytest.raises(Refusal) as e: s.consume(c["claim_id"], "F")
    assert j.fired and e.value.code == "ORDER_REVOKED"
    assert not any(r.kind == "CLAIM_CONSUMED" for r in j.read_from(1))

def test_revocation_between_verify_and_reserve_fails_closed():
    j = RacingJournal("CLAIM_BOUND"); s = ClaimService(j, ANCHOR)
    s.issue_order(order()); j.armed = True
    with pytest.raises(Refusal) as e: reserve(s)
    assert j.fired and e.value.code == "ORDER_REVOKED"

def test_fence_race_exhaustion_fails_closed():
    class Always(InMemoryJournal):
        def append(self, expected_head, kind, body):
            if kind == "CLAIM_CONSUMED":
                raise HeadMismatch(expected_head, expected_head)
            return super().append(expected_head, kind, body)
    j = Always(); s = ClaimService(j, ANCHOR, max_fence_retries=2)
    s.issue_order(order()); c = reserve(s)
    with pytest.raises(Refusal) as e: s.consume(c["claim_id"], "F")
    assert e.value.code == "FENCE_RACE_EXHAUSTED"

# ---- seam 3: projection is subordinate to the journal ----------------------
def test_projection_matches_replay_and_detects_drift():
    j, s = svc(); s.issue_order(order()); c = reserve(s); s.consume(c["claim_id"], "F")
    s.verify_projection()
    s._p.claims[c["claim_id"]]["state"] = "BOUND"        # tamper the read model
    with pytest.raises(ProjectionDrift): s.verify_projection()

def test_second_instance_rebuilds_and_sees_state():
    j, s = svc(); s.issue_order(order()); c = reserve(s)
    s2 = ClaimService(j, ANCHOR)
    with pytest.raises(Refusal) as e: reserve(s2, rid="R9")
    assert e.value.code == "SUBJECT_ALREADY_CLAIMED"
    s2.consume(c["claim_id"], "F")
    with pytest.raises(Refusal) as e: s.consume(c["claim_id"], "F")
    assert e.value.code == "CLAIM_NOT_BOUND"

def test_unknown_kind_and_gap_fail_closed():
    j = InMemoryJournal(); j.append(GENESIS_HEAD, "MYSTERY", {"a": 1})
    with pytest.raises(ProjectionDrift): Projection().sync(j)

# ---- baseline boundary ------------------------------------------------------
def test_baseline_authority_still_false_and_untouched():
    from tracker_identity import store
    assert store._governed_construction_authority({}) is False
    assert store._fixture_seeding_permitted() is False

# ---- seam 4: report hash / schema ------------------------------------------
def good_body():
    return {
        "SAFE_INTAKE_REPORT_ID": "SIR-1",
        "BUILD_OUTPUT_PACKAGE": {"ID": "BOP-1", "HASH": "h1"},
        "REQUEST": {"REQUEST_ID": "R1", "CREATION_REQUEST_ID": "CR1"},
        "INTAKE_VERDICT": "ACCEPT_FOR_REGISTRY", "FAILED_DIMENSIONS": [], "FAILED_DIMENSION_REASON_CODES": [],
        "IDENTITY_DECISION": "NEW_CANONICAL_FEATURE",
        "RESULTING_FEATURE": {"FEATURE_ID": "F1", "FEATURE_VERSION": "1", "REGISTRY_ENTRY_REF": "RE1"},
        "CANONICAL_SURVIVOR": None, "FEATURE_VERSION_RELATIONSHIP_REF": None,
        "DEPENDENCY_CLOSURE_REF": "DC1", "ANCESTRY_COMPLETENESS": "PASS",
        "CAUSAL_AVAILABILITY_VERDICT": "PASS", "SOURCE_VINTAGE_PROVENANCE_VERDICT": "PASS",
        "OUTCOME_INFORMATION_ACCESS_VERDICT": "PASS", "LEARNED_OR_FITTED_ANCESTRY_VERDICT": "PASS",
        "COMPLETION_SEMANTICS_VERDICT": "PASS", "CURRENTNESS_HEALTH_ELIGIBILITY_INITIAL_STATE": "ELIGIBLE_INITIAL",
        "OMISSIONS_EXCLUSIONS_REASONS": [], "SAFE_INTAKE_TS": "2026-11-27T00:00:00Z",
        "TRACKER_VERIFIER_ID": "V1", "POLICY": {"ID": "P", "VERSION": "1", "HASH": "ph"},
    }

def test_report_roundtrip_23_entries():
    rep = R.build_report(good_body()); assert len(rep) == 23
    R.verify_report(rep)

def test_report_missing_extra_and_tamper():
    rep = R.build_report(good_body())
    for k in list(rep):
        bad = {x: v for x, v in rep.items() if x != k}
        with pytest.raises(R.ReportError): R.verify_report(bad)
    extra = dict(rep, EXTRA="x")
    with pytest.raises(R.ReportError): R.verify_report(extra)
    t = copy.deepcopy(rep); t["SAFE_INTAKE_TS"] = "2026-11-28T00:00:00Z"
    with pytest.raises(R.ReportError): R.verify_report(t)

def test_every_body_field_is_hash_covered():
    base = R.build_report(good_body())["FINAL_REPORT_HASH"]
    muts = {
        "SAFE_INTAKE_REPORT_ID": "SIR-2", "BUILD_OUTPUT_PACKAGE": {"ID": "BOP-1", "HASH": "h2"},
        "REQUEST": {"REQUEST_ID": "R2", "CREATION_REQUEST_ID": "CR1"},
        "IDENTITY_DECISION": "MATERIAL_ALTERNATIVE",
        "RESULTING_FEATURE": {"FEATURE_ID": "F2", "FEATURE_VERSION": "1", "REGISTRY_ENTRY_REF": "RE1"},
        "CANONICAL_SURVIVOR": "CS1", "FEATURE_VERSION_RELATIONSHIP_REF": "FV1",
        "DEPENDENCY_CLOSURE_REF": "DC2", "CAUSAL_AVAILABILITY_VERDICT": "FAIL",
        "SOURCE_VINTAGE_PROVENANCE_VERDICT": "FAIL", "OUTCOME_INFORMATION_ACCESS_VERDICT": "FAIL",
        "LEARNED_OR_FITTED_ANCESTRY_VERDICT": "FAIL", "COMPLETION_SEMANTICS_VERDICT": "FAIL",
        "CURRENTNESS_HEALTH_ELIGIBILITY_INITIAL_STATE": "OTHER", "OMISSIONS_EXCLUSIONS_REASONS": ["x"],
        "SAFE_INTAKE_TS": "2026-11-28T00:00:00Z", "TRACKER_VERIFIER_ID": "V2",
        "POLICY": {"ID": "P", "VERSION": "2", "HASH": "ph"},
        "INTAKE_VERDICT": "REUSE_EXISTING",
    }
    for k, v in muts.items():
        b = good_body(); b[k] = v
        assert R.build_report(b)["FINAL_REPORT_HASH"] != base, k
    def review(anc):
        b = good_body(); b["INTAKE_VERDICT"] = "REVIEW_REQUIRED"; b["FAILED_DIMENSIONS"] = ["d"]
        b["FAILED_DIMENSION_REASON_CODES"] = ["c"]; b["ANCESTRY_COMPLETENESS"] = anc
        return R.build_report(b)["FINAL_REPORT_HASH"]
    assert review("PASS") != base and review("PASS") != review("UNKNOWN") != review("FAIL")

def test_report_enum_and_cross_rules():
    for k, v in (("INTAKE_VERDICT", "MAYBE"), ("IDENTITY_DECISION", "X"), ("ANCESTRY_COMPLETENESS", "OK")):
        b = good_body(); b[k] = v
        with pytest.raises(R.ReportError): R.build_report(b)
    b = good_body(); b["FAILED_DIMENSIONS"] = ["d"]
    with pytest.raises(R.ReportError): R.build_report(b)                  # unequal lists
    b = good_body(); b["ANCESTRY_COMPLETENESS"] = "UNKNOWN"
    with pytest.raises(R.ReportError): R.build_report(b)                  # accept needs PASS
    b = good_body(); b["INTAKE_VERDICT"] = "QUARANTINE_REQUIRED"
    with pytest.raises(R.ReportError): R.build_report(b)                  # needs failed dim
    b = good_body(); b["SAFE_INTAKE_TS"] = ""
    with pytest.raises(R.ReportError): R.build_report(b)
    b = good_body(); b["REQUEST"] = {"REQUEST_ID": "R"}
    with pytest.raises(R.ReportError): R.build_report(b)
    b = good_body(); b["OMISSIONS_EXCLUSIONS_REASONS"] = None
    with pytest.raises(R.ReportError): R.build_report(b)
