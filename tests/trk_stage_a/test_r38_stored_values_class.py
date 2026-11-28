"""R38 finding 3: stored-value maintenance requires ONE class across Core plane, accepted journal and store before any write."""
import unittest
from stage_a.errors import Refusal
from stage_a.core.tracker_core import TrackerCore
from stage_a.coordination.object_store_journal import ObjectStoreJournal
from stage_a.storage.object_store import InMemoryObjectStore
from stage_a.tracker import stored_values as SV
from .test_r37_stored_values import Stored, code
from .test_r25_scheduler import core
def qcore():
    j = ObjectStoreJournal(InMemoryObjectStore(), "qcore", "w"); j.acquire_epoch(); return TrackerCore(j, simulation=False)
class Cls(Stored):
    def test_a_qualified_core_over_a_sim_accepted_journal_and_sim_store_writes_nothing(self):
        self.put(); q = qcore(); h0 = q._j.head()
        self.assertEqual(code(SV.record_stored_value_maintenance, q, now=10, max_age=50, **self.kw), "STORED_VALUES_CLASS_MISMATCH")
        self.assertEqual(q._j.head(), h0)                                    # no l2 PASS filed into the ordinary Core HEAD
    def test_a_sim_core_with_an_ordinary_store_or_ordinary_journal_is_refused(self):
        c = core(); sj = c._j.head()
        q_store = InMemoryObjectStore(); qj = ObjectStoreJournal(q_store, "ord", "w"); qj.acquire_epoch()
        self.assertEqual(code(SV.record_stored_value_maintenance, c, now=10, max_age=50, **dict(self.kw, store=q_store)), "STORED_VALUES_CLASS_MISMATCH")
        self.assertEqual(code(SV.record_stored_value_maintenance, c, now=10, max_age=50, **dict(self.kw, journal=qj)), "STORED_VALUES_CLASS_MISMATCH")
        self.assertEqual(c._j.head(), sj)
    def test_persist_refuses_a_journal_store_class_mismatch_before_writing(self):
        s = InMemoryObjectStore(); qj = ObjectStoreJournal(s, "ord", "w"); qj.acquire_epoch()
        self.assertEqual(code(SV.persist_stored_values, **dict(self.kw, journal=qj)), "STORED_VALUES_CLASS_MISMATCH"); self.assertNotIn(self.raw_key(), self.rig.raw_store._d)
    def test_same_class_sim_positive_still_records(self):
        c = core(); self.put(); r = SV.record_stored_value_maintenance(c, now=12, max_age=50, **self.kw); self.assertEqual((r["l1"], r["l2"]), ("PASS", "PASS"))
Cls.__test__ = True
del Stored
if __name__ == "__main__": unittest.main()
