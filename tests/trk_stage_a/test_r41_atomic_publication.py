"""R41: NL0186 candidate atomic publish/read: crash between body and pointer leaves the record ABSENT to every reader; concurrent readers never see a partial; idempotent retry; conflicting retry; tamper/missing body fail closed."""
import threading, unittest
from stage_a.errors import Refusal, IntegrityFailure
from stage_a.storage.object_store import InMemoryObjectStore
from stage_a.tracker.atomic_publication import AtomicRecordStore
REQ = frozenset({"id", "pred", "gen"}); R = {"id": "e1", "pred": 1, "gen": "G1", "extra": "x"}
class Atomic(unittest.TestCase):
    def setUp(self): self.s = InMemoryObjectStore(); self.a = AtomicRecordStore(self.s, required_fields=REQ)
    def test_publish_then_read_and_identical_retry_is_one_record(self):
        h = self.a.publish("k1", R); self.assertEqual(self.a.read("k1"), R); self.assertEqual(self.a.publish("k1", dict(R)), h); self.assertEqual(len([k for k in self.s.list_prefix("atomic/ptr/")]), 1)
    def test_crash_between_body_and_pointer_is_entirely_absent_then_retry_publishes(self):
        def boom(): raise RuntimeError("crash")
        with self.assertRaises(RuntimeError): self.a.publish("k1", R, _after_body=boom)
        self.assertIsNone(self.a.read("k1")); self.assertEqual(len(self.s.list_prefix("atomic/body/")), 1)          # orphan body, unreachable
        self.a.publish("k1", R); self.assertEqual(self.a.read("k1"), R)
    def test_a_concurrent_reader_sees_absent_or_complete_never_partial(self):
        seen = set(); stop = threading.Event()
        def reader():
            while not stop.is_set():
                r = self.a.read("k1"); seen.add(None if r is None else tuple(sorted(r)))
        ts = [threading.Thread(target=reader) for _ in range(4)]; [t.start() for t in ts]
        for i in range(50): self.a.publish("k1", R) if i == 25 else None
        stop.set(); [t.join() for t in ts]; self.assertTrue(seen <= {None, tuple(sorted(R))}); self.assertIn(tuple(sorted(R)), seen)
    def test_same_key_different_payload_is_an_integrity_failure_and_the_first_record_stands(self):
        self.a.publish("k1", R)
        with self.assertRaises(IntegrityFailure): self.a.publish("k1", dict(R, pred=2))
        self.assertEqual(self.a.read("k1"), R)
    def test_incomplete_records_and_bad_keys_refuse_before_any_write(self):
        for bad in ({"id": "e1", "pred": 1}, dict(R, gen=""), dict(R, gen=None), "x"):
            with self.assertRaises(Refusal): self.a.publish("k2", bad)
        with self.assertRaises(Refusal): self.a.publish("", R)
        self.assertEqual(self.s.list_prefix("atomic/"), []); self.assertIsNone(self.a.read("k2"))
    def test_missing_or_tampered_body_fails_closed_not_partial(self):
        h = self.a.publish("k1", R); bk = "atomic/body/" + h; g = self.s.get(bk); self.s.put_if_match(bk, g[0] + b" ", g[1])
        with self.assertRaises(IntegrityFailure): self.a.read("k1")
        s2 = InMemoryObjectStore(); a2 = AtomicRecordStore(s2, required_fields=REQ); a2.publish("k1", R); s2.put_if_absent("atomic/ptr/" + a2._ptr_key("k9").split("/")[-1], b"0" * 64)
        with self.assertRaises(IntegrityFailure): a2.read("k9")
if __name__ == "__main__": unittest.main()
