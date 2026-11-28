"""R50: typed H1 record -> FW10/H3 owning request-return, and the ML_FW_AUGMENTED governed return/rebind caller (candidate; SIMULATION gateway)."""
import dataclasses, unittest
from stage_a.errors import Refusal
from stage_a.fw import outcome_desk as OD
from stage_a.fw.lanes import ConsumerManifest as M
from stage_a.gateway import outcome_series as H
from stage_a.gateway.h1_record import TypedH1
from stage_a.gateway.v038 import FinalResolutionStore, FinalResolutionIdentity as FI
from stage_a.ml import receiver as R
from stage_a.ml.augmented_desk import AugmentedDesk, FWReturnRecord
from . import test_boundaries as B
from .test_boundaries import _gw, _entry, _health, I
from .test_r28_h3 import pkg, ctx
def code(f, *a, **k):
    try: f(*a, **k)
    except Refusal as e: return e.code
def h1(**o):
    d = {k: "x" for k in ("CONSUMER_BINDING_ID", "CONSUMER_ID", "TARGET_CONSUMER", "REQUEST_ID", "BOUND_PAYLOAD_OR_PACKAGE_ID", "PACKAGE_HASH", "PURPOSE", "TEMPORAL_CONTRACT_ID", "SOURCE_VINTAGE_CAUSAL_POLICY_ID", "RESOLVER_POLICY_ID", "FINAL_PACKAGE_HASH", "BOUND_HEALTH_RESOLUTION_REF")}
    d.update(CONSUMER_BINDING_ID="B1", CONSUMER_ID="FW", TARGET_CONSUMER="FW", REQUEST_ID="rq1", PACKAGE_CLASS="FW_PACKAGE", BOUND_FEATURE_IDS_AND_VERSIONS=[["f", "1"]], ELIGIBILITY_AS_OF_T=10, OMISSIONS_EXCLUSIONS_REASON_CODES=[], CREATED_TS=1,
             ISSUER="TRACKER_CONSUMER_GATEWAY", BOUND_HEALTH_RESOLVED_AT=1, RESOLUTION_VISIBILITY_WATERMARK=1, MANIFEST_OR_DATASET_BINDING_ID="M1"); d.update(o); return d

