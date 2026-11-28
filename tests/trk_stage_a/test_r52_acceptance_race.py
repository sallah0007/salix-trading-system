"""R52 (Manager 21:31): the acceptor must pin ONE HEAD basis before its replay/semantic decision and CAS against that same basis. A port that interleaves a rival public run for the same package between decision and append must not produce a second CANONICAL_ACCEPTED. Candidate/SIM only."""
import unittest
from stage_a.errors import Refusal
from stage_a.replay import replay
from stage_a.coordination.attempt_time import accepted_time_of
from .fixtures import Rig, package
NS = "XAUUSD/H4/mom3"
class Port:
    def __init__(self, go=None): self.n = 100; self.go = go; self.fired = False; self.inner = None
    def mint(self):
        if self.go is not None and not self.fired:
            self.fired = True; self.inner = self.go()
        self.n += 1; return self.n
def acc(r): return [x for x in r.journals.journal(NS).read_from(1) if x.kind == "CANONICAL_ACCEPTED"]
class AcceptanceRace(unittest.TestCase):
    def test_interleaved_rival_run_of_the_same_package_yields_ONE_acceptance_and_a_replayable_journal(self):
        pt = Port(); r = Rig(attempt_time_port=pt); p = package(); r.issue(p); pt.go = lambda: r.pipe.run(p)
        o = r.pipe.run(p); a = acc(r)
        self.assertTrue(o.accepted_ok and pt.inner.accepted_ok); self.assertEqual(len(a), 1)
        self.assertEqual([s.status for s in replay(NS, r.journals.journal(NS).read_from(1)).values()], ["CANONICAL_ACCEPTED"])          # no ILLEGAL_TRANSITION
        self.assertEqual(accepted_time_of(a[0]), 101)          # the rival's attempt time won; the outer attempt's time (102) was discarded and nothing remints for a landed replay
    def test_sequential_honest_retry_control_still_one_record(self):
        pt = Port(); r = Rig(attempt_time_port=pt); p = package(); r.issue(p)
        o1 = r.pipe.run(p); o2 = r.pipe.run(p); self.assertTrue(o1.accepted_ok and o2.accepted_ok); self.assertEqual(len(acc(r)), 1)
    def test_no_port_interleaving_is_not_needed_for_the_single_run_positive(self):
        r = Rig(); p = package(); r.issue(p); self.assertTrue(r.pipe.run(p).accepted_ok); self.assertEqual(len(acc(r)), 1)
