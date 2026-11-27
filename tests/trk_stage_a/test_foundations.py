import json, threading, unittest
from tracker_component.journal_port import Head, HeadMismatch, GENESIS_HEAD
from stage_a.errors import Refusal, StaleFence, UnknownCommit, IntegrityFailure
from stage_a.identifiers import Scope, FeatureKey, check_token
from stage_a.clocks import Stamp, IDENTITY, CAUSAL, require_kind, FixedClock
from stage_a.authority import AuthorityRef
from stage_a.storage.object_store import InMemoryObjectStore
from stage_a.storage.keys import journal_key, head_key, artifact_key
from stage_a.coordination.object_store_journal import ObjectStoreJournal
from stage_a.coordination import transition_record as T
from stage_a.coordination.recovery import resolve_unknown_commit, find_orphans, cold_rebuild_head, COMMITTED, NOT_COMMITTED
from stage_a.coordination.scheduler import ReplayScheduler
from stage_a.coordination.fencing import acquire, assert_current
from stage_a.storage.postgres_read_model import ReadModel
from stage_a.replay import replay
from stage_a.currentness import resolve_asof, AS_KNOWN, EVENTUAL

NS = "XAUUSD/H4/mom3"
def accepted_body(v="1", vh="v" * 64):
    return {"feature_key": "%s/%s" % (NS, v), "feature_version": v, "manifest_hash": "m" * 64, "graph_hash": "g" * 64,
            "program_hash": "p" * 64, "attempt_id": "A", "verification_hash": vh, "certification_hash": "c" * 64,
            "claim_witness": "claims#1:" + "w" * 64, "safe_intake_report_hash": "r" * 64, "materialization_hash": "m" * 64}
def pub_body(st, v="1", vh="v" * 64):
    return {"feature_key": "%s/%s" % (NS, v), "feature_version": v, "accepted_seq": st[0], "accepted_hash": st[1], "verification_hash": vh}

def mk(store=None, ns=NS, w="w1"):
    s = store or InMemoryObjectStore()
    j = ObjectStoreJournal(s, ns, w); j.acquire_epoch()
    return s, j

class Identifiers(unittest.TestCase):
    def test_scope_isolation_keys_differ(self):
        a = FeatureKey(Scope("XAUUSD", "H4"), "f", "1"); b = FeatureKey(Scope("EURUSD", "H4"), "f", "1")
        c = FeatureKey(Scope("XAUUSD", "H1"), "f", "1")
        self.assertEqual(len({a.key(), b.key(), c.key()}), 3)
        self.assertEqual(len({a.namespace(), b.namespace(), c.namespace()}), 3)
    def test_bad_tokens_refused(self):
        for bad in ("", "a/b", "../x", "a b", "x" * 80, None, "-x"):
            with self.assertRaises(Refusal): check_token(bad, "t")
    def test_authority_ref_roundtrip_and_malformed(self):
        r = AuthorityRef("XAUUSD/H4/f", 3, "a" * 64)
        self.assertEqual(AuthorityRef.parse(r.to_str()), r)
        for bad in ("", "ACCEPTED:x", "LATEST:ns#1:" + "a" * 64, "ACCEPTED:ns#x:" + "a" * 64):
            with self.assertRaises(Refusal): AuthorityRef.parse(bad)

class Clocks(unittest.TestCase):
    def test_kinds_not_interchangeable(self):
        s = Stamp(CAUSAL, "2026-01-01T00:00:00+00:00")
        with self.assertRaises(Refusal): require_kind(s, IDENTITY)
        self.assertIs(require_kind(s, CAUSAL), s)
    def test_naive_and_garbage_refused(self):
        for bad in ("2026-01-01T00:00:00", "nope"):
            with self.assertRaises(Refusal): Stamp(IDENTITY, bad)

