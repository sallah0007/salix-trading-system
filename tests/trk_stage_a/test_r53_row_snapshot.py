"""R53 per-ROW consumption against the Core's resolved per-timeframe composition (Registry p101-102, p121-123), on the ACTUAL per-row route: FW `Composition.deliver(snapshot=)` and ML `MLConsumerPath.consume(snapshot=)` with an exact-row Gateway window.
The snapshot composition is journaled in a standalone SIM Core (the assembly Core has no timeframe registry); the instrument/timeframe LABEL ports are SUPPLIED; the watermark values are supplied-unadmitted. Clears no gate/hold."""
import dataclasses as dc
from stage_a.errors import Refusal
from stage_a.gateway import contracts as G
from stage_a.gateway.v038 import FinalResolutionIdentity as FI
from stage_a.tracker import row_snapshot as RS_
from . import test_r53_row_l2_maintenance as L2
from . import test_r53_ml_view_in_consumer_path as MV
from .test_r26_snapshot import SealedResolution as SR
from .test_r53_row_route_delivery import GTAB, I, R, NONE_, code

ORIG = "ORIGINAL_AS_OBSERVED"
def comp(vint_h4=ORIG, vint_h1=ORIG, wm=None, fence=100):
    h = SR.__new__(SR); c = SR.core(h); k = {n: SR.put(h, c, tf, n, av, v) for n, tf, av, v in (("P4", "H4", 5, vint_h4), ("P1", "H1", 8, vint_h1))}
    out = c.resolve_sealed_snapshot("XAUUSD", fence, fence, [k["P4"], k["P1"]], {"H4": [(k["P4"], True)], "H1": [(k["P1"], True)]}, wm or {"H4": 9, "H1": 100})
    return dict(core=c, resolved_manifest_hash=out["resolved_manifest_hash"], instrument_of=lambda b: "XAUUSD" if b == I else None, timeframe_of=lambda b: "H1" if b == I else None), out["state"]

class RowSnap(L2.RowL2):
    pass
for _n in [n for n in dir(L2.RowL2) if n.startswith("test_")]: setattr(RowSnap, _n, None)

def delivered(case, snapshot, n, step=0, now=14):
    fk, co, r0, b, e = case.o["B"]; e = dc.replace(e, expected_projection=case.chain["B"][0][0].published_projection_name); k = dict(binding=b, now=now, ref=R("hl-" + n), resolved_at=now - 1, tables=GTAB)
    return co.deliver("fw-" + n, FI("FW", "M-" + n, "XAUUSD", "W" + n), e, I, I, step, 60, case.res["B"], snapshot=snapshot, **k)
