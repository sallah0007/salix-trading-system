import unittest
from stage_a.errors import Refusal, IntegrityFailure
from stage_a.gateway import contracts as G
from stage_a.gateway import durable_final_store as D
from stage_a.gateway.v038 import FinalResolutionIdentity as FI
from stage_a.schema.objects import PendingRow
from stage_a.health.evidence import HealthEvidenceSink, FeatureHealthEvidence
from stage_a.storage import e05_sources as S
from stage_a.storage.e05_index import E05Index
from stage_a.storage.object_store import InMemoryObjectStore
from .test_boundaries import _gw, _entry, _health, I
W1, W2 = FI("FW", "B1", "XAUUSD", "WINDOW-1"), FI("FW", "B1", "XAUUSD", "WINDOW-2")
def code(f, *a, **k):
    try: f(*a, **k)
    except (Refusal, IntegrityFailure) as e: return getattr(e, "code", type(e).__name__)
def bind_cols(ident, out): return dict(consumer_binding_id=ident.window_fence_id, consumer_id=ident.consumer_id, purpose="P", decision_window=ident.window_fence_id, final_package_hash="h")
def nd_cols(ident, out): return dict(non_delivery_resolution_id=ident.window_fence_id, resolution_identity=ident.scope, reason_code=getattr(out, "reason", "NONE"), expected_dependency_key="k")
def mk(raw):
    g = _gw(); g.final_store = D.DurableFinalResolutionStore(raw); g.set_watermark(100)
    b = g.resolve_window("r1", W1, _entry(), I, I, 3, 10, _health()); g.set_watermark(5)
    n = g.resolve_window("r2", W2, _entry(), I, I, 3, 10, _health()); return b, n
class FinalResolutionSource(unittest.TestCase):
    def setUp(self):
        self.raw = InMemoryObjectStore(); self.b, self.n = mk(self.raw); self.res = S.object_resolver(self.raw); self.ix = E05Index()
    def src(self, **k): return {"fr": S.final_resolution_source(self.raw, binding_columns=bind_cols, non_delivery_columns=nd_cols, **k)}
    def test_both_outcome_kinds_project_into_their_own_tables_with_canonical_ref_and_hash_and_no_fabricated_epoch(self):
        self.assertIsInstance(self.b, G.Binding); self.ix.rebuild(self.src())
        r = self.ix.lookup("stagea_consumer_binding_index", {"consumer_binding_id": "WINDOW-1"}, self.res); self.assertFalse(r.authoritative); self.assertTrue(r["ref"].startswith("object:final-resolution/id/"))
        self.assertIsNotNone(self.ix.lookup("stagea_non_delivery_index", {"non_delivery_resolution_id": "WINDOW-2"}, self.res)); self.assertEqual(self.ix.verify_all(self.res), 2)
    def test_a_replaced_stored_record_is_drift_and_a_record_under_another_key_refuses(self):
        self.ix.rebuild(self.src()); k = sorted(self.raw.list_prefix("final-resolution/id/"))[0]; before = self.raw._d[k]
        self.raw._d[k] = (before[0] + b" ", before[1] + 1)
        with self.assertRaises(IntegrityFailure): self.ix.verify_all(self.res)
        self.raw._d[k] = before; other = "final-resolution/id/" + "0" * 64; self.raw._d[other] = before
        self.assertEqual(code(self.ix.rebuild, self.src()), "E05_SOURCE_OBJECT_NOT_CONTENT_ADDRESSED")
    def test_an_unmapped_outcome_type_or_missing_mapper_refuses_instead_of_skipping(self):
        self.assertEqual(code(self.ix.rebuild, {"fr": S.final_resolution_source(self.raw, binding_columns=bind_cols)}), "E05_SOURCE_MAPPER_NOT_SUPPLIED")
        self.assertEqual(code(self.ix.rebuild, {"fr": S.final_resolution_source(self.raw, non_delivery_columns=nd_cols)}), "E05_SOURCE_MAPPER_NOT_SUPPLIED")
    def test_a_new_committed_resolution_moves_the_head_and_recovery_rebuilds_the_same_rows(self):
        head, _ = self.src()["fr"]; h0 = head(); self.ix.rebuild(self.src())
        g = _gw(); g.final_store = D.DurableFinalResolutionStore(self.raw); g.final_store.recover(); g.set_watermark(100)
        g.resolve_window("r3", FI("FW", "B1", "XAUUSD", "WINDOW-3"), _entry(), I, I, 3, 10, _health()); self.assertNotEqual(head(), h0)
        ix2 = E05Index(); ix2.rebuild(self.src()); self.assertIsNotNone(ix2.lookup("stagea_consumer_binding_index", {"consumer_binding_id": "WINDOW-3"}, self.res))
    def test_an_absence_outcome_is_refused_not_skipped_and_an_unreadable_listed_object_refuses(self):
        import json
        from stage_a.schema.encoding import Ref
        raw = InMemoryObjectStore(); ident = FI("FW", "B1", "XAUUSD", "WINDOW-9"); out = G.AbsenceApplied("r9", b"f" * 16, "1", Ref("R", b"x", b"v", None))
        raw.put_if_absent(D._ident_key(ident), json.dumps({"identity": D.encode(ident), "outcome": D.encode(out)}, sort_keys=True, separators=(",", ":")).encode())
        src = S.final_resolution_source(raw, binding_columns=bind_cols, non_delivery_columns=nd_cols); self.assertEqual(code(lambda: list(src[1]())), "E05_SOURCE_OUTCOME_TYPE_UNMAPPED")
        class Flaky(InMemoryObjectStore):
            def get(self, k): return None
        f = Flaky(); f._d = dict(raw._d); self.assertEqual(code(lambda: S.final_resolution_source(f)[0]()), "E05_SOURCE_LISTED_OBJECT_UNREADABLE")
