"""R45/R46 shadow-live ledger (MLCore p325-p329 semantics). Mutants: python tests/trk_stage_a/mutation_sweep_r45_shadow.py. A pass clears no gate."""
import unittest
from stage_a.errors import Refusal
from stage_a.ml.shadow_ledger import ShadowLedger

def code(f, *a):
    try: f(*a)
    except Refusal as e: return e.code

def L(*t, key="k"):
    l = ShadowLedger()
    for x in t: l.expect(key, x)
    return l
class Ledger(unittest.TestCase):
    def test_expected_two_published_one_is_one_half_and_unreported_stays_in_denominator(self):
        l = L("t1", "t2"); l.record("k", "t1", "p1", "PUBLISHED"); self.assertEqual(l.coverage("k"), (1, 2)); self.assertEqual(l.missing("k"), ["t2"])
        self.assertEqual(l.counters("k")["MISSING_OR_IN_PROGRESS"], 1)
    def test_no_expected_trigger_holds_coverage_and_unexpected_record_is_refused(self):
        l = ShadowLedger(); self.assertIsNone(l.coverage("k")); self.assertEqual(code(l.record, "k", "t1", "p", "PUBLISHED"), "SHADOW_TRIGGER_NOT_EXPECTED_HELD_UNBOUND")
    def test_expect_is_counted_once(self):
        l = L("t1", "t1", "t1"); self.assertEqual(l.counters("k")["EXPECTED"], 1)
    def test_retry_counts_once_and_conflicts_refuse_and_terminal_is_immutable(self):
        l = L("t1"); self.assertEqual(l.record("k", "t1", "p1", "PUBLISHED"), "RECORDED"); self.assertEqual(l.record("k", "t1", "p1", "PUBLISHED"), "DUPLICATE_NOOP"); self.assertEqual(l.coverage("k"), (1, 1))
        self.assertEqual(code(l.record, "k", "t1", "p1", "MODEL_ABSTAINED"), "SHADOW_TERMINAL_IMMUTABLE"); self.assertEqual(code(l.record, "k", "t1", "p2", "PUBLISHED"), "SHADOW_EVENT_ID_CONFLICT")
        self.assertEqual(code(l.record, "k", "t1", "p1", "FENCED"), "SHADOW_OUTCOME_NOT_ADMITTED")
    def test_one_prediction_id_cannot_serve_two_triggers(self):
        l = L("t1", "t2"); l.record("k", "t1", "p", "PUBLISHED"); self.assertEqual(code(l.record, "k", "t2", "p", "PUBLISHED"), "SHADOW_EVENT_ID_CONFLICT")
    def test_provisional_abstention_is_not_terminal_then_lifecycle_fence_finalizes_and_wins(self):
        l = L("t1"); self.assertEqual(l.provisional_abstain("k", "t1", "pa"), "PROVISIONAL"); self.assertEqual(l.coverage("k"), (0, 1)); self.assertEqual(l.missing("k"), ["t1"])
        self.assertEqual(l.record("k", "t1", "pf", "LIFECYCLE_FENCED"), "RECORDED"); self.assertEqual(l.fenced("k"), ["t1"]); self.assertEqual(l.missing("k"), [])
        self.assertEqual(code(l.record, "k", "t1", "pa", "MODEL_ABSTAINED"), "SHADOW_EVENT_ID_CONFLICT")        # the finalized fence is never reopened
        self.assertEqual(l.coverage("k"), (0, 1))                                       # fencing miss visible in the denominator
    def test_provisional_abstention_confirmed_and_published_after_it_is_not_guessed(self):
        l = L("t1", "t2"); l.provisional_abstain("k", "t1", "pa"); self.assertEqual(l.record("k", "t1", "pa", "MODEL_ABSTAINED"), "RECORDED")
        l.provisional_abstain("k", "t2", "pb"); self.assertEqual(code(l.record, "k", "t2", "pc", "PUBLISHED"), "SHADOW_EVENT_ID_CONFLICT"); self.assertEqual(code(l.record, "k", "t2", "pb", "PUBLISHED"), "SHADOW_PUBLISHED_AFTER_PROVISIONAL_ABSTENTION_NOT_DEFINED")
    def test_terminal_trigger_refuses_a_later_provisional(self):
        l = L("t1"); l.record("k", "t1", "p", "PUBLISHED"); self.assertEqual(code(l.provisional_abstain, "k", "t1", "q"), "SHADOW_TERMINAL_ALREADY_RECORDED")
    def test_no_retroactive_backfill_after_seal_and_no_new_expected_trigger(self):
        l = L("t1", "t2"); l.record("k", "t1", "p", "PUBLISHED"); l.seal("k")
        self.assertEqual(code(l.record, "k", "t2", "late", "PUBLISHED"), "SHADOW_RETROACTIVE_BACKFILL_PROHIBITED"); self.assertEqual(code(l.expect, "k", "t3"), "SHADOW_RETROACTIVE_BACKFILL_PROHIBITED")
        l.expect("k", "t1"); self.assertEqual(l.record("k", "t1", "p", "PUBLISHED"), "DUPLICATE_NOOP"); self.assertEqual(l.coverage("k"), (1, 2))
    def test_fields_closed_and_keys_isolated(self):
        l = L("t1"); self.assertEqual(code(l.expect, "", "t"), "SHADOW_FIELD_INVALID"); self.assertEqual(code(l.record, "k", "t1", "", "PUBLISHED"), "SHADOW_FIELD_INVALID")
        l.expect("k2", "t1"); l.record("k", "t1", "a", "PUBLISHED"); self.assertEqual(l.coverage("k2"), (0, 1))
    def test_r47_event_id_is_globally_unique_across_provisional_and_terminal_in_both_orders_and_refusals_change_nothing(self):
        l = L("t1", "t2"); l.record("k", "t1", "P", "PUBLISHED"); before = (dict(l._expected), dict(l._provisional), dict(l._ids), l.counters("k"))
        self.assertEqual(code(l.provisional_abstain, "k", "t2", "P"), "SHADOW_EVENT_ID_CONFLICT"); self.assertEqual(code(l.record, "k", "t2", "P", "MODEL_ABSTAINED"), "SHADOW_EVENT_ID_CONFLICT")
        self.assertEqual((dict(l._expected), dict(l._provisional), dict(l._ids), l.counters("k")), before); self.assertEqual(l.coverage("k"), (1, 2))
        l2 = L("t1", "t2"); l2.provisional_abstain("k", "t1", "Q"); self.assertEqual(code(l2.record, "k", "t2", "Q", "MODEL_ABSTAINED"), "SHADOW_EVENT_ID_CONFLICT"); self.assertEqual(code(l2.provisional_abstain, "k", "t2", "Q"), "SHADOW_EVENT_ID_CONFLICT")
        self.assertEqual(l2.missing("k"), ["t1", "t2"]); self.assertEqual(l2.record("k", "t1", "F", "LIFECYCLE_FENCED"), "RECORDED"); self.assertEqual(code(l2.record, "k", "t2", "Q", "PUBLISHED"), "SHADOW_EVENT_ID_CONFLICT")   # the superseded abstention id stays bound to t1
        self.assertEqual(l2.coverage("k"), (0, 2)); self.assertEqual(len({v[0] for v in l2._expected.values() if v}), 1)
        self.assertEqual(l.provisional_abstain("k", "t1", "P") if False else l.record("k", "t1", "P", "PUBLISHED"), "DUPLICATE_NOOP")      # exact retry stays a no-op (MLCore p324)
if __name__ == "__main__": unittest.main()