class FWRowSnapshot(RowSnap):
    def test_a_row_inside_the_single_vintage_per_timeframe_composition_is_received_and_each_contradiction_is_refused_by_the_FW_receiver(self):
        self.reg(); self.maint(13); good, st = comp(); self.assertEqual(st, "RESOLVED"); self.assertIsInstance(delivered(self, good, "g"), G.Binding)
        bad_vint, _ = comp(vint_h1="RESTATED"); self.assertEqual(self.refusal(bad_vint, "v"), ("NON_DELIVERY", "ROW_SNAPSHOT_RESOLVED_MANIFEST_ABSENT_HELD"))              # H4 original vs H1 restated: MIXED_VINTAGE composition => unresolved => refused
        same_other, _ = comp(vint_h4="RESTATED", vint_h1="RESTATED"); self.assertEqual(self.refusal(same_other, "o"), ("NON_DELIVERY", "ROW_SNAPSHOT_VINTAGE_DIFFERS_FROM_TIMEFRAME_RESOLUTION"))   # single vintage, but not the row's vintage
        low_wm, _ = comp(wm={"H4": 9, "H1": 5}); self.assertEqual(self.refusal(low_wm, "w"), ("NON_DELIVERY", "ROW_SNAPSHOT_AVAILABLE_ASOF_AFTER_TIMEFRAME_WATERMARK"))        # row visible only after the H1 watermark
        early_fence, _ = comp(fence=15); self.assertEqual(self.refusal(early_fence, "f"), ("NON_DELIVERY", "ROW_SNAPSHOT_AVAILABLE_ASOF_NOT_BEFORE_FENCE"))                 # row available_asof >= the half-open fence
        wrong_tf = dict(good, timeframe_of=lambda b: "M15"); self.assertEqual(self.refusal(wrong_tf, "t"), ("NON_DELIVERY", "ROW_SNAPSHOT_TIMEFRAME_NOT_IN_COMPOSITION"))
        wrong_ins = dict(good, instrument_of=lambda b: "EURUSD"); self.assertEqual(self.refusal(wrong_ins, "i"), ("NON_DELIVERY", "ROW_SNAPSHOT_INSTRUMENT_NOT_IN_COMPOSITION"))
        for p in ({k: v for k, v in good.items() if k != "timeframe_of"}, dict(good, instrument_of=lambda b: None)): self.assertEqual(self.refusal(p, "h"), ("NON_DELIVERY", RS_.HELD_PORT))              # unbound/unmapped labels: HELD, never guessed
        self.assertEqual(self.refusal({"core": good["core"]}, "x"), ("NON_DELIVERY", "ROW_SNAPSHOT_RESOLVED_MANIFEST_ABSENT_HELD")); self.assertEqual(self.refusal("junk", "y"), ("NON_DELIVERY", "ROW_SNAPSHOT_INPUT_INVALID"))
        self.assertIsInstance(delivered(self, good, "g2", 1), G.Binding)                                                                                   # control: the positive still delivers after the refusals
    def refusal(self, snap, n):
        try: delivered(self, snap, n); return None
        except Refusal as e: return (e.code, str(e.args[0]).split(" ", 1)[-1] if False else getattr(e, "message", None) or str(e).split(" ")[-1])
    def test_BASE_B_delivers_with_the_snapshot_while_the_affected_A_with_unknown_ancestry_is_still_denied_by_the_Core(self):
        self.reg(); self.maint(13); good, _ = comp(); self.assertIsInstance(delivered(self, good, "b"), G.Binding)
        fk, co, r0, b, e = self.o["A"]; e = dc.replace(e, expected_projection=self.chain["A"][0][0].published_projection_name)
        self.assertEqual(code(co.deliver, "fw-a", FI("FW", "M-a", "XAUUSD", "Wa"), e, I, I, 0, 60, self.res["A"], binding=b, now=14, ref=R("hl-a"), resolved_at=13, tables=GTAB, snapshot=good), "NON_DELIVERY")

class MLRowSnapshot(MV.ViewInPath):
    test_r53_separated_child_acceptance_then_BOTH_FW_and_ML_deny_the_unknown_ancestry_feature_and_the_unrelated_BASE_delivers_to_both_before_between_after = None
    test_the_view_duties_gate_the_actual_consumption_and_an_unbound_or_failing_duty_blocks_it = None
    test_a_consumed_feature_the_view_does_not_declare_or_cannot_be_mapped_blocks = None
    test_the_consumed_ROW_must_be_one_of_the_views_declared_rows_a_same_feature_other_MV_row_and_a_legacy_row_are_not = None
    def test_the_exact_row_is_consumed_with_a_matching_snapshot_and_each_contradiction_blocks_while_no_snapshot_is_unchanged(self):
        go, fv, m, st, res = self.build(); good, _ = comp(); base = go(feature_view=fv); self.assertEqual(base.blockers, ())
        self.assertEqual(go(feature_view=fv, snapshot=good).blockers, ())                                                                                    # exact row + matching composition
        self.assertEqual(go(feature_view=fv, snapshot=comp(wm={"H4": 9, "H1": 5})[0]).blockers, ("ROW_SNAPSHOT_AVAILABLE_ASOF_AFTER_TIMEFRAME_WATERMARK",))
        self.assertEqual(go(feature_view=fv, snapshot=comp(fence=15)[0]).blockers, ("ROW_SNAPSHOT_AVAILABLE_ASOF_NOT_BEFORE_FENCE",))
        self.assertEqual(go(feature_view=fv, snapshot=comp(vint_h4="RESTATED", vint_h1="RESTATED")[0]).blockers, ("ROW_SNAPSHOT_VINTAGE_DIFFERS_FROM_TIMEFRAME_RESOLUTION",))
        self.assertEqual(go(feature_view=fv, snapshot=comp(vint_h1="RESTATED")[0]).blockers, ("ROW_SNAPSHOT_RESOLVED_MANIFEST_ABSENT_HELD",))
        self.assertEqual(go(feature_view=fv, snapshot={k: v for k, v in good.items() if k != "instrument_of"}).blockers, (RS_.HELD_PORT,))
