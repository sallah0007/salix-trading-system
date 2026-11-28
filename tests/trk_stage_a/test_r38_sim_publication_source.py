"""R38 finding 1: the SIMULATION publication path is bound to the OWNING accepted-source HEAD (derived cache, not authority). Head advance / withdraw => fail closed until a lawful rebuild; WITHDRAWN is never mapped to any status."""
import json, unittest
from stage_a.errors import Refusal
from stage_a.gateway import contracts as G
from stage_a.gateway import durable_final_store as D
from stage_a.gateway.v038 import FinalResolutionIdentity as FI
from stage_a.storage.object_store import InMemoryObjectStore
from stage_a.tracker import publication as PUB
from stage_a.tracker import sim_publication_path as SP
from .test_boundaries import T, I, _entry, _health
from .test_r37_sim_publication_path import build, supplied, gw, code, F
def live():
    rig, fk, fj, path, body = build(); path.commit(fk, supplied(), "SIM_CUR", sequence=1); proj = path.status_projection(); g = gw(proj); g.final_store = D.DurableFinalResolutionStore(InMemoryObjectStore()); path.feed(g)
    return rig, fk, fj, path, proj, g, _entry(fid=F, ver=fk.feature_version)
W = lambda n: FI("FW", "M-A", "XAUUSD", n)
class Source(unittest.TestCase):
    def test_withdraw_on_the_owning_journal_fails_projection_rows_and_a_new_window_closed_but_the_old_window_stays_immutable(self):
        rig, fk, fj, path, proj, g, e = live()
        first = g.resolve_window("w1", W("W1"), e, I, I, 3, 20, _health()); self.assertIsInstance(first, G.Binding); self.assertTrue(proj.authoritative)
        PUB.withdraw(fj, fk, "test")
        self.assertFalse(proj.authoritative); self.assertEqual(code(path.rows), "SIM_PUBLICATION_SOURCE_NOT_LIVE"); self.assertFalse(path.source_current())
        n = g.resolve_window("w2", W("W2"), e, I, I, 3, 20, _health()); self.assertNotIsInstance(n, G.Binding); self.assertEqual(n.reason, "STATUS_SOURCE_NOT_COMMITTED_PROJECTION")
        self.assertEqual(g.resolve_window("w1", W("W1"), e, I, I, 3, 20, _health()), first)                  # OLD window outcome + retry stay immutable
        self.assertEqual(code(path.commit, fk, supplied(), "SIM_CUR", sequence=2), "SIM_PUBLICATION_SOURCE_NOT_LIVE")      # withdrawn: no rebuild, no guessed status
    def test_any_owning_head_advance_with_the_version_still_live_is_stale_until_a_lawful_recommit_against_the_current_head(self):
        rig, fk, fj, path, proj, g, e = live(); from tracker_component.journal_port import Head; real = fj.head; h = real()
        fj.head = lambda: Head(h.seq + 1, "f" * 64)              # the owning HEAD moved by a record that does not change this version's live state (the only public sim transition is withdraw)
        self.assertEqual(code(path.rows), "SIM_PUBLICATION_SOURCE_HEAD_ADVANCED"); self.assertFalse(proj.authoritative); self.assertEqual(g.resolve("r", e, I, I, 3, 10, _health()).reason, "STATUS_SOURCE_NOT_COMMITTED_PROJECTION")
        path.commit(fk, supplied(), "SIM_CUR", sequence=2); self.assertTrue(path.source_current()); proj.refresh(); self.assertTrue(proj.authoritative)          # lawful rebuild: fresh commit against the CURRENT head
        fj.head = real; self.assertFalse(path.source_current())                                                                                          # and it is bound to that head only
    def test_head_race_between_read_and_append_records_an_older_head_and_fails_closed(self):
        rig, fk, fj, path, body = build(); real = fj.head; calls = []
        def head_then_move():
            h = real(); 
            if not calls: calls.append(1); PUB.withdraw(fj, fk, "race"); 
            return h
        fj.head = head_then_move
        self.assertEqual(code(path.commit, fk, supplied(), "SIM_CUR", sequence=1), "SIM_PUBLICATION_SOURCE_NOT_LIVE")      # state already withdrawn when read: refused, nothing committed
        self.assertEqual(path._sj.head().seq, 0)
    def test_stale_projection_is_refused_by_the_gateway_and_an_unrelated_namespace_is_unaffected(self):
        rig, fk, fj, path, proj, g, e = live(); rig2, fk2, fj2, path2, proj2, g2, e2 = live()
        PUB.withdraw(fj, fk, "x"); self.assertFalse(proj.authoritative); self.assertTrue(proj2.authoritative); self.assertEqual(len(path2.rows()), 1)
        self.assertIsInstance(g2.resolve_window("u1", W("U1"), e2, I, I, 3, 20, _health()), G.Binding)
        self.assertEqual(g.resolve("r", e, I, I, 3, 10, _health()).reason, "STATUS_SOURCE_NOT_COMMITTED_PROJECTION")
    def test_the_commit_is_one_record_and_unmapped_withdrawn_is_never_read_as_current(self):
        rig, fk, fj, path, body = build(); path.commit(fk, supplied(), "SIM_CUR", sequence=1); recs = path._sj.read_from(1); self.assertEqual([r.kind for r in recs], [SP.STATUS_KIND])
        b = json.loads(recs[0].body_json); self.assertEqual((b["source_head_seq"], b["source_head_hash"]), (fj.head().seq, fj.head().hash)); self.assertIn("row", b)
    def test_rebuild_positive_while_live_after_an_unrelated_record_free_commit_sequence(self):
        rig, fk, fj, path, proj, g, e = live(); path.commit(fk, supplied(), "SIM_CUR", sequence=2); self.assertTrue(path.source_current()); proj.refresh(); self.assertTrue(proj.authoritative)
if __name__ == "__main__": unittest.main()
