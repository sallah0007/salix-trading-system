import unittest
from stage_a.errors import Refusal, UnknownCommit, StaleFence
from stage_a.clocks import FixedClock, SystemClock
from stage_a.coordination import transition_record as T
from stage_a.coordination.attempt_time import append_with_attempt_time as awt, accepted_time_of, TIME_KEY
from stage_a.coordination.attempt_time import find_attempt, mint_fresh
from .test_foundations import mk, accepted_body

class Port:
    def __init__(self, start=100): self.n = start - 1; self.calls = 0
    def mint(self): self.n += 1; self.calls += 1; return self.n
def body_for(t): b = accepted_body(); b[TIME_KEY] = t; return b
def code(f, *a, **k):
    try: f(*a, **k)
    except Refusal as e: return e.code

class AttemptTime(unittest.TestCase):
    def test_unbound_identity_clock_and_malformed_ports_are_refused_and_write_nothing(self):
        s, j = mk(); h = j.head()
        self.assertEqual(code(awt, j, T.CANONICAL_ACCEPTED, body_for, None), "ATTEMPT_TIME_PORT_UNBOUND_HELD")
        self.assertEqual(code(awt, j, T.CANONICAL_ACCEPTED, body_for, SystemClock()), "ATTEMPT_TIME_PORT_IS_IDENTITY_CLOCK"); self.assertEqual(code(awt, j, T.CANONICAL_ACCEPTED, body_for, FixedClock()), "ATTEMPT_TIME_PORT_IS_IDENTITY_CLOCK")
        self.assertEqual(code(awt, j, T.CANONICAL_ACCEPTED, body_for, object()), "ATTEMPT_TIME_PORT_INVALID")
        for bad in (-1, True, 1.5, "5", 2**63):
            class P:
                def mint(self, v=bad): return v
            self.assertEqual(code(awt, j, T.CANONICAL_ACCEPTED, body_for, P()), "ATTEMPT_TIME_INVALID", repr(bad))
        self.assertEqual(j.head(), h)
    def test_positive_the_record_carries_the_minted_time_and_it_is_read_back(self):
        s, j = mk(); p = Port(); rec, t = awt(j, T.CANONICAL_ACCEPTED, body_for, p); self.assertEqual((t, p.calls, accepted_time_of(rec)), (100, 1, 100))
    def test_body_must_carry_exactly_the_time_it_was_built_from(self):
        s, j = mk(); self.assertEqual(code(awt, j, T.CANONICAL_ACCEPTED, lambda t: body_for(t + 1), Port()), "ATTEMPT_BODY_DOES_NOT_CARRY_ITS_TIME")
    def test_failed_cas_remints_and_the_old_time_hash_and_key_are_not_reused(self):
        s, j = mk(); p = Port(); other = []
        def build(t):
            if not other: other.append(j.append(j.head(), T.CANONICAL_ACCEPTED, accepted_body(v="9")))    # a rival lands between our HEAD read and our append: our CAS fails
            return body_for(t)
        rec, t = awt(j, T.CANONICAL_ACCEPTED, build, p)
        self.assertEqual((p.calls, t), (2, 101)); self.assertEqual(accepted_time_of(rec), 101); self.assertEqual(rec.seq, 2)           # attempt 1 (t=100) was discarded; attempt 2 minted a NEW time
        self.assertNotIn(100, [accepted_time_of(r) for r in j.read_from(1)])
    def test_unknown_commit_that_actually_landed_returns_the_SAME_record_and_time_without_remint(self):
        s, j = mk(); p = Port(); real = s.put_if_match
        def lose(key, data, etag):
            ok = real(key, data, etag)
            if ok and key.startswith("head/") and not getattr(lose, "done", False): lose.done = True; raise UnknownCommit("ack lost")
            return ok
        s.put_if_match = lose; rec, t = awt(j, T.CANONICAL_ACCEPTED, body_for, p)
        self.assertEqual((p.calls, t, accepted_time_of(rec)), (1, 100, 100)); self.assertEqual(len(j.read_from(1)), 1)
    def test_unknown_commit_proven_not_committed_mints_a_new_attempt_time(self):
        s, j = mk(); p = Port(); real = s.put_if_match
        def drop(key, data, etag):
            if key.startswith("head/") and not getattr(drop, "done", False): drop.done = True; raise UnknownCommit("dropped")
            return real(key, data, etag)
        s.put_if_match = drop; rec, t = awt(j, T.CANONICAL_ACCEPTED, body_for, p)
        self.assertEqual((p.calls, t), (2, 101)); self.assertEqual([accepted_time_of(r) for r in j.read_from(1)], [101])
    def test_retry_exhaustion_and_legacy_records_have_no_fabricated_time(self):
        s, j = mk(); r = j.append(j.head(), T.CANONICAL_ACCEPTED, accepted_body()); self.assertIsNone(accepted_time_of(r))              # legacy body: None, never invented
        s2, j2 = mk(); real = s2.put_if_match
        def always_drop(key, data, etag):
            if key.startswith("head/"): raise UnknownCommit("dropped")
            return real(key, data, etag)
        s2.put_if_match = always_drop; self.assertEqual(code(awt, j2, T.CANONICAL_ACCEPTED, body_for, Port(), max_attempts=3), "ATTEMPT_TIME_RETRY_EXHAUSTED")
    def test_a_port_that_repeats_its_value_is_refused_not_trusted_to_be_fresh(self):
        class Const:
            def mint(self): return 100
        self.assertEqual(code(mint_fresh, Const(), {100}), "ATTEMPT_TIME_NOT_FRESH")
        s, j = mk(); other = []
        def build(t):
            if not other: other.append(j.append(j.head(), T.CANONICAL_ACCEPTED, accepted_body(v="9")))
            return body_for(t)
        self.assertEqual(code(awt, j, T.CANONICAL_ACCEPTED, build, Const()), "ATTEMPT_TIME_NOT_FRESH")          # CAS lost, retry minted the same value: refused, nothing written for it
        self.assertEqual(len(j.read_from(1)), 1)
    def test_unknown_commit_is_resolved_for_the_SPECIFIC_attempt_position_not_a_chain_wide_body_match(self):
        s, j = mk(); h0 = j.head(); b = body_for(5); r1 = j.append(h0, T.CANONICAL_ACCEPTED, b); h1 = j.head()
        from tracker_component.canonical import canonical_json
        self.assertIsNone(find_attempt(j, h1, T.CANONICAL_ACCEPTED, canonical_json(b)))          # an identical body earlier in the chain is NOT this attempt (old kind+body matching would say COMMITTED)
        self.assertEqual(find_attempt(j, h0, T.CANONICAL_ACCEPTED, canonical_json(b)).record_hash, r1.record_hash)
    def test_the_largest_i64_is_accepted_and_the_next_value_is_refused_at_the_record_validator_too(self):
        class P:
            def __init__(self, v): self.v = v
            def mint(self): return self.v
        s, j = mk(); rec, t = awt(j, T.CANONICAL_ACCEPTED, body_for, P(2**63 - 1)); self.assertEqual(accepted_time_of(rec), 2**63 - 1)
        b = accepted_body(); b[TIME_KEY] = 2**63
        self.assertEqual(code(T.validate_body, T.CANONICAL_ACCEPTED, b), "TRANSITION_ACCEPTED_AT_INVALID")
