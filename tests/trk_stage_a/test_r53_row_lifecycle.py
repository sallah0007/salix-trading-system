"""R53 item 7 on the ACTUAL per-row owning route: quarantine -> clear -> reactivate -> trigger-driven ROW re-verification -> restored; restart over the same Core journal; and the E05 read-model rebuild proving HISTORICAL records are unchanged while CURRENT trust (Core HEALTH) changes. Core HEALTH -> stagea_health_index column mapping is HELD (no source mapping): not projected here. Clears no gate/hold."""
import json
from stage_a.core.tracker_core import TrackerCore
from stage_a.gateway import contracts as G
from stage_a.tracker import row_maintenance as RM, row_acceptance as RA
from . import test_r53_row_l2_maintenance as L2
from .test_r53_row_route_delivery import code

class RowLifecycle(L2.RowL2):
    pass
for _n in [n for n in dir(L2.RowL2) if n.startswith("test_")]: setattr(RowLifecycle, _n, None)

class Cycle(RowLifecycle):
    def test_quarantine_clear_reactivate_then_row_reverification_restores_FW_and_ML_row_windows_and_restart_keeps_every_state(self):
        c = self.c; fk = self.o["B"][0]; k = fk.key(); self.reg(); self.assertEqual([x[2] for x in self.maint(13)], ["VERIFIED"])
        self.delivered("B", "q0", 0, 14); fw0, ml0 = self.deliver("B", "q0", 0, 14)                                          # healthy baseline; repeat = the same final outcome
        c.quarantine(k, "R"); self.denied("B", "q1", 1, 15)                                                                  # QUARANTINED: new FW row window denied and ML row excluded
        again = self.deliver("B", "q0", 0, 15); self.assertIsInstance(again[0], G.Binding); self.assertEqual(again[0], fw0)    # an already-final window outcome is immutable (not retroactively rewritten)
        self.assertTrue(TrackerCore(c._j, simulation=True)._blocked(TrackerCore(c._j, simulation=True)._replay(), k))                                  # RESTART over the same journal: still blocked
        c.clear_reason(k, "R", "cert", "maker"); self.denied("B", "q2", 1, 15)                                               # cleared but not reactivated: still denied
        c.reactivate(k); self.assertEqual(c.recording_health(k, fk.feature_version, 15).state, "UNKNOWN"); self.denied("B", "q3", 1, 16)                        # earlier evidence (incl. the earlier row L2 PASS) does not survive reactivation
        self.assertEqual([x[2] for x in self.maint(17)], ["VERIFIED"]); self.delivered("B", "q4", 1, 18)                       # restored ONLY by the trigger-driven ROW re-verification
        c3 = TrackerCore(c._j, simulation=True); self.assertFalse(c3._blocked(c3._replay(), k)); self.assertNotEqual(c3.recording_health(k, fk.feature_version, 18).state, "UNKNOWN")      # restart after restoration: not blocked, health recovered from the journal
    def test_restoration_cannot_come_from_a_row_L2_that_FAILS_and_a_restart_does_not_resurrect_a_PASS(self):
        c = self.c; fk = self.o["B"][0]; k = fk.key(); self.reg(); self.maint(13); self.src["in1"] = 99.0; self.assertEqual([x[2] for x in self.maint(15)], ["RECORDED_NOT_PASS"])
        bad = c.recording_health(k, fk.feature_version, 16).state; c2 = TrackerCore(c._j, simulation=True); self.assertEqual(c2.recording_health(k, fk.feature_version, 16).state, bad); self.denied("B", "r0", 0, 16)
        c.quarantine(k, "R"); c.clear_reason(k, "R", "cert", "maker"); c.reactivate(k); self.assertEqual([x[2] for x in self.maint(17)], ["RECORDED_NOT_PASS"]); self.denied("B", "r1", 0, 18)   # reactivated, re-verified, still FAIL: still denied
    def test_e05_rebuild_proves_the_historical_row_and_transition_records_are_unchanged_when_current_trust_changes(self):
        from stage_a.storage import e05_sources as S, e05_row_sources as RW
        from stage_a.storage.e05_index import E05Index
        rig = self.a.rig; row0 = self.chain["B"][0][0]; ns = RA.row_namespace(row0); j = rig.journals.journal(ns)
        def heads():
            src = {"rows": RW.pending_row_source(rig.store, self.rows, lambda h: "HELD_STATE"), "tx": RW.row_transition_source(j, ns, self.rows)}; ix = E05Index(); h = ix.rebuild(src)
            res = S.combined_resolver(S.object_resolver(rig.store), S.journal_resolver({ns: j})); self.assertGreaterEqual(ix.verify_all(res), 5); return h
        self.reg(); before = heads(); self.assertEqual([x[2] for x in self.maint(13)], ["VERIFIED"]); self.src["in1"] = 99.0; self.assertEqual([x[2] for x in self.maint(15)], ["RECORDED_NOT_PASS"])
        self.assertEqual(heads(), before)                                                                                    # historical canonical records identical; the current-trust change lives only in the Core
