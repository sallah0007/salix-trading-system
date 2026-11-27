"""R36: ML dataset request / union-lineage / claim caller (Addendum s3-s7)."""
import dataclasses, unittest
from stage_a.errors import Refusal
from stage_a.ml import dataset_manifest as DM, dataset_authority as DA, consumption_claim as CC, generation_lifecycle as GL
from stage_a.gateway import contracts as G
from stage_a.gateway.v038 import FinalResolutionStore, FinalResolutionIdentity as FI
from .test_boundaries import _gw, _entry, _health, I
from .test_r35_dataset_manifest import ds
from .test_r29_generation_lifecycle import man
def code(f, *a, **k):
    try: f(*a, **k)
    except Refusal as e: return e.code
class Rig:
    def __init__(self):
        self.reg = DM.DatasetRegistry({"w"}, "GRANT"); self.gr = GL.GenerationRegistry(); self.auth = DA.DatasetAuthority(self.reg, self.gr)
        self.g = _gw(); self.g.final_store = FinalResolutionStore(); self.e = _entry()
    def issue(self, rid, bid, win="W1", consumer="ML"):
        return self.g.resolve_window(rid, FI(consumer, bid, "XAUUSD", win), self.e, I, I, 3, 10, _health())
class Request(unittest.TestCase):
    def test_link_only_for_the_issued_ml_binding_the_binding_id_comes_from_the_identity_and_failure_writes_nothing(self):
        r = Rig(); b1 = r.issue("req1", "B1"); kw = dict(gateway=r.g, final_store=r.g.final_store)
        h = r.auth.request_binding("w", ds("D1"), b1, request_id="req1", **kw); self.assertEqual((h["binding_id"], h["dataset_manifest_id"], h["issuance_checked"], h["verified"]), ("B1", "D1", True, False)); self.assertEqual(r.reg.binding_index(), {"B1": ["D1"]})
        self.assertEqual(r.auth.request_binding("w", ds("D1"), b1, request_id="req1", **kw)["dataset_manifest_id"], "D1")                                            # identical retry idempotent
        b2 = r.issue("req2", "B2"); self.assertEqual(code(r.auth.request_binding, "w", ds("D9"), b2, request_id="req1", **kw), "DATASET_BINDING_OUTCOME_NOT_THE_STORED_FINAL_OUTCOME"); self.assertIsNone(r.reg.manifest("D9"))   # nothing registered
        self.assertEqual(code(r.auth.request_binding, "w", ds("D9"), b2, request_id="nope", **kw), "DATASET_REQUEST_NOT_ISSUED_FOR_ML_BINDING"); self.assertEqual(code(r.auth.request_binding, "w", dataclasses.replace(ds("D1"), dataset_hash="x"), b1, request_id="req1", **kw), "DATASET_MANIFEST_IMMUTABLE")
        self.assertEqual(code(r.auth.request_binding, "w", ds("D2"), b1, request_id="req1", **kw), "DATASET_LINK_IMMUTABLE"); self.assertEqual(r.reg.binding_index(), {"B1": ["D1"]})          # another manifest cannot take B1
        fw = r.issue("req3", "B3", consumer="FW"); self.assertEqual(code(r.auth.request_binding, "w", ds("D3"), fw, request_id="req3", **kw), "DATASET_REQUEST_NOT_ISSUED_FOR_ML_BINDING")
        forged = G.Binding(b1.request_id, b1.entry, b1.delivered_feature_hash, b1.fence); self.assertEqual(code(r.auth.request_binding, "w", ds("D1"), forged, request_id="req1", **kw), "DATASET_BINDING_OUTCOME_NOT_GATEWAY_ISSUED")
        b5 = r.issue("req5", "B5"); f5 = G.Binding(b5.request_id, b5.entry, b5.delivered_feature_hash, b5.fence); self.assertEqual(code(r.auth.request_binding, "w", ds("D5"), f5, request_id="req5", **kw), "DATASET_BINDING_OUTCOME_NOT_GATEWAY_ISSUED"); self.assertIsNone(r.reg.manifest("D5")); self.assertNotIn("B5", r.reg.binding_index())     # refused BEFORE any write
        self.assertEqual(code(DA.DatasetAuthority(DM.DatasetRegistry()).request_binding, "w", ds("D1"), b1, request_id="req1", **kw), "ML_PRINCIPAL_GRANTS_UNBOUND_HELD"); self.assertEqual(code(r.auth.request_binding, "x", ds("D1"), b1, request_id="req1", **kw), "ML_CALLER_NOT_GRANTED")
