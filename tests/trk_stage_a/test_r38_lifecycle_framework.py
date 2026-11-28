import unittest
from stage_a.errors import Refusal
from stage_a.storage.object_store import InMemoryObjectStore
from stage_a.coordination.object_store_journal import ObjectStoreJournal
from stage_a.coordination.lifecycle_framework import LifecycleFramework as LF, LifecyclePolicy as LP
def code(f, *a, **k):
    try: f(*a, **k)
    except Refusal as e: return e.code
def J():
    j = ObjectStoreJournal(InMemoryObjectStore(), "lc", "w"); j.acquire_epoch(); return j
POL = LP(("A", "B", "C"), frozenset({(None, "A"), ("A", "B"), ("B", "C")}), frozenset({"C"}), "TEST-POLICY-NOT-A-SOURCE-GRAPH")       # a TEST policy, not any source's graph
OK = lambda s, f, t, e: e == "good"
class Lc(unittest.TestCase):
    def test_unbound_policy_refuses_everything_and_writes_nothing(self):
        j = J(); f = LF(j); self.assertEqual(code(f.apply, "s", "t1", None, "A", "good"), "LIFECYCLE_POLICY_HELD"); self.assertEqual(code(f.state_of, "s"), "LIFECYCLE_POLICY_HELD"); self.assertEqual(j.head().seq, 0)
    def test_lawful_chain_idempotent_retry_and_reused_id(self):
        f = LF(J(), POL, OK); f.apply("s", "t1", None, "A", "good"); self.assertIsNone(f.apply("s", "t1", None, "A", "good")); f.apply("s", "t2", "A", "B", "good"); self.assertEqual(f.state_of("s"), "B"); self.assertEqual(code(f.apply, "s", "t1", None, "B", "good"), "LIFECYCLE_TRANSITION_ID_REUSED_DIFFERENTLY")
    def test_policy_from_state_unknown_state_terminal_and_skip_refusals_write_nothing(self):
        j = J(); f = LF(j, POL, OK); f.apply("s", "t1", None, "A", "good"); h = j.head()
        self.assertEqual(code(f.apply, "s", "t2", "A", "C", "good"), "LIFECYCLE_TRANSITION_NOT_ALLOWED_BY_POLICY"); self.assertEqual(code(f.apply, "s", "t3", "B", "C", "good"), "LIFECYCLE_FROM_STATE_MISMATCH"); self.assertEqual(code(f.apply, "s", "t4", "A", "ZZ", "good"), "LIFECYCLE_INPUT_INVALID")
        f.apply("s", "t5", "A", "B", "good"); f.apply("s", "t6", "B", "C", "good"); self.assertEqual(code(f.apply, "s", "t7", "C", "A", "good"), "LIFECYCLE_TERMINAL_STATE"); self.assertEqual(j.head().seq, 3)
    def test_evidence_is_required_and_the_checker_must_accept_signer_style_refs_are_not_enough(self):
        j = J(); self.assertEqual(code(LF(j, POL).apply, "s", "t1", None, "A", "good"), "LIFECYCLE_EVIDENCE_CHECK_HELD"); f = LF(j, POL, OK)
        self.assertEqual(code(f.apply, "s", "t1", None, "A", "OWNER-SIGNED"), "LIFECYCLE_EVIDENCE_NOT_ACCEPTED"); self.assertEqual(code(f.apply, "s", "t1", None, "A", ""), "LIFECYCLE_INPUT_INVALID")
        def boom(*a): raise Refusal("x", code="EVIDENCE_NOT_VALID_AT_USE")
        self.assertEqual(code(LF(j, POL, boom).apply, "s", "t1", None, "A", "good"), "LIFECYCLE_EVIDENCE_NOT_ACCEPTED"); self.assertEqual(j.head().seq, 0)
    def test_stale_expected_head_refuses_and_subjects_are_independent(self):
        j = J(); f = LF(j, POL, OK); h0 = j.head(); f.apply("s1", "t1", None, "A", "good"); self.assertEqual(code(f.apply, "s2", "t2", None, "A", "good", expected_head=h0), "LIFECYCLE_STALE_HEAD"); f.apply("s2", "t2", None, "A", "good", expected_head=j.head()); self.assertEqual((f.state_of("s1"), f.state_of("s2")), ("A", "A"))
    def test_bad_policy_is_refused_and_state_is_replayed_after_restart(self):
        self.assertEqual(code(LP, ("A",), frozenset({("A", "Q")}), frozenset(), "r"), "LIFECYCLE_POLICY_INVALID"); self.assertEqual(code(LP, ("A", "A"), frozenset(), frozenset(), "r"), "LIFECYCLE_POLICY_INVALID")
        j = J(); LF(j, POL, OK).apply("s", "t1", None, "A", "good"); self.assertEqual(LF(j, POL, OK).state_of("s"), "A")
if __name__ == "__main__": unittest.main()
