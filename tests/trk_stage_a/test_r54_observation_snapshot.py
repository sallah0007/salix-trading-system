"""R54: observation -> snapshot adapter over the Core's own receipts, exercised against the reference sealed-resolution Core (timeframe registry bound) and refused on the assembly Core (registry unbound)."""
import unittest
from stage_a.errors import Refusal
from stage_a.tracker import snapshot_carrier as SC
from stage_a.tracker.observation_snapshot import ObservationSnapshotAdapter as A, PORT_HELD
from .test_r44_snapshot_carrier import setup, args, HI, code
from .test_r25_scheduler import core
from .test_r24_core import adm
class Adapter(unittest.TestCase):
    def test_equals_the_manual_carrier_call_and_derives_members_and_parents_from_the_cores_own_receipts(self):
        c, k = setup(); a = A(c, parent_complete=lambda key, f: True, watermark_source={"H4": 9, "H1": 10}.get); r = a.resolve(instrument="XAUUSD", query_asof=10, fence=10, timeframe="H1", held_inputs=HI)
        m = SC.resolve_and_bind(c, **args(k)); self.assertEqual((r["state"], r["resolved_manifest_hash"]), ("RESOLVED", m["resolved_manifest_hash"])); self.assertEqual(r["manifest"], m["manifest"]); self.assertFalse(r["bound"].authoritative)
    def test_unbound_ports_refuse_and_nothing_is_defaulted(self):
        c, k = setup(); self.assertEqual(code(A(c, watermark_source={"H4": 9, "H1": 10}.get).resolve, instrument="XAUUSD", query_asof=10, fence=10, timeframe="H1", held_inputs=HI), PORT_HELD)
        self.assertEqual(code(A(c, parent_complete=lambda *a: True).resolve, instrument="XAUUSD", query_asof=10, fence=10, timeframe="H1", held_inputs=HI), SC.WATERMARK_HELD)
        self.assertEqual(code(A(c, parent_complete=lambda *a: 1, watermark_source={"H4": 9, "H1": 10}.get).resolve, instrument="XAUUSD", query_asof=10, fence=10, timeframe="H1", held_inputs=HI), "OBSERVATION_SNAPSHOT_COMPLETENESS_NOT_BOOLEAN")
        self.assertEqual(code(A(c, parent_complete=lambda *a: True, watermark_source={"H4": 9, "H1": 10}.get).resolve, instrument="XAUUSD", query_asof=10, fence=10, timeframe="H1", held_inputs={}), "SNAPSHOT_CARRIER_HELD_INPUTS_INCOMPLETE")
        self.assertEqual(code(A, None), "OBSERVATION_SNAPSHOT_CORE_MISSING"); self.assertEqual(code(A, c, parent_complete=5), "OBSERVATION_SNAPSHOT_PORT_INVALID")
    def test_zero_rows_foreign_instrument_incomplete_parents_late_observations_and_assembly_core(self):
        c, k = setup(); ok = dict(watermark_source={"H4": 9, "H1": 10}.get)
        z = A(c, parent_complete=lambda *a: True, **ok).resolve(instrument="EURUSD", query_asof=10, fence=10, timeframe="H1", held_inputs=HI); self.assertEqual((z["state"], z["manifest"]), ("HELD_NO_RECORDED_OBSERVATIONS", None))
        inc = A(c, parent_complete=lambda key, f: False, **ok).resolve(instrument="XAUUSD", query_asof=10, fence=10, timeframe="H1", held_inputs=HI); self.assertNotEqual(inc["state"], "RESOLVED"); self.assertIsNone(inc["manifest"])    # incomplete parents: never a partial manifest
        late = A(c, parent_complete=lambda *a: True, watermark_source={"H4": 5, "H1": 5}.get).resolve(instrument="XAUUSD", query_asof=6, fence=6, timeframe="H4", held_inputs=HI); self.assertEqual(late["state"], "RESOLVED"); self.assertEqual(late["manifest"].canonical_bar_or_event_identity, k["P4"])        # P1 (available 8) is after the fence and cannot be a parent
        ac = core(); adm(ac, bar_identity="x"); self.assertEqual(code(A(ac, parent_complete=lambda *a: True, **ok).resolve, instrument="XAUUSD", query_asof=10, fence=10, timeframe="H4", held_inputs=HI), "TIMEFRAME_REGISTRY_UNBOUND")
    def test_an_ambiguous_observation_is_not_an_available_receipt(self):
        from .test_r24_core import facts
        c, k = setup(); self.assertIn(k["P1"], [r[0] for r in c.observations_for("XAUUSD")]); c.admit_observation(facts(timeframe="H1", bar_identity="P1"), b"DIFFERENT", 8, "ORIGINAL_AS_OBSERVED")          # same key, different payload: genuine ambiguity
        self.assertNotIn(k["P1"], [r[0] for r in c.observations_for("XAUUSD")]); self.assertIn(k["P4"], [r[0] for r in c.observations_for("XAUUSD")])
if __name__ == "__main__": unittest.main()