class Union(unittest.TestCase):
    def rig(self):
        r = Rig()
        for i in ("D1", "D2", "D3"): r.reg.register("w", ds(i))
        r.gr.register_manifest(man("G1")); r.gr.append_lifecycle("G1", "COMPLETE_CERTIFIED", 1, "c", "A"); return r
    def test_union_is_append_only_acyclic_and_membership_must_be_known(self):
        r = self.rig(); a = r.auth
        self.assertEqual(a.declare_union("w", "D1", ("D2", "D3"), ("G1",)), (("D2", "D3"), ("G1",))); self.assertEqual(a.declare_union("w", "D1", ("D3", "D2"), ("G1",)), (("D2", "D3"), ("G1",)))      # order-insensitive idempotent
        self.assertEqual(code(a.declare_union, "w", "D1", ("D2",), ()), "UNION_IMMUTABLE"); self.assertEqual(code(a.declare_union, "w", "D2", ("D2",)), "UNION_SELF_MEMBERSHIP"); self.assertEqual(code(a.declare_union, "w", "D2", ("D1",)), "UNION_CYCLE")
        self.assertEqual(code(a.declare_union, "w", "D3", ("NOPE",)), "UNION_MEMBER_DATASET_UNKNOWN"); self.assertEqual(code(a.declare_union, "w", "D3", (), ("GX",)), "UNION_GENERATION_UNKNOWN"); self.assertEqual(code(a.declare_union, "w", "ZZ", ()), "UNION_DATASET_UNKNOWN"); self.assertEqual(code(a.declare_union, "x", "D3", ()), "ML_CALLER_NOT_GRANTED"); self.assertEqual(code(a.declare_union, "w", "D3", ["D2"]), "UNION_MALFORMED")
        self.assertIsNone(a.union_of("D2"))                                                                                          # a refused declaration left nothing
    def test_gate_unknown_without_declaration_blocked_on_revoked_member_clear_only_when_every_node_is_declared_and_clean(self):
        r = self.rig(); a = r.auth
        self.assertEqual(a.gate("D1")["verdict"], "BLOCKED_UNKNOWN")                                                                 # undeclared root
        a.declare_union("w", "D1", ("D2",)); self.assertEqual(a.gate("D1")["verdict"], "BLOCKED_UNKNOWN")                            # member D2 has no declaration: not clean
        a.declare_union("w", "D2", ()); self.assertEqual(a.gate("D1")["verdict"], "CLEAR")                                           # control: every node declared, none revoked
        r.reg.revoke("w", "D2", 5, "contamination", "AUTH"); self.assertEqual(a.gate("D1")["verdict"], "BLOCKED")
        a.declare_union("w", "D3", (), ("G1",)); self.assertEqual(a.gate("D3")["verdict"], "BLOCKED_UNKNOWN"); self.assertEqual(a.gate("D3", {"G1": []})["verdict"], "CLEAR"); r.gr.append_lifecycle("G1", "REVOKED", 9, "bad", "A"); self.assertEqual(a.gate("D3", {"G1": []})["verdict"], "BLOCKED")
class Claims(unittest.TestCase):
    def test_claim_uses_the_datasets_own_feed_era_requires_the_link_and_a_clean_dataset(self):
        r = Rig(); b1 = r.issue("req1", "B1"); r.auth.request_binding("w", ds("D1"), b1, gateway=r.g, final_store=r.g.final_store, request_id="req1"); era = ds("D1").feed_era_id; fl = CC.FamilyLedgerRef("F1", "v1", "h", 5)
        c = CC.ConsumptionClaim("C1", "B1", "D1", 10, True, era, fl); self.assertIs(r.auth.record_claim(c), c)
        self.assertEqual(code(r.auth.record_claim, dataclasses.replace(c, claim_id="C2", feed_era_id="OTHER")), "FEED_ERA_MISMATCH"); self.assertEqual(code(r.auth.record_claim, dataclasses.replace(c, claim_id="C3", family_ledger=None)), "AUTHORITY_BEARING_CLAIM_WITHOUT_FAMILY_LEDGER_REF")
        self.assertEqual(code(r.auth.record_claim, dataclasses.replace(c, claim_id="C4", consumer_binding_id="B9")), "CLAIM_BINDING_NOT_LINKED_TO_THIS_DATASET"); self.assertEqual(code(r.auth.record_claim, dataclasses.replace(c, claim_id="C5", manifest_id="NOPE")), "CLAIM_DATASET_UNKNOWN")
        r.reg.revoke("w", "D1", 11, "bad", "A"); self.assertEqual(code(r.auth.record_claim, dataclasses.replace(c, claim_id="C6", claim_ts=12)), "CLAIM_ON_REVOKED_DATASET"); self.assertIs(r.auth.record_claim(c), c)                 # the earlier claim is never rewritten
        cc = r.auth.correlate("B1"); self.assertEqual((cc["link"], cc["dataset_to_generation_key"], cc["qualified"]), ("PRESENT", "PRESENT_UNVERIFIED_NO_SOURCE_DEFINED_KEY", False)); self.assertEqual(r.auth.correlate("none")["link"], "MISSING")
if __name__ == "__main__": unittest.main()
