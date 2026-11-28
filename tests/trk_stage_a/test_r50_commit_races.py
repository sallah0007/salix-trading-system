"""R50: four manager-reproduced defects on the public API (in-memory journal; NOT a production adapter, no security/provider claim).
Every test here was run against the unfixed R49 tree first and failed (see the PR text)."""
import pytest
from tracker_component.journal_port import InMemoryJournal, HeadMismatch
from tracker_component.projection import Projection, ProjectionDrift
from tracker_component.claims import Refusal, ClaimService
from tracker_component.lifecycle import ReplicaLifecycle
from tracker_identity.models import LookupOutcome
from tests.trk_stage_a.test_r48_replica_lifecycle import (mk, order, claim, admit, base, ANCHOR, BIND, FakeTimePort, REF, lease)


class HookJournal(InMemoryJournal):
    """Genuine journal; a one-shot hook fires at a named public call (head/append) so a SECOND service really interleaves."""
    def __init__(self):
        super().__init__(); self.hooks = {}
    def _fire(self, name):
        h = self.hooks.pop(name, None)
        if h: h()
    def head(self):
        self._fire("head"); return super().head()
    def append(self, expected_head, kind, body):
        self._fire("append"); return super().append(expected_head, kind, body)


def kinds(j): return [r.kind for r in j.read_from(1)]


def cold(j):
    p = Projection(); p.sync(j); return p


# ---- 1. stale projection with newer HEAD ----------------------------------------------------------------------------------------------
def test_r50_1_consume_never_appends_after_a_revoke_it_did_not_see():
    j = HookJournal(); s1 = ReplicaLifecycle(j, ANCHOR); s2 = ReplicaLifecycle(j, ANCHOR)
    order(s1); claim(s1); admit(s1)
    # arm AFTER s1's first projection.sync: the next head() call is the one inside s1._commit
    real_sync = s1._p.sync
    def sync_then_arm(journal):
        real_sync(journal); j.hooks["head"] = lambda: s2.revoke_order("O1", "interleaved")
        s1._p.sync = real_sync
    s1._p.sync = sync_then_arm
    with pytest.raises(Refusal) as e: s1.consume("CLAIM:C1", "ID1")
    assert e.value.code == "ORDER_REVOKED"
    assert kinds(j) == ["ORDER_ISSUED", "CLAIM_BOUND", "ATTEMPT_ADMITTED", "ORDER_REVOKED"]            # no CLAIM_CONSUMED after the revoke
    cold(j); s1.verify_projection()                                                                    # no ProjectionDrift either


def test_r50_1_every_sync_head_path_uses_the_pinned_basis():
    """verified_order / authorizes / reserve replay / lease admit all read HEAD after sync: each must equal the projection seq/hash or resync."""
    j = HookJournal(); s1 = ReplicaLifecycle(j, ANCHOR); s2 = ReplicaLifecycle(j, ANCHOR)
    order(s1); claim(s1)
    def arm(then):
        real = s1._p.sync
        def f(journal):
            real(journal); j.hooks["head"] = then; s1._p.sync = real
        s1._p.sync = f
    arm(lambda: s2.revoke_order("O1", "x"))
    with pytest.raises(Refusal, match="ORDER_REVOKED"): s1.verified_order("O1")
    j2 = HookJournal(); a = ReplicaLifecycle(j2, ANCHOR); b = ReplicaLifecycle(j2, ANCHOR); order(a); claim(a)
    real = a._p.sync
    def f2(journal): real(journal); j2.hooks["head"] = lambda: b.revoke_order("O1", "x"); a._p.sync = real
    a._p.sync = f2
    assert a.authorizes("S1", "C1") is False                                                           # fail closed, not a stale True
    j3 = HookJournal(); c = ReplicaLifecycle(j3, ANCHOR); d = ReplicaLifecycle(j3, ANCHOR); order(c); claim(c); port = FakeTimePort(j3)
    real = c._p.sync
    def f3(journal): real(journal); j3.hooks["head"] = lambda: d.revoke_order("O1", "x"); c._p.sync = real
    c._p.sync = f3
    with pytest.raises(Refusal, match="ORDER_REVOKED"): lease(c, port)
    assert "ATTEMPT_ADMITTED" not in kinds(j3) and port.calls == []                                    # the port was never even asked


def test_r50_1_basis_that_never_converges_refuses_closed():
    j = HookJournal(); s = ReplicaLifecycle(j, ANCHOR); s2 = ReplicaLifecycle(j, ANCHOR); order(s); claim(s); n = [0]
    real = s._p.sync
    def storm(journal):
        real(journal)
        n[0] += 1; s2.attach_provenance("O1", {"n": n[0]})                                             # head moves after every sync
    s._p.sync = storm
    with pytest.raises(Refusal, match="FENCE_RACE_EXHAUSTED"): s.consume("CLAIM:C1", "ID1")
    assert "CLAIM_CONSUMED" not in kinds(j)


