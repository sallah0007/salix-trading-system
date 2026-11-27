import unittest
from stage_a.errors import Refusal
from stage_a.ml import dataset_manifest as DM, six_joins as SJ, generation_lifecycle as GL
from stage_a.gateway import contracts as G
from stage_a.gateway.v038 import FinalResolutionStore, FinalResolutionIdentity as FI
from .test_boundaries import _gw, _entry, _health, I
from .test_r29_generation_lifecycle import man
def code(f, *a, **k):
    try: f(*a, **k)
    except Refusal as e: return e.code
def ds(i="D1", **k):
    d = dict(dataset_manifest_id=i, manifest_hash="h-" + i, dataset_hash="dh-" + i, source_contracts=("SC1",), source_identities=("SRC1",), row_provenance="RP1", instrument_scope=("XAUUSD",), construction_code_version="cv1", transformation_lineage=("T1",), feed_era_id="E1"); d.update(k); return DM.DatasetProvenanceManifest(**d)
def reg(): return DM.DatasetRegistry({"w"}, "SRC-GRANT")
class Registry(unittest.TestCase):
    def test_grants_held_without_a_slot_every_source_named_field_required_and_immutable_idempotent(self):
        self.assertEqual(code(DM.DatasetRegistry().register, "w", ds()), "ML_PRINCIPAL_GRANTS_UNBOUND_HELD"); r = reg(); self.assertEqual(code(r.register, "x", ds()), "ML_CALLER_NOT_GRANTED")
        for f, v in (("dataset_hash", ""), ("source_contracts", ()), ("source_identities", ("a", "a")), ("row_provenance", None), ("instrument_scope", ()), ("construction_code_version", ""), ("transformation_lineage", ()), ("feed_era_id", "")): self.assertEqual(code(r.register, "w", ds(**{f: v})), "DATASET_MANIFEST_MALFORMED", f)
        m = ds(); self.assertIs(r.register("w", m), m); self.assertIs(r.register("w", m), m); import dataclasses; self.assertEqual(code(r.register, "w", dataclasses.replace(m, dataset_hash="other")), "DATASET_MANIFEST_IMMUTABLE")
    def test_revocation_is_append_only_and_unknown_is_not_false(self):
        r = reg(); r.register("w", ds()); self.assertIs(r.is_revoked("D1"), False); self.assertIsNone(r.is_revoked("NOPE")); r.revoke("w", "D1", 5, "contamination", "AUTH"); self.assertIs(r.is_revoked("D1"), True); self.assertIs(r.is_revoked("D1", as_of_ts=4), False)
        r.revoke("w", "D1", 6, "again", "AUTH"); self.assertEqual(len(r._ledger), 1); self.assertEqual(code(r.revoke, "w", "NOPE", 7, "x", "A"), "DATASET_MANIFEST_UNKNOWN")
class RevokedAncestryGate(unittest.TestCase):
    def test_31C_held_back_test_a_fresh_model_on_a_revoked_dataset_is_blocked_with_no_weight_ancestor(self):
        r = reg(); r.register("w", ds()); r.register("w", ds("D2")); r.revoke("w", "D1", 5, "instrument contamination", "AUTH")
        g = DM.revoked_ancestry_gate("MODEL_NEW", {"MODEL_NEW": ["D1"], "D1": []}, r); self.assertEqual((g["verdict"], g["qualified"]), ("BLOCKED", False))
        self.assertEqual(DM.revoked_ancestry_gate("MODEL_CLEAN", {"MODEL_CLEAN": ["D2"], "D2": []}, r)["verdict"], "CLEAR")                             # unrelated clean dataset
        self.assertEqual(DM.revoked_ancestry_gate("M", {"M": ["D2", "X"], "D2": [], "X": []}, r)["verdict"], "BLOCKED_UNKNOWN")                        # an unregistered ancestor is unknown, not clean
    def test_generation_registry_revocation_and_dataset_revocation_are_one_graph(self):
        r = reg(); r.register("w", ds()); gr = GL.GenerationRegistry(); gr.register_manifest(man("G1")); gr.append_lifecycle("G1", "COMPLETE_CERTIFIED", 1, "c", "A"); gr.append_lifecycle("G1", "REVOKED", 2, "bad", "A")
        self.assertEqual(DM.revoked_ancestry_gate("G2", {"G2": ["G1"], "G1": ["D1"], "D1": []}, r, gr)["verdict"], "BLOCKED")
