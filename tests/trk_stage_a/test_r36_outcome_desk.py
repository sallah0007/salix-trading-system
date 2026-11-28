import dataclasses, unittest
from stage_a.errors import Refusal
from stage_a.fw import outcome_desk as OD
from stage_a.gateway import outcome_series as H
from stage_a.gateway.v038 import FinalResolutionStore, FinalResolutionIdentity as FI
from .test_boundaries import _gw, _entry, _health, I
from .test_r28_h3 import pkg, ctx
def code(f, *a, **k):
    try: f(*a, **k)
    except Refusal as e: return e.code
class Desk(unittest.TestCase):
    def rig(self):
        g = _gw(); g.final_store = FinalResolutionStore(); e = _entry(); w = FI("FW", "M1", "XAUUSD", "W1"); b = g.resolve_window("rq1", w, e, I, I, 3, 10, _health()); return g, w, b      # R37: manifest binding id M1 is DISTINCT from the package CBID B1
    def desk(self, g, w, rid="rq1", cbid="B1"):
        d = OD.OutcomeSeriesDesk(g); d.register_consumer_binding(OD.ConsumerBindingRecord(cbid, "FW", rid, w.manifest_or_dataset_binding_id), identity=w); return d
    def test_request_return_is_correlated_to_the_issued_fw_window_and_the_return_is_immutable_and_never_a_delivery(self):
        g, w, b = self.rig(); d = self.desk(g, w); r = d.request("rq1", pkg(), ctx(), identity=w)
        self.assertEqual((r.decision.status, r.delivered, r.held_fields, r.consumer_binding_id), (H.PASS_STRUCTURAL, False, OD.HELD_FIELDS, "B1")); self.assertIs(d.request("rq1", pkg(), ctx(authorized_segments=((0, 1),)), identity=w), r)       # stored return, never re-evaluated by a later context
        self.assertEqual(code(d.request, "rq1", pkg(series_id="OTHER"), ctx(), identity=w), "OUTCOME_REQUEST_IMMUTABLE"); self.assertIs(d.return_for("rq1"), r); self.assertIsNone(d.return_for("nope"))
        self.assertEqual(code(d.request, "rq1", pkg(consumer_binding_id="B2"), ctx(), identity=w), "OUTCOME_REQUEST_CONSUMER_BINDING_NOT_CORRELATED")
        self.assertEqual(code(d.request, "rq9", pkg(), ctx(), identity=w), "OUTCOME_REQUEST_NOT_ISSUED_TO_FW_WINDOW"); self.assertEqual(code(d.request, "rq1", pkg(), ctx(), identity=FI("FW", "B1", "XAUUSD", "OTHER")), "OUTCOME_REQUEST_NOT_ISSUED_TO_FW_WINDOW")
        self.assertEqual(code(d.request, "rq1", "x", ctx(), identity=w), "OUTCOME_REQUEST_MALFORMED"); self.assertEqual(code(OD.OutcomeSeriesDesk(_gw()).request, "rq1", pkg(), ctx(), identity=w), "OUTCOME_REQUEST_NO_WINDOW_STORE")
    def test_withheld_and_unknown_decisions_are_returned_as_such_and_a_ml_or_non_binding_window_cannot_request(self):
        g, w, b = self.rig(); d = self.desk(g, w); self.assertEqual(d.request("rq1", pkg(dependency_interval_end=40), ctx(), identity=w).decision.status, H.WITHHELD)
        g2 = _gw(); g2.final_store = FinalResolutionStore(); w2 = FI("ML", "M1", "XAUUSD", "W1"); g2.resolve_window("rq1", w2, _entry(), I, I, 3, 10, _health()); self.assertEqual(code(OD.OutcomeSeriesDesk(g2).request, "rq1", pkg(), ctx(), identity=w2), "OUTCOME_REQUEST_NOT_ISSUED_TO_FW_WINDOW")
        g3 = _gw(); g3.final_store = FinalResolutionStore(); g3.set_watermark(1); w3 = FI("FW", "M1", "XAUUSD", "W1"); nd = g3.resolve_window("rq1", w3, _entry(), I, I, 3, 10, _health()); self.assertEqual(type(nd).__name__, "NonDeliveryResolution")
        self.assertEqual(code(self.desk(g3, w3).request, "rq1", pkg(), ctx(), identity=w3), "OUTCOME_REQUEST_WINDOW_OUTCOME_NOT_A_BINDING")
    def test_r37_cbid_and_manifest_binding_id_are_distinct_fields_correlated_only_through_a_registered_record(self):
        g, w, b = self.rig(); d = OD.OutcomeSeriesDesk(g); self.assertNotEqual(w.manifest_or_dataset_binding_id, "B1")
        self.assertEqual(code(d.request, "rq1", pkg(), ctx(), identity=w), "OUTCOME_REQUEST_CONSUMER_BINDING_NOT_CORRELATED")                                              # no H1 CBID relation: HELD, nothing derived from M1
        self.assertEqual(code(d.request, "rq1", pkg(consumer_binding_id="M1"), ctx(), identity=w), "OUTCOME_REQUEST_CONSUMER_BINDING_NOT_CORRELATED")                      # the manifest binding id is NOT accepted as the CBID
        rec = OD.ConsumerBindingRecord("B1", "FW", "rq1", "M1"); self.assertIs(d.register_consumer_binding(rec, identity=w), rec); self.assertIs(d.register_consumer_binding(rec, identity=w), rec)   # idempotent
        r = d.request("rq1", pkg(), ctx(), identity=w); self.assertEqual((r.consumer_binding_id, r.decision.status, r.delivered), ("B1", H.PASS_STRUCTURAL, False))      # positive: CBID C1/B1 vs manifest binding M1 distinct
        for bad, c in ((OD.ConsumerBindingRecord("B1", "FW", "rq1", "OTHER"), "CONSUMER_BINDING_NOT_THE_ISSUED_WINDOW_IDENTITY"), (OD.ConsumerBindingRecord("B2", "FW", "rq9", "M1"), "CONSUMER_BINDING_NOT_THE_ISSUED_WINDOW_IDENTITY"), (OD.ConsumerBindingRecord("B2", "ML", "rq1", "M1"), "CONSUMER_BINDING_NOT_THE_ISSUED_WINDOW_IDENTITY"), (OD.ConsumerBindingRecord("B2", "FW", "rq1", "M1"), "CONSUMER_BINDING_REQUEST_ALREADY_CORRELATED"), ("x", "CONSUMER_BINDING_RECORD_MALFORMED")):
            self.assertEqual(code(d.register_consumer_binding, bad, identity=w), c, bad)
        g2, w2, _ = self.rig(); d2 = OD.OutcomeSeriesDesk(g2); d2.register_consumer_binding(OD.ConsumerBindingRecord("FOREIGN", "FW", "rq1", "M1"), identity=w2)
        self.assertEqual(code(d2.request, "rq1", pkg(), ctx(), identity=w2), "OUTCOME_REQUEST_CONSUMER_BINDING_NOT_CORRELATED")                                              # a foreign CBID in the package is not the registered one
        d.request("rq1", pkg(), ctx(), identity=w); self.assertEqual(d.return_for("rq1"), r)                                                                                 # retry returns the stored return
if __name__ == "__main__": unittest.main()
