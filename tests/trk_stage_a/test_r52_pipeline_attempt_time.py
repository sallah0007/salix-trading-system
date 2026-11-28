"""R52 E03-F1: the supplied candidate acceptance-time port through the REAL pipeline acceptor. Candidate/simulation only: a plain supplied port is not an admitted clock; nothing is qualified by it."""
import unittest
from unittest import mock
from stage_a.errors import Refusal, UnknownCommit
from stage_a.replay import replay
from stage_a.coordination.attempt_time import accepted_time_of, TIME_KEY
from stage_a.coordination.object_store_journal import ObjectStoreJournal
from tracker_component.journal_port import HeadMismatch
from .fixtures import Rig, package
NS = "XAUUSD/H4/mom3"
class Port:
    def __init__(self, v=100): self.n = v - 1; self.calls = 0
    def mint(self): self.n += 1; self.calls += 1; return self.n
def run(port, wrap=None):
    r = Rig(simulation=True, attempt_time_port=port); p = package(); r.issue(p)
    if wrap is None: return r, r.pipe.run(p)
    real = ObjectStoreJournal.append; state = {"n": 0}
    def app(self, head, kind, body):
        state["n"] += 1
        if kind != "CANONICAL_ACCEPTED": return real(self, head, kind, body)
        return wrap(real, state, self, head, kind, body)
    with mock.patch.object(ObjectStoreJournal, "append", app): return r, r.pipe.run(p)
def accepted(r): return [x for x in r.journals.journal(NS).read_from(1) if x.kind == "CANONICAL_ACCEPTED"]
class PipelineAttemptTime(unittest.TestCase):
    def test_no_port_writes_no_time_and_history_reads_as_unknown(self):
        r, o = run(None); self.assertTrue(o.accepted_ok); self.assertIsNone(accepted_time_of(accepted(r)[0]))
    def test_port_time_is_in_the_committed_body_replays_and_validates(self):
        pt = Port(); r, o = run(pt); self.assertTrue(o.accepted_ok); a = accepted(r); self.assertEqual((len(a), accepted_time_of(a[0]), pt.calls), (1, 100, 1))
        self.assertEqual([s.status for s in replay(NS, r.journals.journal(NS).read_from(1)).values()], ["CANONICAL_ACCEPTED"])
    def test_known_failed_cas_rebuilds_with_a_new_time_hash(self):
        def w(real, st, self, head, kind, body):
            if st.setdefault("hm", 0) == 0: st["hm"] = 1; st["first"] = body[TIME_KEY]; raise HeadMismatch(head, head)
            return real(self, head, kind, body)
        pt = Port(); r, o = run(pt, w); a = accepted(r)
        self.assertTrue(o.accepted_ok); self.assertEqual((len(a), accepted_time_of(a[0]), pt.calls), (1, 101, 2))
    def test_unknown_commit_that_landed_returns_the_same_record_and_time_without_remint(self):
        def w(real, st, self, head, kind, body):
            rec = real(self, head, kind, body); raise UnknownCommit("ack lost")
        pt = Port(); r, o = run(pt, w); a = accepted(r)
        self.assertTrue(o.accepted_ok); self.assertEqual((len(a), accepted_time_of(a[0]), pt.calls), (1, 100, 1))
    def test_unknown_commit_not_landed_mints_a_new_time_on_the_new_attempt(self):
        def w(real, st, self, head, kind, body):
            if st.setdefault("d", 0) == 0: st["d"] = 1; raise UnknownCommit("dropped")
            return real(self, head, kind, body)
        pt = Port(); r, o = run(pt, w); a = accepted(r); self.assertEqual((len(a), accepted_time_of(a[0]), pt.calls), (1, 101, 2))
    def test_a_non_fresh_port_is_refused_on_retry_and_nothing_is_accepted(self):
        class Const:
            def mint(self): return 100
        def w(real, st, self, head, kind, body):
            if st.setdefault("hm", 0) == 0: st["hm"] = 1; raise HeadMismatch(head, head)
            return real(self, head, kind, body)
        with self.assertRaises(Refusal) as c: run(Const(), w)
        self.assertEqual(c.exception.code, "ATTEMPT_TIME_NOT_FRESH")
    def test_bad_ports_are_refused_at_construction(self):
        from stage_a.clocks import SystemClock
        for bad, code in ((SystemClock(), "ATTEMPT_TIME_PORT_IS_IDENTITY_CLOCK"), (object(), "ATTEMPT_TIME_PORT_INVALID")):
            with self.assertRaises(Refusal) as c: Rig(simulation=True, attempt_time_port=bad)
            self.assertEqual(c.exception.code, code)
