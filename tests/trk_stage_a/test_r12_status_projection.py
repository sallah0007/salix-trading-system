"""R12: status projection over committed journal records; direct uncommitted append is not consumer-authoritative.
The record->StatusFact decoder here is a TEST double: the real mapping is the unresolved R7 clause (see status_projection.py)."""
import json, unittest
from tracker_component.journal_port import GENESIS_HEAD
from stage_a.errors import Refusal
from stage_a.storage.object_store import InMemoryObjectStore
from stage_a.coordination.object_store_journal import ObjectStoreJournal
from stage_a.tracker import chain_status as C
from stage_a.tracker.status_projection import StatusProjection
from stage_a.gateway import contracts as G
from tests.trk_stage_a import test_boundaries as B

MV = (B.I, "f1", B.I, B.I, "m1")
def decode(rec):
    if rec.kind != "STATUS_FACT_TEST": return None
    b = json.loads(rec.body_json)
    mv = tuple(bytes.fromhex(x[2:]) if isinstance(x, str) and x.startswith("b:") else x for x in b["mv"])
    return C.StatusFact(mv, b["seq"], b["status"], b["asof"], b["corr"], b.get("des", False))
def jr():
    j = ObjectStoreJournal(InMemoryObjectStore(), "status-ns", "status-writer"); j.acquire_epoch(); return j
def commit(j, seq, status, asof=1, corr=False, des=False, mv=MV):
    return j.append(j.head(), "STATUS_FACT_TEST", {"mv": ["b:" + x.hex() if isinstance(x, bytes) else x for x in mv], "seq": seq, "status": status, "asof": asof, "corr": corr, "des": des})
def gw(status):
    g = G.SimulatedGateway(B.T, status, watermark=100); g.publish(B._row()); return g
def res(g, rid="r"): return g.resolve(rid, B._entry(), B.I, B.I, 3, 10, B._health(), True)

class Projection(unittest.TestCase):
    def test_direct_uncommitted_append_is_not_consumer_authoritative(self):
        a = C.ChainStatusAuthority(); a.append(C.StatusFact(MV, 1, C.CURRENT, 1, False))
        r = res(gw(a)); self.assertEqual(r.reason, "STATUS_SOURCE_NOT_COMMITTED_PROJECTION")           # default is fail closed
        self.assertIsInstance(res(G.SimulatedGateway(B.T, a, allow_uncommitted_status=True, watermark=100) and self._open(a)), G.Binding)   # explicit test-only opt-in
    def _open(self, a):
        g = G.SimulatedGateway(B.T, a, allow_uncommitted_status=True, watermark=100); g.publish(B._row()); return g
    def test_committed_record_projects_and_gateway_binds(self):
        j = jr(); commit(j, 1, C.CURRENT); p = StatusProjection(j, decode); p.refresh()
        self.assertTrue(p.authoritative); self.assertIsInstance(res(gw(p)), G.Binding)
    def test_never_refreshed_projection_is_not_authoritative(self):
        j = jr(); commit(j, 1, C.CURRENT); p = StatusProjection(j, decode)
        self.assertFalse(p.authoritative); self.assertEqual(res(gw(p)).reason, "STATUS_SOURCE_NOT_COMMITTED_PROJECTION")
        with self.assertRaises(Refusal): p.status_at(MV, 10)
    def test_stale_after_new_commit_until_refresh(self):
        j = jr(); commit(j, 1, C.CURRENT); p = StatusProjection(j, decode); p.refresh()
        commit(j, 2, C.HALTED, asof=2, corr=True)
        self.assertFalse(p.authoritative); self.assertEqual(res(gw(p)).reason, "STATUS_SOURCE_NOT_COMMITTED_PROJECTION")   # cannot keep answering CURRENT
        p.refresh(); self.assertTrue(p.authoritative); self.assertTrue(res(gw(p), "r2").reason.startswith("CHAIN_STATUS_NOT_CURRENT"))
    def test_orphan_uncommitted_object_never_read(self):
        j = jr(); commit(j, 1, C.CURRENT); p = StatusProjection(j, decode); p.refresh()
        from stage_a.storage.keys import journal_key
        j._s.put_if_absent(journal_key("status-ns", 2, "ff" * 32), b'{"orphan": true}')      # object not reachable from HEAD
        p.refresh(); self.assertTrue(p.authoritative); self.assertEqual(p.status_at(MV, 10).status, C.CURRENT)
    def test_replay_is_deterministic_and_independent_of_projection_instance(self):
        j = jr(); commit(j, 1, C.CATCHING_UP); commit(j, 2, C.CURRENT, asof=2, des=True)
        a, b = StatusProjection(j, decode), StatusProjection(j, decode); a.refresh(); b.refresh()
        self.assertEqual(a.status_at(MV, 10), b.status_at(MV, 10)); self.assertEqual(a.built_head, b.built_head)
        self.assertEqual(a.status_at(MV, 2).status, C.CATCHING_UP)                           # half-open fence preserved by the replayed authority
    def test_state_machine_violation_in_committed_record_invalidates_projection(self):
        j = jr(); commit(j, 1, C.HALTED); commit(j, 2, C.CURRENT, asof=2)                    # HALTED is terminal
        p = StatusProjection(j, decode)
        with self.assertRaises(Refusal): p.refresh()
        self.assertFalse(p.authoritative)
        with self.assertRaises(Refusal) as c: p.status_at(MV, 10)
        self.assertEqual(c.exception.code, "STATUS_PROJECTION_INVALID")
    def test_decoder_is_required_and_must_return_facts(self):
        with self.assertRaises(Refusal): StatusProjection(jr(), None)
        j = jr(); commit(j, 1, C.CURRENT)
        with self.assertRaises(Refusal) as c: StatusProjection(j, lambda r: "not a fact").refresh()
        self.assertEqual(c.exception.code, "STATUS_DECODER_RETURNED_NON_FACT")
    def test_non_status_records_are_skipped_and_empty_journal_is_authoritative_but_empty(self):
        j = jr(); p = StatusProjection(j, decode); p.refresh(); self.assertEqual(p.built_head, GENESIS_HEAD)
        self.assertIsNone(p.status_at(MV, 10)); self.assertEqual(res(gw(p)).reason, "NO_STATUS_AUTHORITY_FACT")
        j.append(j.head(), "OTHER", {"x": 1}); p.refresh(); self.assertIsNone(p.status_at(MV, 10))
    def test_projection_has_no_write_path(self):
        self.assertFalse(any(hasattr(StatusProjection, n) for n in ("append", "put", "write", "commit")))
if __name__ == "__main__": unittest.main()
