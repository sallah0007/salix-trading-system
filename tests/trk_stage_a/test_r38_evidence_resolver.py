"""R38 B19: evidence-resolution API. Exact-truth negatives per dimension; signer alone insufficient; pins; watermark; revocation; tamper; use-time re-resolution; unrelated baseline. Candidate store, no admission: nothing is authoritative."""
import dataclasses, json, unittest
from stage_a.errors import Refusal
from stage_a.storage.object_store import InMemoryObjectStore
from stage_a.coordination.object_store_journal import ObjectStoreJournal
from stage_a.tracker import evidence_resolver as ER
from stage_a.tracker.evidence_truth import EvidenceRecord, TransitionClaim, VALID, INVALID, UNPROVABLE
def store():
    j = ObjectStoreJournal(InMemoryObjectStore(), "evid", "w"); j.acquire_epoch(); return ER.JournalEvidenceStore(j, "candidate-store")
def rec(ref="E1", **o):
    d = dict(ref=ref, subject="S", version_or_hash="v1", instrument="XAUUSD", timeframe="H4", battery="B", vintage="V", dependencies=("D1",), result="PASS", available_at=10, max_age=100, revoked=False, current=True, approval_state="APPROVED"); d.update(o); return EvidenceRecord(**d)
def claim(**o):
    d = dict(subject="S", version_or_hash="v1", instrument="XAUUSD", timeframe="H4", battery="B", vintage="V", dependencies=("D1",), expected_result="PASS", required_approval="APPROVED", evidence_refs=("E1",)); d.update(o); return TransitionClaim(**d)
def pins(s, *refs): return {r: s.snapshot()[1][r][1] for r in refs}
def setup(**o):
    s = store(); s.put(rec(**o)); return s, ER.EvidenceResolver(s)
