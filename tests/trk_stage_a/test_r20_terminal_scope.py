"""R20: terminal identity must not lose data (comma ids), must be row-order independent, and must never link across era/instrument/timeframe. Identity/report-only."""
import itertools, unittest
from dataclasses import replace
from tracker_identity.models import LookupOutcome
from stage_a.tracker import terminal_identity as TI
from .test_r19_terminal_identity import rec, A, lookup
X = lambda r, **k: replace(r, **k)
class Faithful(unittest.TestCase):
    def test_comma_and_colon_ids_are_not_lost(self):                                  # Codex repro: rows=[A('b,comma'), rec('b,comma', REJECTED)]
        for fid in ("b,comma", "b:colon", "b,c:d"):
            rows = [A(fid), rec(fid, state="REJECTED_INVALID")]; lk, store = lookup(rows)
            self.assertTrue(any(e.startswith("UNRESOLVED_CANONICAL_SURVIVOR:") for e in lk.errors))
            notes = TI.terminal_notes(lk, rows)
            self.assertEqual(len(notes), 1, fid); self.assertIn(repr(fid), notes[0]); self.assertIn("REJECTED_INVALID", notes[0])
            t = TI.resolve_terminal_identity(rows[0], rows); self.assertEqual((t.terminal_id, t.terminal_state), (fid, "REJECTED_INVALID"))
    def test_notes_are_hints_gated_by_the_lookup_and_never_resolve_identity_from_text(self):
        rows = [A("b"), rec("b", state="REJECTED_INVALID")]
        self.assertEqual(TI.terminal_notes(type("L", (), {"errors": ()})(), rows), [])        # no unresolved-survivor error -> no report
    def test_terminal_carries_full_facts_not_only_an_id(self):
        rows = [A("b"), rec("b", survivor="c", version="7", defn="d7"), rec("c", current=True, state="CURRENT", version="9", defn="d9")]
        t = TI.resolve_terminal_identity(rows[0], rows)
        self.assertEqual(len(t.chain_facts), 3); f = t.terminal_facts
        self.assertEqual((f[0], f[1], f[2], f[4], f[5], f[6], f[8], f[9]), ("c", "9", "d9", "ERA_1", "EURUSD", "H1", "CURRENT", True))
class Scope(unittest.TestCase):
    def rows(self):
        a = A("b"); bE = rec("b", survivor="c"); bX = X(rec("b", survivor="d"), instrument="XAUUSD")
        c = rec("c", current=True, state="ACTIVE"); d = X(rec("d", current=True, state="ACTIVE"), instrument="XAUUSD")
        return a, [a, bE, bX, c, d]
    def test_reordering_legal_instrument_qualified_records_never_changes_the_result(self):    # Codex repro
        a, rows = self.rows(); results = set()
        for perm in itertools.permutations(rows):
            t = TI.resolve_terminal_identity(a, list(perm)); results.add((t.status, t.terminal_id, t.terminal_facts, t.chain_facts))
        self.assertEqual(len(results), 1); (st, tid, *_), = results; self.assertEqual((st, tid), (TI.CURRENT_SURVIVOR, "c"))
    def test_foreign_instrument_timeframe_era_successor_is_not_a_link(self):
        for k, v in (("instrument", "XAUUSD"), ("timeframe", "M5"), ("era_id", "ERA_2")):
            a = A("b"); b = X(rec("b", current=True, state="CURRENT"), **{k: v})
            t = TI.resolve_terminal_identity(a, [a, b]); self.assertEqual((t.status, t.terminal_id, t.terminal_facts), (TI.CROSS_SCOPE, "", ()), k)
            self.assertFalse(t.authorizes_claim or t.authorizes_resurrection or t.authorizes_delivery or t.authorizes_near_match_substitution)
    def test_conflicting_successors_in_the_same_scope_refuse_in_any_order(self):
        a = A("b"); b1 = rec("b", survivor="c"); b2 = rec("b", survivor="d", version="2")
        c = rec("c", current=True, state="ACTIVE"); d = rec("d", current=True, state="ACTIVE")
        for perm in itertools.permutations([a, b1, b2, c, d]): self.assertEqual(TI.resolve_terminal_identity(a, list(perm)).status, TI.AMBIGUOUS)
        e1 = rec("b", survivor="c"); e2 = X(e1, graph_hash="other")                       # same pointer, different hash
        self.assertEqual(TI.resolve_terminal_identity(a, [a, e1, e2, c]).status, TI.AMBIGUOUS)
    def test_identical_duplicate_rows_collapse_but_are_not_an_ambiguity(self):
        a = A("b"); b = rec("b", state="REJECTED_INVALID"); self.assertEqual(TI.resolve_terminal_identity(a, [a, b, b]).terminal_id, "b")
    def test_cycle_orphan_and_cross_scope_cycle_controls(self):
        a = rec("a", survivor="b"); b = rec("b", survivor="a"); self.assertEqual(TI.resolve_terminal_identity(a, [a, b]).status, TI.CYCLE)
        b2 = X(rec("b", survivor="a"), instrument="XAUUSD"); self.assertEqual(TI.resolve_terminal_identity(a, [a, b2]).status, TI.CROSS_SCOPE)    # not a cycle: a different identity
        self.assertEqual(TI.resolve_terminal_identity(rec("a", survivor="zz"), [rec("a", survivor="zz")]).status, TI.ORPHAN)
    def test_noncurrent_terminal_and_unaffected_valid_current_controls(self):
        a = A("b"); b = rec("b", state="RETIRED"); t = TI.resolve_terminal_identity(a, [a, b])
        self.assertEqual((t.status, t.terminal_state, t.terminal_is_current), (TI.TERMINAL_NONCURRENT, "RETIRED", False))
        c = rec("c", current=True, state="CURRENT"); t = TI.resolve_terminal_identity(c, [a, b, c]); self.assertEqual((t.status, t.chain), (TI.CURRENT_SURVIVOR, ("c",)))
    def test_notes_scope_filter_and_deterministic_order(self):
        a, rows = self.rows(); lk, _ = lookup([A("q"), rec("q", state="REJECTED_INVALID")])         # any lookup with the unresolved-survivor error
        n1 = TI.terminal_notes(lk, rows, scope=("ERA_1", "EURUSD", "H1")); n2 = TI.terminal_notes(lk, list(reversed(rows)), scope=("ERA_1", "EURUSD", "H1"))
        self.assertEqual(n1, n2); self.assertTrue(all("'d'" not in n for n in n1))                 # the XAUUSD chain is not reported under the EURUSD scope
    def test_multiple_starts_are_reported_in_input_order_independent_order(self):
        lk, _ = lookup([A("q"), rec("q", state="REJECTED_INVALID")])
        rows = [rec("s1", survivor="z1"), rec("z1", state="RETIRED"), rec("s2", survivor="z2"), rec("z2", state="DISCARDED")]
        base = TI.terminal_notes(lk, rows); self.assertEqual(len(base), 2)                       # only noncurrent rows that carry a survivor pointer are starts
        for perm in itertools.permutations(rows): self.assertEqual(TI.terminal_notes(lk, list(perm)), base)
if __name__ == "__main__": unittest.main()