class TypedH1Record(unittest.TestCase):
    def rig(self):
        g = _gw(); g.final_store = FinalResolutionStore(); w = FI("FW", "M1", "XAUUSD", "W1"); g.resolve_window("rq1", w, _entry(), I, I, 3, 10, _health()); return g, w
    def test_positive_h1_record_registers_the_cbid_relation_and_the_request_return_is_issued_and_immutable(self):
        g, w = self.rig(); d = OD.OutcomeSeriesDesk(g); rec = TypedH1(h1()); d.register_h1(rec, identity=w)
        r = d.request("rq1", pkg(), ctx(), identity=w); self.assertEqual((r.consumer_binding_id, r.decision.status, r.delivered), ("B1", H.PASS_STRUCTURAL, False)); self.assertNotEqual(w.manifest_or_dataset_binding_id, rec.fields["CONSUMER_BINDING_ID"])
    def test_record_is_validated_deep_frozen_and_detached_from_the_callers_dict(self):
        src = h1(); rec = TypedH1(src); src["CONSUMER_BINDING_ID"] = "HACKED"; src["BOUND_FEATURE_IDS_AND_VERSIONS"].append(["z", "9"])
        self.assertEqual(rec.fields["CONSUMER_BINDING_ID"], "B1"); self.assertEqual(rec.fields["BOUND_FEATURE_IDS_AND_VERSIONS"], (("f", "1"),))
        self.assertEqual(code(setattr, rec, "x", 1), "H1_RECORD_IMMUTABLE")
        with self.assertRaises(TypeError): rec.fields["a"] = 1
        with self.assertRaises(TypeError): rec.fields["BOUND_FEATURE_IDS_AND_VERSIONS"][0][0] = "q"
        t = rec.thaw(); t["CONSUMER_BINDING_ID"] = "Z"; self.assertEqual(rec.fields["CONSUMER_BINDING_ID"], "B1")
    def test_incomplete_or_inconsistent_h1_is_refused_by_the_existing_checker(self):
        for o, c in (({"ISSUER": "X"}, "BAD_ISSUER"), ({"PACKAGE_CLASS": "ML_PACKAGE", "ML_MANIFEST_CLASS": "OFFICIAL_ML_TRAINING_MANIFEST", "GENERATION_AUTHORITY_CLASS": "ML_STANDALONE"}, "H1_CONSUMER_PACKAGE_CLASS_MISMATCH"), ({"PURPOSE": None}, "H1_FIELD_MISSING"), ({"CONSUMER_BINDING_ID": ""}, "H1_ID_FIELD_NOT_A_NONEMPTY_STRING")):
            self.assertEqual(code(TypedH1, h1(**o)), c, o)
        self.assertEqual(code(TypedH1, [1]), "H1_RECORD_NOT_A_MAPPING")
    def test_a_record_without_a_manifest_binding_id_cannot_be_correlated_and_nothing_is_derived_from_the_cbid(self):
        g, w = self.rig(); d = OD.OutcomeSeriesDesk(g); x = h1(); del x["MANIFEST_OR_DATASET_BINDING_ID"]
        self.assertEqual(code(d.register_h1, TypedH1(x), identity=w), "H1_MANIFEST_OR_DATASET_BINDING_ID_HELD")
        self.assertEqual(code(d.request, "rq1", pkg(), ctx(), identity=w), "OUTCOME_REQUEST_CONSUMER_BINDING_NOT_CORRELATED")
    def test_wrong_consumer_wrong_manifest_untyped_and_conflicting_records_refuse(self):
        g, w = self.rig(); d = OD.OutcomeSeriesDesk(g)
        self.assertEqual(code(d.register_h1, h1(), identity=w), "H1_RECORD_NOT_TYPED")                                           # a loose dict is not a typed record
        self.assertEqual(code(d.register_h1, TypedH1(h1(MANIFEST_OR_DATASET_BINDING_ID="OTHER")), identity=w), "IDENTITY_BINDING_DIFFERS_FROM_BINDING")
        self.assertEqual(code(d.register_h1, TypedH1(h1(CONSUMER_ID="ML", PACKAGE_CLASS="ML_PACKAGE", TARGET_CONSUMER="ML", ML_MANIFEST_CLASS="OFFICIAL_ML_TRAINING_MANIFEST", GENERATION_AUTHORITY_CLASS="ML_STANDALONE")), identity=w), "CONSUMER_BINDING_NOT_THE_ISSUED_WINDOW_IDENTITY")
        d.register_h1(TypedH1(h1()), identity=w); self.assertEqual(code(d.register_h1, TypedH1(h1(CONSUMER_BINDING_ID="B2")), identity=w), "CONSUMER_BINDING_REQUEST_ALREADY_CORRELATED")

FWML = lambda: {"fw": M("fw", "FW", (b"a",)), "ml": M("ml", "ML", (b"a",), derived_from="fw")}
Q = b"quant"
def mlh1(req="ml-rq", mid="MM1", **o):
    d = dict(CONSUMER_BINDING_ID="MB1", CONSUMER_ID="ML", TARGET_CONSUMER="ML", REQUEST_ID=req, PACKAGE_CLASS="ML_PACKAGE", ML_MANIFEST_CLASS="OFFICIAL_ML_TRAINING_MANIFEST", GENERATION_AUTHORITY_CLASS="ML_STANDALONE", MANIFEST_OR_DATASET_BINDING_ID=mid); d.update(o); return h1(**d)