class Journal(unittest.TestCase):
    def test_append_read_roundtrip_and_chain(self):
        s, j = mk()
        h = j.head(); self.assertEqual(h, GENESIS_HEAD)
        r1 = j.append(h, T.CANONICAL_ACCEPTED, accepted_body())
        r2 = j.append(Head(r1.seq, r1.record_hash), T.PUBLISHABLE, pub_body((r1.seq, r1.record_hash)))
        self.assertEqual([r.seq for r in j.read_from(1)], [1, 2])
        self.assertEqual(cold_rebuild_head(j), Head(2, r2.record_hash))
    def test_stale_expected_head_is_mismatch(self):
        s, j = mk(); r = j.append(j.head(), T.CANONICAL_ACCEPTED, accepted_body())
        with self.assertRaises(HeadMismatch): j.append(GENESIS_HEAD, T.WITHDRAWN, {"x": 1})
    def test_append_without_epoch_refused(self):
        j = ObjectStoreJournal(InMemoryObjectStore(), NS, "w")
        with self.assertRaises(Refusal) as c: j.append(GENESIS_HEAD, "K", {})
        self.assertEqual(c.exception.code, "NO_EPOCH")
    def test_fenced_out_writer_cannot_commit_and_leaves_no_authority(self):
        s, old = mk(w="old")
        new = ObjectStoreJournal(s, NS, "new"); new.acquire_epoch()
        with self.assertRaises(StaleFence): old.append(old.head(), T.CANONICAL_ACCEPTED, accepted_body())
        self.assertFalse(old.epoch_is_current()); self.assertTrue(new.epoch_is_current())
        self.assertEqual(new.read_from(1), [])
        from stage_a.coordination.fencing import Fence
        with self.assertRaises(StaleFence): assert_current(old, Fence(NS, 1))
        assert_current(new, Fence(NS, 2))
    def test_writer_fenced_between_check_and_cas_leaves_orphan_that_does_not_block_new_epoch(self):
        s, old = mk(w="old")
        h = old.head()
        # simulate: old writer wrote its record object, then lost the epoch before the HEAD swap
        real_put_if_match = s.put_if_match
        fired = []
        def interfering(key, data, etag):
            if not fired:
                fired.append(1)
                ObjectStoreJournal(s, NS, "new").acquire_epoch()      # new epoch lands first
            return real_put_if_match(key, data, etag)
        s.put_if_match = interfering
        with self.assertRaises(StaleFence): old.append(h, T.CANONICAL_ACCEPTED, accepted_body())
        s.put_if_match = real_put_if_match
        new = ObjectStoreJournal(s, NS, "new2"); new.acquire_epoch()
        r = new.append(new.head(), T.CANONICAL_ACCEPTED, accepted_body(vh="x" * 64))
        self.assertEqual(r.seq, 1)
        orphans = find_orphans(s, NS, new)
        self.assertEqual(len(orphans), 1)                      # old writer's object: present, unreferenced, authority-free
        self.assertEqual([x.record_hash for x in new.read_from(1)], [r.record_hash])
    def test_concurrent_writers_single_winner_per_seq(self):
        s, j0 = mk()
        base = j0.head(); results = []
        js = []
        for i in range(6):
            pass
        # all contenders share one epoch holder (same journal object) but race on the same expected head
        def go(i):
            try:
                j0.append(base, T.CANONICAL_ACCEPTED, accepted_body(v=str(i)))
                results.append("ok")
            except HeadMismatch:
                results.append("lost")
        ts = [threading.Thread(target=go, args=(i,)) for i in range(6)]
        [t.start() for t in ts]; [t.join() for t in ts]
        self.assertEqual(results.count("ok"), 1); self.assertEqual(len(j0.read_from(1)), 1)
    def test_unknown_commit_ack_lost_resolves_committed(self):
        s, j = mk(); body = accepted_body()
        s.lose_ack_on_next_write = False
        # fault on the HEAD swap: 2nd conditional write of the append (1st is the record object)
        real = s.put_if_match
        def lose(key, data, etag):
            ok = real(key, data, etag)
            if ok and key.startswith("head/"): raise UnknownCommit("ack lost")
            return ok
        s.put_if_match = lose
        with self.assertRaises(UnknownCommit): j.append(j.head(), T.CANONICAL_ACCEPTED, body)
        s.put_if_match = real
        from tracker_component.canonical import canonical_json
        self.assertEqual(resolve_unknown_commit(j, kind=T.CANONICAL_ACCEPTED, body_json=canonical_json(body)), COMMITTED)
    def test_unknown_commit_dropped_write_resolves_not_committed(self):
        s, j = mk(); body = accepted_body()
        real = s.put_if_match
        def drop(key, data, etag):
            if key.startswith("head/"): raise UnknownCommit("dropped")
            return real(key, data, etag)
        s.put_if_match = drop
        with self.assertRaises(UnknownCommit): j.append(j.head(), T.CANONICAL_ACCEPTED, body)
        s.put_if_match = real
        from tracker_component.canonical import canonical_json
        self.assertEqual(resolve_unknown_commit(j, kind=T.CANONICAL_ACCEPTED, body_json=canonical_json(body)), NOT_COMMITTED)
        self.assertEqual(len(find_orphans(s, NS, j)), 1)
    def test_tampered_record_detected_on_read(self):
        s, j = mk(); r = j.append(j.head(), T.CANONICAL_ACCEPTED, accepted_body())
        key = journal_key(NS, 1, r.record_hash)
        blob = json.loads(s.get(key)[0]); blob["body_json"] = blob["body_json"].replace("mom", "xxx").replace('"A"', '"B"')
        s._d[key] = (json.dumps(blob).encode(), 99)
        with self.assertRaises(IntegrityFailure): j.read_from(1)
    def test_head_pointing_at_missing_record_detected(self):
        s, j = mk(); r = j.append(j.head(), T.CANONICAL_ACCEPTED, accepted_body())
        del s._d[journal_key(NS, 1, r.record_hash)]
        with self.assertRaises(IntegrityFailure): j.read_from(1)
    def test_separate_namespaces_do_not_share_state(self):
        s = InMemoryObjectStore()
        _, a = mk(s, "XAUUSD/H4/f"); _, b = mk(s, "EURUSD/H4/f")
        a.append(a.head(), "K", {"x": 1})
        self.assertEqual(b.head(), GENESIS_HEAD)
    def test_cold_rebuild_equals_live_after_restart(self):
        s, j = mk(); r = j.append(j.head(), T.CANONICAL_ACCEPTED, accepted_body())
        j2 = ObjectStoreJournal(s, NS, "restarted")   # no epoch needed for reads
        self.assertEqual(cold_rebuild_head(j2), Head(1, r.record_hash))
    def test_bad_namespace_refused(self):
        for bad in ("", "../x", "/abs", "a//b"):
            with self.assertRaises(Refusal): head_key(bad)

