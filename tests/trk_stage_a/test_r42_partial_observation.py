"""R42 item C: the ACTUAL partial-observation boundary over the published objects and their consumers. The SIM publication unit is ONE status record carrying the row and the receipt binding; it becomes visible only when the journal head moves (record body first, head CAS second). A crash between them leaves an ORPHAN body that no reader can see: the status projection, the rows and the Gateway observe NOTHING, and the retry publishes exactly once. The orphan is not 'present' for any consumer, and no current-generation fallback exists (a missing status is a denial). Does NOT supply the shadow-row field set (UNBOUND)."""
import unittest
from stage_a.errors import Refusal, IntegrityFailure
from stage_a.gateway import contracts as G
from stage_a.coordination.object_store_journal import head_key
from .test_r37_sim_publication_path import build, supplied, gw, F, I
from .test_boundaries import _entry, _health
class Boom(Exception): pass
class Partial(unittest.TestCase):
    def _crash_head_once(self, store):
        real = store.put_if_match; state = {"armed": True}
        def pim(key, data, etag):
            if state["armed"] and key == head_key(self.ns): state["armed"] = False; raise Boom()
            return real(key, data, etag)
        store.put_if_match = pim; return state
    def test_a_crash_between_the_record_body_and_the_head_leaves_nothing_visible_to_any_consumer_and_the_retry_publishes_once(self):
        rig, fk, fj, path, body = build(); self.ns = path._sj._ns; self._crash_head_once(rig.store)
        with self.assertRaises(Boom): path.commit(fk, supplied(), "SIM_CUR", sequence=1)
        self.assertEqual(path.rows(), []) if isinstance(path.rows(), list) else self.assertEqual(len(path.rows()), 0)
        proj = path.status_projection(); g = gw(proj); self.assertEqual(path.feed(g), 0)
        self.assertNotIsInstance(g.resolve("r0", _entry(fid=F, ver=fk.feature_version), I, I, 3, 10, _health()), G.Binding)          # no status -> denial, never a current-generation fallback
        self.assertGreaterEqual(len(rig.store.list_prefix("")), 1)
        path.commit(fk, supplied(), "SIM_CUR", sequence=1)                                                  # retry: the orphan body is re-used/overwritten idempotently
        g2 = gw(path.status_projection()); self.assertEqual(path.feed(g2), 1); self.assertIsInstance(g2.resolve("r1", _entry(fid=F, ver=fk.feature_version), I, I, 3, 10, _health()), G.Binding)
        self.assertEqual(len(path._records()), 1)
    def test_a_published_record_whose_row_is_altered_in_place_is_not_observable_as_a_complete_publication(self):
        rig, fk, fj, path, body = build(); path.commit(fk, supplied(), "SIM_CUR", sequence=1)
        k = [k for k in rig.store.list_prefix("") if "SIMPUB" in k and k != head_key(path._sj._ns)][0]; b, e = rig.store.get(k)
        rig.store.put_if_match(k, b.replace(b"p", b"q", 1), e)
        with self.assertRaises((Refusal, IntegrityFailure)): path.status_projection(); path.rows()
if __name__ == "__main__": unittest.main()
