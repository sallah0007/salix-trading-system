import json, unittest
from stage_a.errors import Refusal, IntegrityFailure
from stage_a.context.event_context_store import EventContextStore as ECS
from stage_a.storage import e05_sources as S
from stage_a.storage.e05_index import E05Index
from stage_a.storage.object_store import InMemoryObjectStore
# TEST-supplied interface: a JSON encoding is NOT the canonical Event/Context byte layout (D13 is unsupplied)
enc = lambda f: json.dumps(f, sort_keys=True, separators=(",", ":")).encode(); dec = lambda b: json.loads(b)
ident = lambda f: f["id"]; cols = lambda f: dict(event_context_identity=f["id"], available_asof=f["asof"], event_time=f["t"], applicability_map_ref=f["map"])
def code(f, *a, **k):
    try: f(*a, **k)
    except (Refusal, IntegrityFailure) as e: return getattr(e, "code", type(e).__name__)
F1 = {"id": "EC1", "asof": 5, "t": 4, "map": "M1"}
class Store(unittest.TestCase):
    def mk(self): self.raw = InMemoryObjectStore(); return ECS(self.raw, encode=enc, decode=dec, identity_of=ident, columns_of=cols)
    def test_unsupplied_encoding_interface_holds(self):
        self.assertEqual(code(ECS, InMemoryObjectStore(), encode=None, decode=dec, identity_of=ident, columns_of=cols), "EVENT_CONTEXT_ENCODING_INTERFACE_UNBOUND_HELD"); self.assertEqual(code(ECS, None, encode=enc, decode=dec, identity_of=ident, columns_of=cols), "EVENT_CONTEXT_ENCODING_INTERFACE_UNBOUND_HELD")
    def test_immutable_idempotent_and_a_correction_is_a_new_identity_with_lineage(self):
        s = self.mk(); self.assertEqual(s.put(F1), "EC1"); self.assertEqual(s.put(F1), "EC1"); self.assertEqual(s.get("EC1"), F1); self.assertIsNone(s.get("NOPE"))
        self.assertEqual(code(s.put, dict(F1, t=9)), "INTEGRITY_FAILURE")                     # same identity, other bytes: never an overwrite
        F2 = {"id": "EC2", "asof": 8, "t": 4, "map": "M1"}; s.put(F2, corrects="EC1"); self.assertEqual(s.corrections_of("EC1"), ["EC2"]); self.assertEqual(s.get("EC1"), F1)
        self.assertEqual(code(s.put, {"id": "EC3", "asof": 1, "t": 1, "map": "M"}, corrects="GHOST"), "EVENT_CONTEXT_CORRECTION_TARGET_UNKNOWN"); self.assertEqual(code(s.put, F1, corrects="EC1"), "EVENT_CONTEXT_CORRECTION_TARGET_UNKNOWN")
        self.assertIsNone(s.get("EC3")); self.assertEqual(code(s.put, {"id": "", "asof": 1, "t": 1, "map": "M"}), "EVENT_CONTEXT_FACT_INVALID")
    def test_a_non_round_trip_encoding_and_a_tampered_stored_object_refuse(self):
        raw = InMemoryObjectStore(); bad = ECS(raw, encode=enc, decode=lambda b: {k: v for k, v in json.loads(b).items() if k != "map"}, identity_of=ident, columns_of=cols); self.assertEqual(code(bad.put, F1), "EVENT_CONTEXT_ENCODING_NOT_ROUND_TRIP")
        s = self.mk(); s.put(F1); k = [k for k in self.raw.list_prefix("event-context/fact/")][0]; b, e = self.raw.get(k); self.raw.put_if_match(k, enc(dict(F1, id="EC9")), e); self.assertEqual(code(s.get, "EC1"), "INTEGRITY_FAILURE")
    def test_e05_event_context_rows_rebuild_with_canonical_ref_and_hash_and_drift_is_detected(self):
        s = self.mk(); s.put(F1); ix = E05Index(); ix.rebuild({"ec": s.source()}); res = S.object_resolver(self.raw)
        r = ix.lookup("stagea_event_context_index", {"event_context_identity": "EC1"}, res); self.assertFalse(r.authoritative); self.assertTrue(r["ref"].startswith("object:event-context/fact/"))
        k = self.raw.list_prefix("event-context/fact/")[0]; b, e = self.raw.get(k); self.raw.put_if_match(k, enc(dict(F1, t=0)), e)
        with self.assertRaises(IntegrityFailure): ix.lookup("stagea_event_context_index", {"event_context_identity": "EC1"}, res)
    def test_columns_that_disagree_with_the_identity_refuse(self):
        raw = InMemoryObjectStore(); s = ECS(raw, encode=enc, decode=dec, identity_of=ident, columns_of=lambda f: dict(cols(f), event_context_identity="OTHER")); s.put(F1)
        self.assertEqual(code(E05Index().rebuild, {"ec": s.source()}), "E05_SOURCE_COLUMNS_DISAGREE_WITH_IDENTITY")
    def test_a_fact_stored_under_another_key_is_not_content_addressed_and_refuses(self):
        s = self.mk(); s.put(F1); self.assertTrue(self.raw.put_if_absent("event-context/fact/" + "f" * 64, enc(F1)))                      # same bytes, a key that is not the identity's key
        self.assertEqual(code(E05Index().rebuild, {"ec": s.source()}), "E05_SOURCE_OBJECT_NOT_CONTENT_ADDRESSED")
if __name__ == "__main__": unittest.main()
