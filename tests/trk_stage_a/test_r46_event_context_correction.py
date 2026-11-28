"""R46 (root reproduction 3): a correction's fact and lineage become visible together; any failed/unknown phase leaves it hidden; exact retry completes it; legacy facts stay readable.
Candidate/in-memory only; the JSON codec is a TEST encoding (D13 unsupplied); no provider/cross-HEAD atomicity is claimed. A pass clears no gate."""
import unittest
from stage_a.errors import Refusal, IntegrityFailure
from stage_a.context.event_context_store import EventContextStore as ECS, FACT, CORR, INTENT
from stage_a.storage.e05_index import E05Index
from stage_a.storage.object_store import InMemoryObjectStore
from .test_r43_event_context_store import enc, dec, ident, cols, F1, code

class Boom(RuntimeError): pass
class Faulty(InMemoryObjectStore):
    """fails put_if_absent for `prefix` either BEFORE the write (not committed) or AFTER it (committed, outcome unknown)."""
    def __init__(self): super().__init__(); self.fail = None
    def put_if_absent(self, k, b):
        if self.fail and k.startswith(self.fail[0]):
            when = self.fail[1]; self.fail = None
            if when == "before": raise Boom("CORRECTION_WRITE_FAILED")
            super().put_if_absent(k, b); raise Boom("CORRECTION_WRITE_UNKNOWN")
        return super().put_if_absent(k, b)
F2 = {"id": "EC2", "asof": 8, "t": 4, "map": "M1"}
def rows(s):
    ix = E05Index(); ix.rebuild({"ec": s.source()}); return ix
def visible_ids(s):
    return sorted(r["event_context_identity"] for _, r in s.source()[1]())

class Correction(unittest.TestCase):
    def mk(self): self.raw = Faulty(); return ECS(self.raw, encode=enc, decode=dec, identity_of=ident, columns_of=cols)
    def test_every_phase_failure_or_unknown_commit_leaves_the_correction_hidden_and_exact_retry_completes_it(self):
        for prefix in (INTENT, FACT, CORR):
            for when in ("before", "after"):
                s = self.mk(); s.put(F1); self.raw.fail = (prefix, when)
                with self.assertRaises(Boom): s.put(F2, corrects="EC1")
                if (prefix, when) != (CORR, "after"):          # lineage commit unknown-but-written is, by construction, the confirmed boundary: see below
                    self.assertIsNone(s.get("EC2"), (prefix, when)); self.assertEqual(visible_ids(s), ["EC1"], (prefix, when)); self.assertEqual(s.corrections_of("EC1"), [])
                    if prefix != INTENT or when == "after":
                        self.assertEqual(s.pending(), ["EC2>EC1"])
                    self.assertEqual(code(s.put, F2), "EVENT_CONTEXT_PARTIAL_CORRECTION_PENDING_RETRY_THE_EXACT_CORRECTION") if prefix != INTENT or when == "after" else None
                self.assertEqual(s.put(F2, corrects="EC1"), "EC2")                          # exact retry
                self.assertEqual(s.get("EC2"), F2); self.assertEqual(s.corrections_of("EC1"), ["EC2"]); self.assertEqual(visible_ids(s), ["EC1", "EC2"]); self.assertEqual(s.pending(), [])
                rows(s)                                                                      # E05 rebuild succeeds with both rows
    def test_a_different_lineage_for_a_pending_correction_is_an_integrity_failure(self):
        s = self.mk(); s.put(F1); s.put({"id": "EC0", "asof": 1, "t": 1, "map": "M"}); self.raw.fail = (FACT, "before")
        with self.assertRaises(Boom): s.put(F2, corrects="EC1")
        self.assertEqual(code(s.put, F2, corrects="EC0"), "INTEGRITY_FAILURE"); self.assertIsNone(s.get("EC2"))
    def test_a_pending_correction_cannot_itself_be_corrected_or_used_as_a_target(self):
        s = self.mk(); s.put(F1); self.raw.fail = (CORR, "before")
        with self.assertRaises(Boom): s.put(F2, corrects="EC1")
        self.assertEqual(code(s.put, {"id": "EC3", "asof": 9, "t": 4, "map": "M"}, corrects="EC2"), "EVENT_CONTEXT_CORRECTION_TARGET_UNKNOWN")
    def test_normal_facts_and_complete_corrections_are_unchanged_and_legacy_facts_stay_readable(self):
        s = self.mk(); s.put(F1); s.put(F2, corrects="EC1"); self.assertEqual((s.get("EC1"), s.get("EC2"), s.corrections_of("EC1")), (F1, F2, ["EC2"])); self.assertEqual(s.put(F2), "EC2")
        legacy = {"id": "EC9", "asof": 1, "t": 1, "map": "M"}; import hashlib
        self.raw.put_if_absent(FACT + hashlib.sha256(b"EC9").hexdigest(), enc(legacy))        # a pre-R46 fact: no intent record
        self.assertEqual(s.get("EC9"), legacy); self.assertIn("EC9", visible_ids(s))
if __name__ == "__main__": unittest.main()