class ReverseLink(unittest.TestCase):
    def test_binding_to_manifest_feeds_the_J1_relation_and_a_wrong_link_is_a_mismatch(self):
        r = reg(); r.register("w", ds()); r.register("w", ds("D2")); r.link_binding("w", "B1", "D1"); self.assertEqual(code(r.link_binding, "w", "B1", "D2"), "DATASET_LINK_IMMUTABLE"); self.assertEqual(code(r.link_binding, "w", "B2", "NOPE"), "DATASET_LINK_UNKNOWN_MANIFEST")
        j = {"binding_id": "B1", "dataset_manifest_id": "D1", "dataset_manifest_hash": "h-D1"}
        from .test_r32_six_joins import good, reg as greg
        gr = greg("M1")
        def j1(jj, **k): d = good(gr); d[SJ.JOINS[0]] = jj; return {n: st for n, st, _ in SJ.check_six_joins(d, gr, fence=10, **k).statuses}[SJ.JOINS[0]]
        self.assertEqual(j1(j, binding_to_manifest=r.binding_index(), dataset_manifests=r.manifest_index(), consumer_binding_id="B1"), SJ.VERIFIED_AGAINST_REGISTRY)
        self.assertEqual(j1(dict(j, dataset_manifest_id="D2", dataset_manifest_hash="h-D2"), binding_to_manifest=r.binding_index(), dataset_manifests=r.manifest_index(), consumer_binding_id="B1"), SJ.MISMATCH)      # D2 is known but is not THIS binding's manifest
    def test_bind_time_health_only_for_an_outcome_the_same_gateway_and_final_store_issued_for_this_binding(self):
        r = reg(); r.register("w", ds()); r.register("w", ds("D2")); r.link_binding("w", "B1", "D1"); r.link_binding("w", "B2", "D2")
        g = _gw(); g.final_store = FinalResolutionStore(); e = _entry(); w1 = FI("ML", "B1", "XAUUSD", "W1"); w2 = FI("ML", "B2", "XAUUSD", "W1")
        b1 = g.resolve_window("req1", w1, e, I, I, 3, 10, _health()); b2 = g.resolve_window("req2", w2, e, I, I, 3, 10, _health()); self.assertIsInstance(b1, G.Binding)
        kw = dict(gateway=g, final_store=g.final_store)
        h = r.bind_time_health("B1", b1, request_id="req1", **kw); self.assertEqual((h["dataset_manifest_id"], h["health_resolution_ref"], h["verified"], h["issuance_checked"], h["window_identity"]), ("D1", b1.entry.bound_health_resolution_ref, False, True, w1))
        self.assertEqual(code(r.bind_time_health, "B1", b1, request_id="req9", **kw), "DATASET_BINDING_REQUEST_NOT_ISSUED_FOR_BINDING")       # an unknown request id
        self.assertEqual(code(r.bind_time_health, "B1", b2, request_id="req2", **kw), "DATASET_BINDING_REQUEST_NOT_ISSUED_FOR_BINDING")             # root repro: B2's issued Binding presented for B1 (R35 returned B1/D1/<B2 health>)
        self.assertEqual(code(r.bind_time_health, "B1", b2, request_id="req1", **kw), "DATASET_BINDING_OUTCOME_NOT_THE_STORED_FINAL_OUTCOME")        # B1's request with B2's outcome
        forged = G.Binding(b1.request_id, b1.entry, b1.delivered_feature_hash, b1.fence); self.assertEqual(forged, b1)
        self.assertEqual(code(r.bind_time_health, "B1", forged, request_id="req1", **kw), "DATASET_BINDING_OUTCOME_NOT_GATEWAY_ISSUED")             # typed, equal, but never issued: not the confirmed object
        fw = g.resolve_window("req3", FI("FW", "B1", "XAUUSD", "W1"), e, I, I, 3, 10, _health()); self.assertEqual(code(r.bind_time_health, "B1", fw, request_id="req3", **kw), "DATASET_BINDING_REQUEST_NOT_ISSUED_FOR_BINDING")   # foreign consumer
        g.set_watermark(1); nd = _gw().resolve("r2", _entry(), I, I, 3, 200, _health()); self.assertIsNone(r.bind_time_health("B1", nd, request_id="r2", **kw)); self.assertIsNone(r.bind_time_health("B-unlinked", b1, request_id="req1", **kw))
class RevocationTimeSemantics(unittest.TestCase):
    def test_revocation_is_effective_from_its_own_timestamp_and_the_ledger_cannot_go_backwards(self):
        r = reg(); r.register("w", ds()); r.register("w", ds("D2")); r.revoke("w", "D1", 5, "x", "A")
        self.assertIs(r.is_revoked("D1", 4), False); self.assertIs(r.is_revoked("D1", 5), True); self.assertIs(r.is_revoked("D1", 6), True)
        self.assertEqual(code(r.revoke, "w", "D2", 4, "later-discovered", "A"), "ML_LIFECYCLE_TS_REGRESSED"); self.assertIs(r.is_revoked("D2"), False)
if __name__ == "__main__": unittest.main()
