"""R42: historical eligibility/present trust over the ACTUAL LifecycleFramework journal + a lagging derived E05 index; slice closure derived from the ledger's own ordering; no caller freshness/closure booleans; no current-generation fallback; no fabricated epochs."""
import unittest
from stage_a.errors import Refusal
from stage_a.coordination.object_store_journal import ObjectStoreJournal
from stage_a.coordination.lifecycle_framework import LifecycleFramework as LF, LifecyclePolicy as LP
from stage_a.storage.object_store import InMemoryObjectStore
from stage_a.storage.e05_index import E05Index
from stage_a.storage import e05_sources as S
from stage_a.tracker import lifecycle_eligibility as LE, historical_eligibility as H
POL = LP(("CAND", "CERT", "SUPER", "REVOKED"), frozenset({(None, "CAND"), ("CAND", "CERT"), ("CERT", "SUPER"), ("CERT", "REVOKED"), ("SUPER", "REVOKED")}), frozenset({"REVOKED"}), "TEST-POLICY-NOT-A-SOURCE-GRAPH")
EL, RV = frozenset({"CERT"}), frozenset({"REVOKED"})
TIMES = {}
time_of = lambda r: TIMES[r.seq]
class Fx:
    def __init__(self):
        j = ObjectStoreJournal(InMemoryObjectStore(), "lifecycle", "w"); j.acquire_epoch(); self.j = j; self.lf = LF(j, POL, lambda s, a, b, e: e == "good"); self.ix = E05Index(); TIMES.clear()
    def at(self, t, subject, tid, frm, to): self.lf.apply(subject, tid, frm, to, "good"); TIMES[self.j.head().seq] = t
    def reindex(self):
        src = S.ledger_source(self.j, "lifecycle", accepted_at_of=time_of); self.ix.rebuild({"lifecycle": src})
    def resolved(self): return lambda: self.ix._c.execute("SELECT seq FROM stagea_index_meta WHERE source='lifecycle'").fetchone()[0] if self.ix._c.execute("SELECT seq FROM stagea_index_meta WHERE source='lifecycle'").fetchone() else 0
def ledger():
    f = Fx(); f.at(10, "G1", "t1", None, "CAND"); f.at(12, "G1", "t2", "CAND", "CERT"); f.at(20, "G1", "t3", "CERT", "SUPER"); f.at(20, "G2", "t4", None, "CAND"); f.at(22, "G2", "t5", "CAND", "CERT"); f.at(40, "G2", "t6", "CERT", "REVOKED"); f.reindex(); return f
class Elig(unittest.TestCase):
    def test_fresh_index_and_a_closed_slice_resolve_the_generation_certified_then_not_the_current_one(self):
        f = ledger(); d = LE.reconstruct(f.j, time_of=time_of, event_time=15, index_resolved_through=f.resolved(), eligible_states=EL); self.assertEqual((d.status, d.generation_id), (H.READY, "G1"))
        d = LE.reconstruct(f.j, time_of=time_of, event_time=25, index_resolved_through=f.resolved(), eligible_states=EL); self.assertEqual((d.status, d.generation_id), (H.READY, "G2"))      # revoked at t=40 does not rewrite history
    def test_a_lagging_index_after_a_new_revocation_is_detected_and_present_trust_is_never_reported_trusted(self):
        f = ledger(); self.assertEqual(LE.trust(f.j, "G1", time_of=time_of, index_resolved_through=f.resolved(), revoked_states=RV), "TRUSTED")
        f.at(50, "G1", "t7", "SUPER", "REVOKED")                                  # authoritative ledger advanced; the derived index did not
        self.assertEqual(LE.trust(f.j, "G1", time_of=time_of, index_resolved_through=f.resolved(), revoked_states=RV), "UNKNOWN_STALE")
        d = LE.reconstruct(f.j, time_of=time_of, event_time=15, index_resolved_through=f.resolved(), eligible_states=EL); self.assertEqual((d.status, d.generation_id), (H.MISSED, "")); self.assertIn("CURRENT_READ_FRESHNESS_FAIL", d.reasons)
        f.reindex(); self.assertEqual(LE.trust(f.j, "G1", time_of=time_of, index_resolved_through=f.resolved(), revoked_states=RV), "REVOKED")
    def test_a_slice_not_closed_by_a_later_ledger_entry_is_incomplete_even_with_a_fresh_index(self):
        f = ledger(); d = LE.reconstruct(f.j, time_of=time_of, event_time=40, index_resolved_through=f.resolved(), eligible_states=EL)           # head entry is AT t=40: more entries at 40 may still arrive
        self.assertEqual(d.status, H.MISSED); self.assertTrue(any(r.startswith("HISTORICAL_SLICE_COMPLETENESS_FAIL") for r in d.reasons))
        f.at(41, "G3", "t8", None, "CAND"); f.reindex(); d = LE.reconstruct(f.j, time_of=time_of, event_time=40, index_resolved_through=f.resolved(), eligible_states=EL); self.assertEqual(d.status, H.READY if d.generation_id else H.MISSED); self.assertFalse(any(r.startswith("HISTORICAL_SLICE") for r in d.reasons))
    def test_unbound_inputs_missing_times_empty_ledger_and_epochs_are_not_fabricated(self):
        e = Fx(); f = ledger()
        with self.assertRaises(Refusal): LE.reconstruct(f.j, time_of=None, event_time=1, index_resolved_through=f.resolved(), eligible_states=EL)
        with self.assertRaises(Refusal): LE.reconstruct(f.j, time_of=lambda r: None, event_time=1, index_resolved_through=f.resolved(), eligible_states=EL)
        with self.assertRaises(Refusal): LE.reconstruct(f.j, time_of=time_of, event_time=1, index_resolved_through=None, eligible_states=EL)
        self.assertEqual(LE.reconstruct(e.j, time_of=time_of, event_time=1, index_resolved_through=lambda: 0, eligible_states=EL).reasons, ("NO_LEDGER_ENTRIES",))
        _, ents = LE.ledger_entries(f.j, time_of); self.assertTrue(all(x.epoch is None for x in ents))
if __name__ == "__main__": unittest.main()
