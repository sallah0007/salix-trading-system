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
import threading, json
from tracker_component.journal_port import HeadMismatch
class Race(unittest.TestCase):
    def _two(self, l, f1, f2):
        """Both callers pause after their FIRST real _state read (read-boundary fault scheduling), then proceed."""
        bar = threading.Barrier(2, timeout=5); real = l._state; seen = threading.local(); out = [None, None]
        def st():
            r = real()
            if not getattr(seen, "p", False): seen.p = True; bar.wait()
            return r
        l._state = st
        def run(i, f):
            try: out[i] = ("ok", f())
            except Refusal as e: out[i] = ("refused", e.code)
        ts = [threading.Thread(target=run, args=(0, f1)), threading.Thread(target=run, args=(1, f2))]
        [t.start() for t in ts]; [t.join(10) for t in ts]; del l._state; return out
    def test_two_conflicting_attempts_with_the_same_id_cannot_both_land(self):
        l = L(); o = self._two(l, lambda: att(l, "SAME", "REJECTED"), lambda: att(l, "SAME", "COMPLETED", outcome_ref="other"))
        self.assertEqual(sorted(x[0] for x in o), ["ok", "refused"]); self.assertIn("LINEAGE_ATTEMPT_ID_REUSED_DIFFERENTLY", [x[1] for x in o])
        kinds = [r.kind for r in l._j.read_from(1)]; self.assertEqual(kinds.count("ATTEMPT"), 1); self.assertEqual(l.multiplicity_facts("F", "B1")["attempts"], 1)
    def test_two_identical_concurrent_retries_land_exactly_once(self):
        l = L(); o = self._two(l, lambda: att(l, "S"), lambda: att(l, "S")); self.assertEqual([x[0] for x in o], ["ok", "ok"]); self.assertEqual([r.kind for r in l._j.read_from(1)].count("ATTEMPT"), 1)
    def test_an_extra_attempt_racing_a_selection_invalidates_the_declared_n(self):
        l = L(); att(l, "a1"); o = self._two(l, lambda: l.record_selection("F", "B1", "a1", 1), lambda: att(l, "a2", "REJECTED"))
        res = dict((i, x) for i, x in enumerate(o)); sel = [r for r in l._j.read_from(1) if r.kind == "SELECTION"]; n = l.multiplicity_facts("F", "B1")["attempts"]
        for r in sel: self.assertEqual(json.loads(r.body_json)["declared_n"], n)                      # any recorded selection declares the TRUE final count; never a stale one
        if not sel: self.assertEqual(o[0], ("refused", "LINEAGE_MULTIPLICITY_UNDERREPORTED_OR_WRONG"))
    def test_replay_refuses_a_conflicting_duplicate_attempt_record_and_is_not_last_writer_wins(self):
        l = L(); att(l, "SAME", "REJECTED"); b = json.loads(l._j.read_from(1)[-1].body_json); b["status"] = "COMPLETED"; b["outcome_ref"] = "x"; l._j.append(l._j.read_from(1)[-1] and __import__("tracker_component.journal_port", fromlist=["Head"]).Head(l._j.read_from(1)[-1].seq, l._j.read_from(1)[-1].record_hash), "ATTEMPT", b)
        self.assertEqual(code(l.multiplicity_facts, "F", "B1"), "LINEAGE_CONFLICTING_DUPLICATE_ATTEMPT"); self.assertEqual(code(l.resolves, "SAME"), "LINEAGE_CONFLICTING_DUPLICATE_ATTEMPT")
    def test_append_uses_the_validation_head_so_a_moved_head_is_a_HeadMismatch_not_a_blind_append(self):
        l = L(); heads = []; real = l._j.append
        def spy(h, k, b):
            heads.append(h)
            if len(heads) == 1: real(h, "ATTEMPT", {"attempt_id": "sneak", "family": "F", "battery": "B1", "input_ref": "i", "input_hash": "h", "params_hash": "p", "status": "COMPLETED", "outcome_ref": "o", "parents": []})
            return real(h, k, b)
        l._j.append = spy; att(l, "a1"); self.assertGreaterEqual(len(heads), 2); self.assertEqual(l.multiplicity_facts("F", "B1")["attempts"], 2)       # re-read after the mismatch; nothing lost
if __name__ == "__main__": unittest.main()
