import unittest
from stage_a.errors import Refusal
from stage_a.storage.object_store import InMemoryObjectStore
from stage_a.coordination.object_store_journal import ObjectStoreJournal
from stage_a.tracker.research_lineage import ResearchLineage, STATUSES
def code(f, *a, **k):
    try: f(*a, **k)
    except Refusal as e: return e.code
def L():
    j = ObjectStoreJournal(InMemoryObjectStore(), "lin", "w"); j.acquire_epoch(); l = ResearchLineage(j); l.register_battery("F", "B1"); return l
def att(l, i, status="COMPLETED", **o): d = dict(attempt_id=i, family="F", battery="B1", input_ref="in", input_hash="h", params_hash="p" + i, status=status, outcome_ref="o" + i); d.update(o); return l.record_attempt(**d)
class Lin(unittest.TestCase):
    def test_count_is_derived_includes_rejected_and_idempotent_retry_does_not_inflate(self):
        l = L(); att(l, "a1"); att(l, "a2", "REJECTED"); att(l, "a3", "FAILED"); self.assertIsNone(att(l, "a1")); f = l.multiplicity_facts("F", "B1"); self.assertEqual((f["attempts"], f["by_status"], f["inference"]), (3, {"COMPLETED": 1, "FAILED": 1, "REJECTED": 1}, "NONE_COUNTS_ONLY"))
    def test_selection_must_declare_the_exact_ledger_multiplicity_and_a_completed_attempt(self):
        l = L(); att(l, "a1"); att(l, "a2", "REJECTED"); att(l, "a3")
        self.assertEqual(code(l.record_selection, "F", "B1", "a3", 1), "LINEAGE_MULTIPLICITY_UNDERREPORTED_OR_WRONG"); self.assertEqual(code(l.record_selection, "F", "B1", "a3", 99), "LINEAGE_MULTIPLICITY_UNDERREPORTED_OR_WRONG")
        self.assertEqual(code(l.record_selection, "F", "B1", "a2", 3), "LINEAGE_SELECTED_ATTEMPT_NOT_COMPLETED"); self.assertEqual(code(l.record_selection, "F", "B1", "zz", 3), "LINEAGE_SELECTED_ATTEMPT_NOT_IN_FAMILY_BATTERY")
        self.assertIsNotNone(l.record_selection("F", "B1", "a3", 3)); self.assertEqual(l.multiplicity_facts("F")["selections"], 1)
        self.assertEqual(code(l.record_selection, "F", "B1", "a3", True), "LINEAGE_MULTIPLICITY_UNDERREPORTED_OR_WRONG")           # bool is not an int count
    def test_unregistered_battery_unknown_parent_reused_id_bad_status_and_cross_family_parent(self):
        l = L(); self.assertEqual(code(att, l, "x", battery="B9"), "LINEAGE_BATTERY_UNREGISTERED"); self.assertEqual(code(att, l, "x", parents=("nope",)), "LINEAGE_UNKNOWN_PARENT")
        att(l, "a1"); self.assertEqual(code(att, l, "a1", params_hash="other"), "LINEAGE_ATTEMPT_ID_REUSED_DIFFERENTLY"); self.assertEqual(code(att, l, "a2", status="PASSED"), "LINEAGE_INPUT_INVALID")
        l.register_battery("G", "B1"); self.assertEqual(code(l.record_attempt, "g1", "G", "B1", "in", "h", "p", "COMPLETED", "o", ("a1",)), "LINEAGE_PARENT_OTHER_FAMILY"); self.assertEqual(l.multiplicity_facts("F", "B1")["attempts"], 1)
    def test_accepted_record_attempt_reference_resolves_only_when_the_ledger_holds_it_and_other_families_are_unaffected(self):
        l = L(); att(l, "a1"); self.assertTrue(l.resolves("a1")); self.assertFalse(l.resolves("ghost")); l.register_battery("G", "B1"); self.assertEqual(l.multiplicity_facts("G")["attempts"], 0); self.assertEqual(l.multiplicity_facts("F")["attempts"], 1)
    def test_ledger_survives_restart_by_replay(self):
        l = L(); att(l, "a1"); l2 = ResearchLineage(l._j); self.assertEqual(l2.multiplicity_facts("F", "B1")["attempts"], 1); self.assertEqual(code(att, l2, "a1", params_hash="x"), "LINEAGE_ATTEMPT_ID_REUSED_DIFFERENTLY")
if __name__ == "__main__": unittest.main()