class Scheduler(unittest.TestCase):
    def test_budget_exceeded_is_refusal_not_truncation(self):
        with self.assertRaises(Refusal) as c: ReplayScheduler(3, 2).plan({"a": [1, 2], "b": [3, 4]})
        self.assertEqual(c.exception.code, "REPLAY_BUDGET_EXCEEDED")
    def test_round_robin_fairness_and_batch_cap(self):
        b = ReplayScheduler(10, 2).plan({"b": [1, 2, 3], "a": [4]})
        self.assertTrue(all(len(x) <= 2 for x in b))
        self.assertEqual([ns for ns, _ in b[0]], ["a", "b"])
        self.assertEqual(sum(len(x) for x in b), 4)

class Replay(unittest.TestCase):
    def build(self):
        s, j = mk()
        r1 = j.append(j.head(), T.CANONICAL_ACCEPTED, accepted_body())
        r2 = j.append(j.head(), T.PUBLISHABLE, pub_body((1, r1.record_hash)))
        r3 = j.append(j.head(), T.WITHDRAWN, {"feature_key": NS + "/1", "feature_version": "1", "reason": "x"})
        return s, j, (r1, r2, r3)
    def test_replay_states(self):
        _, j, _ = self.build()
        st = replay(NS, j.read_from(1))
        self.assertEqual(st["1"].status, "WITHDRAWN")
    def test_illegal_transition_refused(self):
        s, j = mk()
        j.append(j.head(), T.WITHDRAWN, {"feature_key": NS + "/1", "feature_version": "1", "reason": "x"})
        with self.assertRaises(Refusal): replay(NS, j.read_from(1))
    def test_publishable_binding_must_match_accepted(self):
        s, j = mk(); r1 = j.append(j.head(), T.CANONICAL_ACCEPTED, accepted_body())
        j.append(j.head(), T.PUBLISHABLE, pub_body((1, "0" * 64)))
        with self.assertRaises(Refusal) as c: replay(NS, j.read_from(1))
        self.assertEqual(c.exception.code, "PUBLISHABLE_BINDING_MISMATCH")
    def test_repeated_publishable_and_publish_after_withdraw_refused(self):
        s, j = mk(); r1 = j.append(j.head(), T.CANONICAL_ACCEPTED, accepted_body())
        j.append(j.head(), T.PUBLISHABLE, pub_body((1, r1.record_hash)))
        j.append(j.head(), T.PUBLISHABLE, pub_body((1, r1.record_hash)))
        with self.assertRaises(Refusal) as c: replay(NS, j.read_from(1))
        self.assertEqual(c.exception.code, "ILLEGAL_TRANSITION")
        s, j = mk(); r1 = j.append(j.head(), T.CANONICAL_ACCEPTED, accepted_body())
        j.append(j.head(), T.WITHDRAWN, {"feature_key": NS + "/1", "feature_version": "1", "reason": "x"})
        j.append(j.head(), T.PUBLISHABLE, pub_body((1, r1.record_hash)))
        with self.assertRaises(Refusal): replay(NS, j.read_from(1))
    def test_duplicate_acceptance_of_same_version_refused(self):
        s, j = mk(); j.append(j.head(), T.CANONICAL_ACCEPTED, accepted_body())
        j.append(j.head(), T.CANONICAL_ACCEPTED, accepted_body())
        with self.assertRaises(Refusal): replay(NS, j.read_from(1))
    def test_cross_namespace_record_refused(self):
        s, j = mk(); b = accepted_body(); b["feature_key"] = "EURUSD/H4/mom3/1"
        j.append(j.head(), T.CANONICAL_ACCEPTED, b)
        with self.assertRaises(Refusal) as c: replay(NS, j.read_from(1))
        self.assertEqual(c.exception.code, "CROSS_NAMESPACE_RECORD")
    def test_incomplete_or_extra_body_refused(self):
        for mutate in (lambda b: b.pop("manifest_hash"), lambda b: b.update(extra=1)):
            s, j = mk(); b = accepted_body(); mutate(b)
            j.append(j.head(), T.CANONICAL_ACCEPTED, b)
            with self.assertRaises(Refusal): replay(NS, j.read_from(1))