class Augmented(unittest.TestCase):
    """R51: FW returns must be ACTUALLY ISSUED by the owning FW outcome desk; the reverse-H1 association is HELD until an explicit mapping is checked against the final store's issued ML identity."""
    def rig(self, fw_req="fw-req", ml_req="ml-rq", ml_win=True, issue_fw=True):
        gw = B._gw(avail=9); gw.final_store = FinalResolutionStore(); ref = B.R("lin"); g = FWML()
        od = OD.OutcomeSeriesDesk(gw); fw = FI("FW", "M1", "XAUUSD", "W1")
        gw.resolve_window(fw_req, fw, _entry(), I, I, 3, 10, _health()); od.register_h1(TypedH1(h1(REQUEST_ID=fw_req)), identity=fw)
        if issue_fw: od.request(fw_req, pkg(), ctx(), identity=fw)
        ml = FI("ML", "MM1", "XAUUSD", "W2")
        if ml_win: bd = gw.resolve_window(ml_req, ml, _entry(), I, I, 3, 10, _health())
        else: bd = gw.resolve("legacy-ml", _entry(), I, I, 3, 10, _health())
        desk = AugmentedDesk(gw, g, od); ret = FWReturnRecord("ret1", fw_req, "fw", ("EVIDENCE", "LINEAGE"), ref); aug = R.AugmentedInput(ref, ref, ref, ref, bd, ref, ref, ref); return gw, g, desk, ret, aug, ml
    def test_positive_return_recorded_then_rebind_verified_against_the_issued_binding_and_immutable_and_association_is_HELD(self):
        gw, g, desk, ret, aug, ml = self.rig(); self.assertIs(desk.record_fw_return(ret), ret); self.assertIs(desk.record_fw_return(ret), ret)
        r = desk.rebind(g["ml"], aug, Q, return_id="ret1"); self.assertEqual((r.verified, r.lane, r.return_id, r.association, r.consumer_binding_id, r.manifest_or_dataset_binding_id), (True, "BASELINE", "ret1", "HELD", None, None)); self.assertEqual(desk.rebind(g["ml"], aug, Q, return_id="ret1"), r); self.assertEqual(desk.result_for("ml"), r)
    def test_fw_return_requires_an_actually_issued_fw_result(self):
        gw, g, desk, ret, aug, ml = self.rig(issue_fw=False); self.assertEqual(code(desk.record_fw_return, ret), "FW_RETURN_NOT_AN_ISSUED_FW_RESULT")                    # the window exists and the CBID is registered, but no return was ever issued
        gw2, g2, d2, ret2, aug2, ml2 = self.rig(); self.assertEqual(code(d2.record_fw_return, dataclasses.replace(ret2, fw_request_id="never-issued")), "FW_RETURN_NOT_AN_ISSUED_FW_RESULT")
        self.assertEqual(code(AugmentedDesk(gw2, g2).record_fw_return, ret2), "FW_RESULT_SOURCE_HELD")                                                                     # no owning desk => the issued result cannot be established
        self.assertEqual(code(d2.rebind, g2["ml"], aug2, Q, return_id="ret1"), "FW_RETURN_UNKNOWN"); self.assertIsNone(d2.result_for("ml"))
    def test_return_record_negatives(self):
        gw, g, desk, ret, aug, ml = self.rig(); bad = lambda **k: dataclasses.replace(ret, **k)
        self.assertEqual(code(desk.record_fw_return, "x"), "FW_RETURN_RECORD_MALFORMED"); self.assertEqual(code(desk.record_fw_return, bad(classes=("EVIDENCE",))), "FW_RETURN_HAS_NO_LINEAGE")
        self.assertEqual(code(desk.record_fw_return, bad(classes=("LINEAGE", "SIGNAL"))), "FW_RETURN_CLASS_NOT_PERMITTED"); self.assertEqual(code(desk.record_fw_return, bad(classes=())), "FW_RETURN_EMPTY")
        self.assertEqual(code(desk.record_fw_return, bad(fw_manifest_id="ml")), "FW_RETURN_MANIFEST_NOT_AN_FW_MANIFEST"); self.assertEqual(code(desk.record_fw_return, bad(fw_manifest_id="zz")), "FW_RETURN_MANIFEST_NOT_AN_FW_MANIFEST")
        desk.record_fw_return(ret); self.assertEqual(code(desk.record_fw_return, bad(fw_manifest_id="fw", classes=("LINEAGE",))), "FW_RETURN_IMMUTABLE"); self.assertEqual(code(desk.record_fw_return, bad(return_id="ret2")), "FW_RETURN_LINEAGE_ALREADY_RETURNED_BY_ANOTHER")
    def test_rebind_negatives_write_nothing(self):
        gw, g, desk, ret, aug, ml = self.rig(); ref = B.R("lin")
        self.assertEqual(code(desk.rebind, g["ml"], None, Q, return_id="ret1"), "FW_DERIVED_INPUT_WITHOUT_LINEAGE_AND_REBIND"); self.assertEqual(code(desk.rebind, g["ml"], aug, Q, return_id="ret1"), "FW_RETURN_UNKNOWN")
        desk.record_fw_return(ret)
        g2 = {"fw": M("fw", "FW", (b"a",)), "fw2": M("fw2", "FW", (b"a",)), "ml": M("ml", "ML", (b"a",), derived_from="fw2")}; d2 = AugmentedDesk(gw, g2, desk._od); d2.record_fw_return(ret); self.assertEqual(code(d2.rebind, g2["ml"], aug, Q, return_id="ret1"), "AUGMENTED_RETURN_FOR_DIFFERENT_FW_MANIFEST")
        other = B.R("other"); a2 = R.AugmentedInput(other, ref, ref, ref, aug.gateway_rebind, ref, ref, ref); self.assertEqual(code(desk.rebind, g["ml"], a2, Q, return_id="ret1"), "AUGMENTED_LINEAGE_NOT_THE_RETURNED_ONE")
        forged = dataclasses.replace(aug.gateway_rebind, request_id="NOT-ISSUED"); a3 = R.AugmentedInput(ref, ref, ref, ref, forged, ref, ref, ref); self.assertEqual(code(desk.rebind, g["ml"], a3, Q, return_id="ret1"), "BINDING_NOT_FROM_GATEWAY")
        self.assertIsNone(desk.result_for("ml"))
        hidden = {"fw": M("fw", "FW", (Q,)), "ml": M("ml", "ML", (b"a",), derived_from="fw")}; d4 = AugmentedDesk(gw, hidden, desk._od); d4.record_fw_return(ret); self.assertEqual(code(d4.rebind, hidden["ml"], aug, Q, return_id="ret1"), "HIDDEN_QUANT_ANCESTOR")
    def test_the_fw_returns_own_binding_is_not_an_ml_rebind(self):
        gw, g, desk, ret, aug, ml = self.rig(fw_req="same-req", ml_req="same-req"); ref = B.R("lin"); desk.record_fw_return(ret)                                           # consumer-local request ids: FW and ML windows may share one id
        self.assertEqual(code(desk.rebind, g["ml"], aug, Q, return_id="ret1"), "AUGMENTED_REBIND_IS_THE_FW_BINDING"); self.assertIsNone(desk.result_for("ml"))
    def test_a_different_rebind_for_the_same_ml_manifest_is_refused(self):
        gw, g, desk, ret, aug, ml = self.rig(); desk.record_fw_return(ret); desk.rebind(g["ml"], aug, Q, return_id="ret1")
        ref = B.R("lin"); b2 = gw.resolve("second", B._entry(), I, I, 3, 10, B._health()); self.assertIsNot(b2, aug.gateway_rebind); a2 = R.AugmentedInput(ref, ref, ref, ref, b2, ref, ref, ref)
        self.assertEqual(code(desk.rebind, g["ml"], a2, Q, return_id="ret1"), "AUGMENTED_REBIND_IMMUTABLE")
        self.assertEqual(desk.result_for("ml").rebind_request_id, aug.gateway_rebind.request_id)
    # ---- association: HELD until an explicit reverse-H1 mapping matches the identity the final store actually issued --------------------------------------------------------------
    def test_association_bound_only_by_the_explicit_mapping_and_cbid_never_equals_the_manifest_binding_id(self):
        gw, g, desk, ret, aug, ml = self.rig(); desk.record_fw_return(ret); desk.rebind(g["ml"], aug, Q, return_id="ret1"); h = TypedH1(mlh1())
        r = desk.associate("ml", h, ml); self.assertEqual((r.association, r.consumer_binding_id, r.manifest_or_dataset_binding_id, r.verified), ("BOUND", "MB1", "MM1", True)); self.assertNotEqual(r.consumer_binding_id, r.manifest_or_dataset_binding_id)
        self.assertEqual(desk.associate("ml", h, ml), r); self.assertEqual(desk.result_for("ml"), r); self.assertEqual(desk.rebind(g["ml"], aug, Q, return_id="ret1"), r)                # replay never resets BOUND to HELD
        self.assertEqual(code(desk.associate, "ml", TypedH1(mlh1(CONSUMER_BINDING_ID="OTHER")), ml), "AUGMENTED_ASSOCIATION_IMMUTABLE")
    def test_association_negatives_leave_it_HELD(self):
        gw, g, desk, ret, aug, ml = self.rig(); desk.record_fw_return(ret); self.assertEqual(code(desk.associate, "ml", TypedH1(mlh1()), ml), "AUGMENTED_REBIND_UNKNOWN"); desk.rebind(g["ml"], aug, Q, return_id="ret1")
        nomb = mlh1(); del nomb["MANIFEST_OR_DATASET_BINDING_ID"]
        for h, i, c in ((mlh1(), ml, None), (h1(), ml, "H1_RECORD_NOT_TYPED"), (TypedH1(h1(REQUEST_ID="ml-rq")), ml, "ASSOCIATION_H1_NOT_AN_ML_RECORD"), (TypedH1(mlh1(req="other-rq")), ml, "ASSOCIATION_H1_REQUEST_NOT_THE_REBIND_REQUEST"),
                        (TypedH1(mlh1()), FI("ML", "MM1", "XAUUSD", "W-other"), "ASSOCIATION_IDENTITY_NOT_ISSUED_TO_ML_REQUEST"), (TypedH1(mlh1()), FI("FW", "MM1", "XAUUSD", "W2"), "ASSOCIATION_IDENTITY_NOT_ISSUED_TO_ML_REQUEST"),
                        (TypedH1(nomb), ml, "H1_MANIFEST_OR_DATASET_BINDING_ID_HELD"), (TypedH1(mlh1(mid="WRONG")), ml, "IDENTITY_BINDING_DIFFERS_FROM_BINDING")):
            if c is None: continue
            self.assertEqual(code(desk.associate, "ml", h, i), c); self.assertEqual(desk.result_for("ml").association, "HELD", c)
        self.assertEqual(code(AugmentedDesk(gw, g, desk._od).associate, "ml", TypedH1(mlh1()), ml), "AUGMENTED_REBIND_UNKNOWN")
    def test_a_rebind_that_was_never_issued_through_the_final_store_cannot_be_associated(self):
        gw, g, desk, ret, aug, ml = self.rig(ml_win=False); desk.record_fw_return(ret); r = desk.rebind(g["ml"], aug, Q, return_id="ret1"); self.assertEqual(r.association, "HELD")                      # legacy request-id binding: provenance only
        self.assertEqual(code(desk.associate, "ml", TypedH1(mlh1(req="legacy-ml")), ml), "ASSOCIATION_IDENTITY_NOT_ISSUED_TO_ML_REQUEST"); self.assertEqual(desk.result_for("ml").association, "HELD")