class Resolve(unittest.TestCase):
    def test_exact_match_is_valid_but_never_authoritative_and_cannot_be_required_current(self):
        s, r = setup(); x = r.resolve(claim(), pins(s, "E1"), 20, 15); self.assertEqual((x.status, x.authoritative, x.valid_until), (VALID, False, 110)); self.assertEqual(x.refs[0][0], "E1")
        with self.assertRaises(Refusal) as c: x.require_authoritative_current()
        self.assertEqual(c.exception.code, "EVIDENCE_STORE_NOT_ADMITTED_HELD")
    def test_every_dimension_mismatch_is_invalid(self):
        s, r = setup(); p = pins(s, "E1")
        for f, v in (("subject", "S2"), ("version_or_hash", "v2"), ("instrument", "EURUSD"), ("timeframe", "H1"), ("battery", "B2"), ("vintage", "V2"), ("dependencies", ("D2",)), ("expected_result", "FAIL"), ("required_approval", "PENDING")):
            x = r.resolve(claim(**{f: v}), p, 20, 15); self.assertEqual(x.status, INVALID, f); self.assertTrue(any("MISMATCH" in q for q in x.reasons), f)
    def test_signer_or_authorized_actor_alone_is_not_evidence(self):
        s, r = setup(); x = r.resolve(claim(evidence_refs=(), signed_by="OWNER"), {}, 20, 15); self.assertEqual((x.status, x.reasons), (INVALID, ("NO_EVIDENCE_REFERENCED",)))
        x = r.resolve(claim(evidence_refs=("NOPE",), signed_by="OWNER"), {}, 20, 15); self.assertEqual(x.status, INVALID); self.assertIn("EVIDENCE_MISSING:NOPE", x.reasons)
        self.assertEqual(r.resolve(claim(signed_by="OWNER"), pins(s, "E1"), 20, 15).status, VALID)                               # the signer neither helps nor hurts a genuinely matching record
    def test_unpinned_wrongly_pinned_and_swapped_content_is_refused(self):
        s, r = setup(); self.assertEqual(r.resolve(claim(), {}, 20, 15).reasons, ("EVIDENCE_HASH_NOT_PINNED_OR_MISMATCH:E1",)); self.assertEqual(r.resolve(claim(), {"E1": "0" * 64}, 20, 15).status, INVALID)
        s2 = store(); s2.put(rec(result="FAIL")); self.assertEqual(ER.EvidenceResolver(s2).resolve(claim(), pins(s, "E1"), 20, 15).status, INVALID)              # pins from a different record
    def test_watermark_staleness_future_revocation_and_currentness(self):
        s, r = setup(); p = pins(s, "E1")
        self.assertIn("EVIDENCE_BEYOND_WATERMARK:E1", r.resolve(claim(), p, 20, 9).reasons)                                       # available_at 10 > watermark 9
        self.assertEqual(r.resolve(claim(), p, 200, 15).status, INVALID); self.assertEqual(r.resolve(claim(), p, 5, 15).status, INVALID)      # stale / future
        s3, r3 = setup(current=False); self.assertTrue(any("NOT_CURRENT" in q for q in r3.resolve(claim(), pins(s3, "E1"), 20, 15).reasons))
        s.revoke("E1", "bad"); self.assertTrue(any("REVOKED" in q for q in r.resolve(claim(), p, 20, 15).reasons))
    def test_tampered_record_and_ambiguous_duplicate_fail_closed(self):
        s, r = setup(); j = s._j; b = json.loads(j.read_from(1)[0].body_json); p = pins(s, "E1"); b2 = dict(b, result="FAIL"); j.append(j.head(), ER.REC_KIND, b2)      # content_hash no longer matches the body
        self.assertTrue(any("ALTERED" in q for q in r.resolve(claim(), p, 20, 15).reasons))
        s2, r2 = setup(); s2.put(rec(available_at=11)); self.assertTrue(any("AMBIGUOUS" in q for q in r2.resolve(claim(), {"E1": "x"}, 20, 15).reasons))
        s3, r3 = setup(); s3.put(rec()); self.assertEqual(r3.resolve(claim(), pins(s3, "E1"), 20, 15).status, VALID)               # identical duplicate is not ambiguous
    def test_use_time_reresolution_catches_later_revocation_and_a_receipt_for_other_evidence(self):
        s, r = setup(); p = pins(s, "E1"); x = r.resolve(claim(), p, 20, 15); self.assertEqual(r.use(x, claim(), p, 30, 15).status, VALID)
        s.revoke("E1", "later")
        with self.assertRaises(Refusal) as c: r.use(x, claim(), p, 31, 15)
        self.assertEqual(c.exception.code, "EVIDENCE_NOT_VALID_AT_USE")
        s2, r2 = setup(); y = r2.resolve(claim(), pins(s2, "E1"), 20, 15); s4 = store(); s4.put(rec(ref="E1", available_at=12)); r4 = ER.EvidenceResolver(s4)
        with self.assertRaises(Refusal) as c: r4.use(y, claim(), pins(s4, "E1"), 30, 15)
        self.assertEqual(c.exception.code, "EVIDENCE_RECEIPT_DOES_NOT_BIND_CURRENT_EVIDENCE")
    def test_unrelated_record_and_unrelated_claim_baseline_positive_and_interface_checks(self):
        s, r = setup(); s.put(rec(ref="E2", subject="OTHER")); p = pins(s, "E1", "E2"); self.assertEqual(r.resolve(claim(), p, 20, 15).status, VALID); self.assertEqual(r.resolve(claim(subject="OTHER", evidence_refs=("E2",)), p, 20, 15).status, VALID)
        self.assertEqual(r.resolve(claim(), p, True, 15).status, UNPROVABLE)
        with self.assertRaises(Refusal): ER.EvidenceResolver(object())
        with self.assertRaises(Refusal): s.put(dataclasses.replace(rec(), revoked=True))
if __name__ == "__main__": unittest.main()