class SequenceSources(unittest.TestCase):
    def test_fit_generation_mapping_projects_and_a_changed_generation_hash_is_drift(self):
        fits = {1: "a" * 64, 2: "b" * 64}
        mk_src = lambda: S.sequence_source("stagea_fit_generation_index", lambda: sorted(fits.items()), lambda kv: str(kv[0]), lambda kv: kv[1], lambda kv: dict(fit_generation_ref="fit:%d" % kv[0], feature_id="F", feature_version="1", available_asof=0), ref_prefix="fit:")
        res = S.sequence_resolver(lambda: sorted(fits.items()), lambda kv: str(kv[0]), lambda kv: kv[1], ref_prefix="fit:"); ix = E05Index(); ix.rebuild({"fit": mk_src()})
        self.assertIsNotNone(ix.lookup("stagea_fit_generation_index", {"fit_generation_ref": "fit:1"}, res)); fits[1] = "c" * 64
        with self.assertRaises(IntegrityFailure): ix.lookup("stagea_fit_generation_index", {"fit_generation_ref": "fit:1"}, res)
        self.assertNotEqual(mk_src()[0](), (2, "x"))
    def test_health_evidence_sink_projects_and_a_duplicate_ident_refuses(self):
        sink = HealthEvidenceSink(); sink.emit(FeatureHealthEvidence("1", b"i" * 16, b"t" * 16, materialization_version="m"))
        ident = lambda e: "%s/%s" % (e.feature_version, e.materialization_version); hsh = lambda e: "e" * 64
        cols = lambda e: dict(health_evidence_id=ident(e), subject_id="S", observed_at=1, local_state="OK", carried_upstream_state="OK")
        ix = E05Index(); src = S.sequence_source("stagea_health_index", sink.evidence, ident, hsh, cols, ref_prefix="health:"); ix.rebuild({"h": src})
        res = S.sequence_resolver(sink.evidence, ident, hsh, ref_prefix="health:"); self.assertIsNotNone(ix.lookup("stagea_health_index", {"health_evidence_id": "1/m"}, res))
        sink.emit(FeatureHealthEvidence("1", b"i" * 16, b"t" * 16, materialization_version="m")); self.assertEqual(code(src[0]), "E05_SOURCE_DUPLICATE_IDENT")
    def test_an_empty_ident_refuses_and_a_changed_owner_hash_moves_the_head_under_the_same_ident(self):
        h = ["a" * 64]; mk = lambda i: S.sequence_source("stagea_fit_generation_index", lambda: [1], lambda o: i, lambda o: h[0], lambda o: dict(fit_generation_ref="f", feature_id="F", feature_version="1", available_asof=0), ref_prefix="fit:")
        self.assertEqual(code(lambda: mk("")[0]()), "E05_SOURCE_IDENT_INVALID"); src = mk("1"); h0 = src[0](); h[0] = "b" * 64; self.assertNotEqual(src[0](), h0)
    def test_event_context_has_no_owning_store_and_is_held_not_fabricated(self):
        self.assertEqual(code(S.event_context_source), "E05_SOURCE_EVENT_CONTEXT_HELD_NO_ENCODING_INTERFACE")
    def test_invalid_inputs_refuse(self):
        self.assertEqual(code(S.sequence_source, "t", None, None, None, None, ref_prefix="x:"), "E05_SOURCE_INPUT_INVALID")
if __name__ == "__main__": unittest.main()
