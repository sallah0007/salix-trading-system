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
        g = _gw(); g.final_store = FinalResolutionStore(); e = _entry(); w = FI("FW", "B1", "XAUUSD", "W1"); b = g.resolve_window("rq1", w, e, I, I, 3, 10, _health()); return g, w, b
    def test_request_return_is_correlated_to_the_issued_fw_window_and_the_return_is_immutable_and_never_a_delivery(self):
        g, w, b = self.rig(); d = OD.OutcomeSeriesDesk(g); r = d.request("rq1", pkg(), ctx(), identity=w)
        self.assertEqual((r.decision.status, r.delivered, r.held_fields, r.consumer_binding_id), (H.PASS_STRUCTURAL, False, OD.HELD_FIELDS, "B1")); self.assertIs(d.request("rq1", pkg(), ctx(authorized_segments=((0, 1),)), identity=w), r)       # stored return, never re-evaluated by a later context
        self.assertEqual(code(d.request, "rq1", pkg(series_id="OTHER"), ctx(), identity=w), "OUTCOME_REQUEST_IMMUTABLE"); self.assertIs(d.return_for("rq1"), r); self.assertIsNone(d.return_for("nope"))
        self.assertEqual(code(d.request, "rq1", pkg(consumer_binding_id="B2"), ctx(), identity=w), "OUTCOME_REQUEST_BINDING_ID_DIFFERS_FROM_ISSUED_IDENTITY")
        self.assertEqual(code(d.request, "rq9", pkg(), ctx(), identity=w), "OUTCOME_REQUEST_NOT_ISSUED_TO_FW_WINDOW"); self.assertEqual(code(d.request, "rq1", pkg(), ctx(), identity=FI("FW", "B1", "XAUUSD", "OTHER")), "OUTCOME_REQUEST_NOT_ISSUED_TO_FW_WINDOW")
        self.assertEqual(code(d.request, "rq1", "x", ctx(), identity=w), "OUTCOME_REQUEST_MALFORMED"); self.assertEqual(code(OD.OutcomeSeriesDesk(_gw()).request, "rq1", pkg(), ctx(), identity=w), "OUTCOME_REQUEST_NO_WINDOW_STORE")
    def test_withheld_and_unknown_decisions_are_returned_as_such_and_a_ml_or_non_binding_window_cannot_request(self):
        g, w, b = self.rig(); d = OD.OutcomeSeriesDesk(g); self.assertEqual(d.request("rq1", pkg(dependency_interval_end=40), ctx(), identity=w).decision.status, H.WITHHELD)
        g2 = _gw(); g2.final_store = FinalResolutionStore(); w2 = FI("ML", "B1", "XAUUSD", "W1"); g2.resolve_window("rq1", w2, _entry(), I, I, 3, 10, _health()); self.assertEqual(code(OD.OutcomeSeriesDesk(g2).request, "rq1", pkg(), ctx(), identity=w2), "OUTCOME_REQUEST_NOT_ISSUED_TO_FW_WINDOW")
        g3 = _gw(); g3.final_store = FinalResolutionStore(); g3.set_watermark(1); w3 = FI("FW", "B1", "XAUUSD", "W1"); nd = g3.resolve_window("rq1", w3, _entry(), I, I, 3, 10, _health()); self.assertEqual(type(nd).__name__, "NonDeliveryResolution")
        self.assertEqual(code(OD.OutcomeSeriesDesk(g3).request, "rq1", pkg(), ctx(), identity=w3), "OUTCOME_REQUEST_WINDOW_OUTCOME_NOT_A_BINDING")
if __name__ == "__main__": unittest.main()
