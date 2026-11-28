"""R45 shadow-live ledger tests. Mutants: python -m tests.trk_stage_a.mutation_sweep_r45_shadow. A pass clears no gate."""
import unittest
from stage_a.errors import Refusal
from stage_a.ml.shadow_ledger import ShadowLedger

def code(f, *a):
    try: f(*a)
    except Refusal as e: return e.code

class Ledger(unittest.TestCase):
    def test_idempotent_duplicate_and_conflict(self):
        L = ShadowLedger()
        self.assertEqual(L.record("p1", "k", "PUBLISHED"), "RECORDED")
        self.assertEqual(L.record("p1", "k", "PUBLISHED"), "DUPLICATE_NOOP")
        self.assertEqual(L.counters("k")["PUBLISHED"], 1)
        self.assertEqual(code(L.record, "p1", "k", "MODEL_ABSTAINED"), "SHADOW_EVENT_ID_CONFLICT")
        self.assertEqual(L.counters("k"), {"PUBLISHED": 1, "MODEL_ABSTAINED": 0, "LIFECYCLE_FENCED": 0})
    def test_outcome_and_fields_closed(self):
        L = ShadowLedger()
        self.assertEqual(code(L.record, "p", "k", "OK"), "SHADOW_OUTCOME_NOT_ADMITTED")
        self.assertEqual(code(L.record, "", "k", "PUBLISHED"), "SHADOW_FIELD_INVALID")
        self.assertEqual(code(L.record, "p", None, "PUBLISHED"), "SHADOW_FIELD_INVALID")
    def test_fencing_misses_visible_in_coverage_and_list(self):
        L = ShadowLedger()
        L.record("a", "k", "PUBLISHED"); L.record("b", "k", "LIFECYCLE_FENCED"); L.record("c", "k", "MODEL_ABSTAINED")
        self.assertEqual(L.coverage("k"), (1, 3)); self.assertEqual(L.fenced("k"), ["b"])
    def test_empty_coverage_is_none_not_full(self):
        self.assertIsNone(ShadowLedger().coverage("nothing"))
    def test_no_retroactive_backfill_after_seal_but_duplicates_still_noop(self):
        L = ShadowLedger(); L.record("a", "k", "PUBLISHED"); L.seal("k")
        self.assertEqual(code(L.record, "late", "k", "PUBLISHED"), "SHADOW_RETROACTIVE_BACKFILL_PROHIBITED")
        self.assertEqual(L.record("a", "k", "PUBLISHED"), "DUPLICATE_NOOP")
        self.assertEqual(L.coverage("k"), (1, 1))
        self.assertEqual(L.record("o", "other", "PUBLISHED"), "RECORDED")          # sealing is per logical key
    def test_counters_are_per_logical_key(self):
        L = ShadowLedger(); L.record("a", "k1", "PUBLISHED"); L.record("b", "k2", "MODEL_ABSTAINED")
        self.assertEqual(L.counters("k1"), {"PUBLISHED": 1, "MODEL_ABSTAINED": 0, "LIFECYCLE_FENCED": 0}); self.assertEqual(L.coverage("k2"), (0, 1))
if __name__ == "__main__": unittest.main()
