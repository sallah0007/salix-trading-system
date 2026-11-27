"""R20: terminal identity must not lose data (comma ids), must be row-order independent, and must never link across era/instrument/timeframe. Identity/report-only."""
import itertools, unittest
from dataclasses import replace
from tracker_identity.models import LookupOutcome
from stage_a.tracker import terminal_identity as TI
from tests import test_identity_surface as T
from .test_r19_terminal_identity import rec, A, lookup
X = lambda r, **k: replace(r, **k)
def results(rows, subject=None):
    lk, store = lookup(rows); return TI.subject_terminal_identities(subject or T.subject(), store.all(), T.normalizer(), active_era_id=store.active_era_id)
class Faithful(unittest.TestCase):
    def test_comma_and_colon_ids_are_not_lost(self):                                  # Codex repro: rows=[A('b,comma'), rec('b,comma', REJECTED)]
        for fid in ("b,comma", "b:colon", "b,c:d"):
            rows = [A(fid), rec(fid, state="REJECTED_INVALID")]
            t, = results(rows); self.assertEqual((t.start_id, t.terminal_id, t.terminal_state), ("returns.1bar", fid, "REJECTED_INVALID"), fid)
    def test_unrelated_same_scope_rows_are_never_starts(self):                        # Codex repro: unrelated>z was reported
        rows = [A("b"), rec("b", state="REJECTED_INVALID"), rec("unrelated", survivor="z", defn="other-def"), rec("z", state="RETIRED", defn="other-def")]
        t, = results(rows); self.assertEqual((t.start_id, t.terminal_id), ("returns.1bar", "b"))
        self.assertEqual(results([rec("unrelated", survivor="z"), rec("z", state="RETIRED")]), ())          # no matching row at all -> nothing asserted
    def test_matching_noncurrent_without_successor_reports_its_own_state(self):
        t, = results([A(None, state="RETIRED")]); self.assertEqual((t.status, t.terminal_id, t.terminal_state), (TI.TERMINAL_NONCURRENT, "returns.1bar", "RETIRED"))
    def test_ambiguous_starts_are_each_reported_in_a_row_order_independent_way(self):
        a1 = A("b"); a2 = A("c"); rows = [a1, a2, rec("b", state="REJECTED_INVALID"), rec("c", state="DISCARDED")]
        base = results(rows); self.assertEqual(len(base), 2)
        for perm in itertools.permutations(rows): self.assertEqual(results(list(perm)), base)
    def test_cycles_and_orphans_from_a_real_subject(self):
        t, = results([A("b"), rec("b", survivor="returns.1bar")]); self.assertEqual(t.status, TI.CYCLE)
        t, = results([A("ghost")]); self.assertEqual((t.status, t.terminal_id), (TI.ORPHAN, ""))
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
class CycleChain(unittest.TestCase):
    def test_cycle_reports_the_repeated_node_not_just_a_status(self):
        a = rec("a", survivor="b"); b = rec("b", survivor="a"); t = TI.resolve_terminal_identity(a, [a, b])
        self.assertEqual((t.status, t.chain), (TI.CYCLE, ("a", "b", "a")))
class CurrentRowIsNeverAStart(unittest.TestCase):
    def test_a_matching_current_row_is_not_a_noncurrent_start(self):
        self.assertEqual(results([A(None, current=True, state="CURRENT")]), ())            # R21 mutant: a current match must not be reported as a terminal start
class NoContentSubject(unittest.TestCase):
    def test_subject_without_content_never_matches_by_content_key(self):
        sub = dict(T.subject()); sub.pop("candidate_content", None)
        row = X(A("b"), content_key_composite="K", content_key_definition="d", content_key_causal_time="c", content_key_provenance="p", content_key_scope="s", content_key_fitted="f"); self.assertTrue(row.has_content_key)
        lk, store = lookup([row, rec("b", state="REJECTED_INVALID")])
        self.assertEqual(len(TI.subject_terminal_identities(sub, store.all(), T.normalizer(), active_era_id=store.active_era_id)), 1)        # still found by exact canonical key, no content-key crash/match
class R22EraAndSearchBounds(unittest.TestCase):
    """Codex PR45 repro: lookup_era_scope=ERA_1_ONLY must not return an ERA_2 terminal."""
    def rows(self):
        return [A("b"), rec("b", state="REJECTED_INVALID"), X(A("foreign-era-terminal"), era_id="ERA_2"), X(rec("foreign-era-terminal", state="RETIRED"), era_id="ERA_2")]
    def test_era_1_only_excludes_other_era_rows(self):
        sub = dict(T.subject(), lookup_era_scope="ERA_1_ONLY"); lk, store = lookup(self.rows())
        res = TI.subject_terminal_identities(sub, store.all(), T.normalizer(), active_era_id=store.active_era_id)
        self.assertEqual([t.terminal_id for t in res], ["b"])
    def test_unknown_or_unverified_era_and_bad_scope_fail_closed(self):
        lk, store = lookup(self.rows()); n = T.normalizer()
        self.assertEqual(TI.subject_terminal_identities(dict(T.subject(), lookup_era_scope="ERA_1_ONLY"), store.all(), n), ())          # no verified active era
        self.assertEqual(TI.subject_terminal_identities(dict(T.subject(), lookup_era_scope="ERA_9"), store.all(), n, active_era_id="ERA_1"), ())
    def test_rows_outside_searched_scopes_are_not_evidence(self):
        lk, store = lookup(self.rows()); n = T.normalizer()
        self.assertEqual(TI.subject_terminal_identities(T.subject(), store.all(), n, active_era_id="ERA_1", searched_scopes=("some_other_scope",)), ())
    def test_malformed_normalization_yields_nothing(self):
        lk, store = lookup(self.rows()); bad = dict(T.subject()); bad["feature_id"] = None
        self.assertEqual(TI.subject_terminal_identities(bad, store.all(), T.normalizer(), active_era_id="ERA_1"), ())

class R22UnsupportedActiveEra(unittest.TestCase):
    def test_active_era_other_than_era_1_with_era_1_only_scope_asserts_nothing(self):
        rows = [X(A("b"), era_id="ERA_2"), X(rec("b", state="REJECTED_INVALID"), era_id="ERA_2")]; lk, store = lookup(rows)
        self.assertEqual(TI.subject_terminal_identities(dict(T.subject(), lookup_era_scope="ERA_1_ONLY"), store.all(), T.normalizer(), active_era_id="ERA_2"), ())