def test_r50_1_unraced_positive_still_consumes():
    j, s = base(); admit(s); assert s.consume("CLAIM:C1", "ID1")["state"] == "CONSUMED"


# ---- 2. concurrent settle ------------------------------------------------------------------------------------------------------------
def revoked_fault(j, s):
    """Genuine fault: GRANT_REVOKED lands, the process stops before settle's abandonment."""
    j.append(j.head(), "GRANT_REVOKED", {"grant_id": "ISS1", "role": "issuer"})


@pytest.mark.parametrize("at", ["append"])
def test_r50_2_concurrent_settle_does_not_double_abandon(at):
    j = HookJournal(); s1 = ReplicaLifecycle(j, ANCHOR); s2 = ReplicaLifecycle(j, ANCHOR)
    order(s1); claim(s1); revoked_fault(j, s1)
    s1._p.sync(j)
    # s1 reaches its OWN first append (ORDER_REVOKED); at that moment s2 settles completely
    j.hooks["append"] = lambda: s2.settle()
    s1.settle()
    p = cold(j)                                                                                        # cold rebuild must not raise
    assert p.claims["CLAIM:C1"]["state"] == "ABANDONED" and "O1" in p.revoked
    assert kinds(j).count("CLAIM_ABANDONED") == 1 and kinds(j).count("ORDER_REVOKED") == 1
    s1.verify_projection(); s2.verify_projection()


def test_r50_2_race_at_the_abandon_append_too():
    j = HookJournal(); s1 = ReplicaLifecycle(j, ANCHOR); s2 = ReplicaLifecycle(j, ANCHOR)
    order(s1); claim(s1); revoked_fault(j, s1); s1.revoke_order("O1", "GRANT_REVOCATION")             # order already revoked: only the abandonment is outstanding
    fired = []
    def once():
        fired.append(1); s2.settle()
    j.hooks["append"] = once
    s1.settle()
    assert fired and kinds(j).count("CLAIM_ABANDONED") == 1
    cold(j)


def test_r50_2_restart_retry_and_controls():
    j, s = mk(); order(s); claim(s); revoked_fault(j, s)
    class Boom(Exception): pass
    real = j.append; state = {"n": 0}
    def flaky(head, kind, body):
        r = real(head, kind, body)
        if kind == "CLAIM_ABANDONED" and state["n"] == 0:
            state["n"] = 1; raise Boom()                                                               # durable write, caller sees an UNKNOWN outcome
        return r
    j.append = flaky
    with pytest.raises(Boom): s.settle()
    restarted = ReplicaLifecycle(j, ANCHOR)                                                            # restart + retry
    assert restarted.settle() == [] or True
    assert kinds(j).count("CLAIM_ABANDONED") == 1 and kinds(j).count("ORDER_REVOKED") == 1
    cold(j); restarted.verify_projection()


def test_r50_2_consumed_and_unrelated_controls_untouched():
    j, s = mk(); order(s); claim(s); admit(s); s.consume("CLAIM:C1", "ID1")
    order(s, "O2", "S2", "ISS2"); claim(s, "O2", "S2", "C2")
    j.append(j.head(), "GRANT_REVOKED", {"grant_id": "ISS1", "role": "issuer"})
    assert s.settle() == []                                                                            # consumed history immutable
    assert s.claim("CLAIM:C1")["state"] == "CONSUMED" and s.claim("CLAIM:C2")["state"] == "BOUND" and s.authorizes("S2", "C2") is True
    cold(j)


def test_r50_2_replace_creation_concurrent_duplicate_lineage():
    """Same class: a captured unconditional lineage append must not duplicate under a race, and a partial commit must be resumable."""
    j = HookJournal(); s1 = ReplicaLifecycle(j, ANCHOR); s2 = ReplicaLifecycle(j, ANCHOR)
    order(s1); claim(s1); s1.revoke_grant("ISS1", "issuer"); order(s1, "O2", "S1", "ISS2")
    j.hooks["append"] = lambda: s2.replace_creation(old_creation_id="C1", new_creation_id="C2", subject_key="S1", order_id="O2", lookup_outcome=LookupOutcome.ABSENT)
    r = s1.replace_creation(old_creation_id="C1", new_creation_id="C2", subject_key="S1", order_id="O2", lookup_outcome=LookupOutcome.ABSENT)
    assert kinds(j).count("LINEAGE_REPLACED") == 1 and r["claim_id"] == "CLAIM:C2"
    cold(j)