class Currentness(unittest.TestCase):
    def setUp(self):
        s, j = mk(); self.j = j
        a = j.append(j.head(), T.CANONICAL_ACCEPTED, accepted_body())              # seq1
        p = j.append(j.head(), T.PUBLISHABLE, pub_body((1, a.record_hash)))        # seq2
        self.w = j.append(j.head(), T.WITHDRAWN, {"feature_key": NS + "/1", "feature_version": "1", "reason": "r"})  # seq3
    def test_as_known_does_not_see_later_withdrawal(self):
        r = resolve_asof(NS, self.j.read_from(1), mode=AS_KNOWN, asof_seq=2)
        self.assertEqual(r.available_version, "1")
    def test_eventual_sees_withdrawal(self):
        r = resolve_asof(NS, self.j.read_from(1), mode=EVENTUAL)
        self.assertIsNone(r.available_version)
    def test_as_known_before_publication_has_nothing_available(self):
        self.assertIsNone(resolve_asof(NS, self.j.read_from(1), mode=AS_KNOWN, asof_seq=1).available_version)
    def test_mode_misuse_refused(self):
        recs = self.j.read_from(1)
        for kw in (dict(mode=AS_KNOWN), dict(mode=EVENTUAL, asof_seq=2), dict(mode="LATEST"), dict(mode=AS_KNOWN, asof_seq=True)):
            with self.assertRaises(Refusal): resolve_asof(NS, recs, **kw)
    def test_technical_latest_object_is_not_authority(self):
        # a newer-looking object that is not on the accepted chain must not change resolution
        s, j = mk(); a = j.append(j.head(), T.CANONICAL_ACCEPTED, accepted_body())
        s.put_if_absent(journal_key(NS, 2, "f" * 64), b'{"fake":"record"}')
        self.assertEqual([r.seq for r in j.read_from(1)], [1])

class ReadModelTests(unittest.TestCase):
    def test_rebuild_query_and_staleness(self):
        s, j = mk(); a = j.append(j.head(), T.CANONICAL_ACCEPTED, accepted_body())
        rm = ReadModel()
        with self.assertRaises(Refusal): rm.status(NS, "1", j)          # never built -> stale
        rm.rebuild(NS, j); self.assertEqual(rm.status(NS, "1", j), "CANONICAL_ACCEPTED")
        j.append(j.head(), T.PUBLISHABLE, pub_body((1, a.record_hash)))
        with self.assertRaises(Refusal) as c: rm.status(NS, "1", j)     # journal moved -> stale sidecar refused
        self.assertEqual(c.exception.code, "STALE_READ_MODEL")
        rm.rebuild(NS, j); rm.verify_against(NS, j); self.assertEqual(rm.status(NS, "1", j), "PUBLISHABLE")
    def test_drift_detected(self):
        s, j = mk(); j.append(j.head(), T.CANONICAL_ACCEPTED, accepted_body())
        rm = ReadModel(); rm.rebuild(NS, j)
        rm._c.execute("UPDATE status SET status='PUBLISHABLE'")
        with self.assertRaises(IntegrityFailure): rm.verify_against(NS, j)

if __name__ == "__main__":
    unittest.main()