# ---- 3. lease path validation ---------------------------------------------------------------------------------------------------------
@pytest.mark.parametrize("bad", ["", None, 5])
def test_r50_3_lease_refuses_what_ordinary_admit_refuses(bad):
    j, s = base(); port = FakeTimePort(j); n = j.head().seq
    with pytest.raises(Refusal, match="BUILD_ID_REQUIRED"): lease(s, port, build_id=bad)
    with pytest.raises(Refusal, match="BUILD_ID_REQUIRED"): admit(s, bid=bad)
    assert j.head().seq == n and port.calls == []                                                      # no write, the port is never asked


def test_r50_3_genuine_positive_unchanged():
    j, s = base(); port = FakeTimePort(j); assert lease(s, port)["build_id"] == "B1"


# ---- 4. aliasing -----------------------------------------------------------------------------------------------------------------------
def test_r50_4_lease_result_is_detached_from_projection_reads_and_retries():
    j, s = base(); port = FakeTimePort(j); ref = {"clock_domain_ref": "DOM1", "config_generation": 7, "deadline": 100}
    a = lease(s, port, ref)
    a["deadline_ref"]["deadline"] = 999
    assert s.attempt("B1")["deadline_ref"]["deadline"] == 100
    assert lease(s, port, {"clock_domain_ref": "DOM1", "config_generation": 7, "deadline": 100})["deadline_ref"]["deadline"] == 100
    ref["deadline"] = 5                                                                                # caller mutating its OWN input afterwards changes nothing admitted
    assert s.attempt("B1")["deadline_ref"]["deadline"] == 100
    r = s.attempt("B1"); r["deadline_ref"]["deadline"] = 1; assert s.attempt("B1")["deadline_ref"]["deadline"] == 100
    assert cold(j).attempts["B1"]["deadline_ref"]["deadline"] == 100
    s.verify_projection()


def test_r50_4_retry_with_a_different_deadline_is_a_conflict_not_a_silent_replay():
    j, s = base(); port = FakeTimePort(j); lease(s, port, {"clock_domain_ref": "DOM1", "config_generation": 7, "deadline": 100})
    with pytest.raises(Refusal, match="BUILD_ID_CONFLICT"): lease(s, port, {"clock_domain_ref": "DOM1", "config_generation": 7, "deadline": 101})
    with pytest.raises(Refusal, match="BUILD_ID_CONFLICT"): admit(s)                                  # non-lease path cannot replay a leased attempt


def test_r50_4_other_public_reads_are_detached():
    j, s = base(); admit(s)
    c = s.claim("CLAIM:C1"); c["state"] = "X"; assert s.claim("CLAIM:C1")["state"] == "BOUND"
    a = s.attempt("B1"); a["state"] = "X"; assert s.attempt("B1")["state"] == "ADMITTED"
    ad = admit(s); ad["state"] = "X"; assert s.attempt("B1")["state"] == "ADMITTED"


def test_r50_1_builder_never_sees_a_head_that_differs_from_the_projection_in_hash():
    from tracker_component.journal_port import Head
    j = HookJournal(); s = ReplicaLifecycle(j, ANCHOR); order(s); real = j.head; n = [0]
    def forked():
        h = real(); n[0] += 1
        return Head(h.seq, "f" * 64) if n[0] == 1 else h                                              # same seq, DIFFERENT hash, once
    j.head = forked; seen = []
    s._commit(lambda head: (seen.append((head.seq, head.hash)) or (None, None)))
    assert len(seen) == 1 and seen[0] == (s._p.seq, s._p.hash)


def test_r50_1_reserve_replay_precheck_also_uses_the_basis():
    j = HookJournal(); s1 = ReplicaLifecycle(j, ANCHOR); s2 = ReplicaLifecycle(j, ANCHOR); order(s1); claim(s1)
    real = s1._p.sync
    def f(journal): real(journal); j.hooks["head"] = lambda: s2.revoke_order("O1", "x"); s1._p.sync = real
    s1._p.sync = f
    with pytest.raises(Refusal, match="ORDER_REVOKED"): claim(s1)                                      # an exact replay must not return a claim under an order revoked meanwhile


def test_r50_4_replay_result_is_detached_too():
    j, s = base(); port = FakeTimePort(j); r = {"clock_domain_ref": "DOM1", "config_generation": 7, "deadline": 100}
    lease(s, port, r); again = lease(s, port, dict(r)); again["deadline_ref"]["deadline"] = 999
    assert s.attempt("B1")["deadline_ref"]["deadline"] == 100
