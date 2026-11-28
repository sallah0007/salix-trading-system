"""R44: the snapshot manifest is DERIVED from the Core's owning resolved composition; the per-timeframe watermark is a source-owned slot (unbound => HELD); held fields are explicit; negatives refuse."""
import unittest
from stage_a.errors import Refusal
from stage_a.tracker import snapshot_carrier as SC
from .test_r26_snapshot import SealedResolution as SR
HI = {k: k + "-v" for k in SC.HELD_INPUTS}
def code(f, *a, **k):
    try: f(*a, **k)
    except Refusal as e: return e.code
def setup(vint="ORIGINAL_AS_OBSERVED"):
    h = SR.__new__(SR); c = SR.core(h); k = {n: SR.put(h, c, tf, n, av, vint) for n, tf, av in (("P4", "H4", 5), ("P1", "H1", 8))}; return c, k
def args(k, **o):
    a = dict(instrument="XAUUSD", query_asof=10, fence=10, member_keys=[k["P4"], k["P1"]], parents_by_tf={"H4": [(k["P4"], True)], "H1": [(k["P1"], True)]}, watermark_source={"H4": 9, "H1": 10}.get, timeframe="H1", held_inputs=HI); a.update(o); return a
class Carrier(unittest.TestCase):
    def test_manifest_is_derived_from_core_records_and_binds_candidate_only(self):
        c, k = setup(); r = SC.resolve_and_bind(c, **args(k)); self.assertEqual(r["state"], "RESOLVED"); m = r["manifest"]
        self.assertEqual((m.instrument_id, m.query_asof, m.snapshot_fence_ts, m.canonical_bar_or_event_identity, m.timeframe_watermarks), ("XAUUSD", 10, 10, k["P1"], (("H1", 10), ("H4", 9))))
        self.assertEqual(m.data_vintage_mode, "ORIGINAL_AS_OBSERVED"); self.assertFalse(r["bound"].authoritative); self.assertNotIn("source_provider_identity", r["bound"].unbound_fields)
    def test_unbound_or_bad_watermark_source_and_incomplete_held_inputs_refuse(self):
        c, k = setup()
        self.assertEqual(code(SC.resolve_and_bind, c, **args(k, watermark_source=None)), SC.WATERMARK_HELD)
        self.assertEqual(code(SC.resolve_and_bind, c, **args(k, watermark_source=lambda tf: None)), "SNAPSHOT_WATERMARK_SOURCE_RETURNED_NON_WATERMARK")
        self.assertEqual(code(SC.resolve_and_bind, c, **args(k, watermark_source=lambda tf: -1)), "SNAPSHOT_WATERMARK_SOURCE_RETURNED_NON_WATERMARK")
        for drop in SC.HELD_INPUTS: self.assertEqual(code(SC.resolve_and_bind, c, **args(k, held_inputs={x: v for x, v in HI.items() if x != drop})), "SNAPSHOT_CARRIER_HELD_INPUTS_INCOMPLETE")
        self.assertEqual(code(SC.resolve_and_bind, c, **args(k, held_inputs=dict(HI, utc_identity=""))), "SNAPSHOT_CARRIER_HELD_INPUTS_INCOMPLETE")
    def test_an_unresolved_composition_yields_no_manifest_and_unknown_timeframe_refuses(self):
        c, k = setup(); r = SC.resolve_and_bind(c, **args(k, parents_by_tf={"H4": [(k["P4"], False)], "H1": [(k["P1"], True)]})); self.assertEqual(r["state"], "UNRESOLVED"); self.assertIsNone(r["manifest"])
        self.assertEqual(code(SC.resolve_and_bind, c, **args(k, timeframe="D1")), "SNAPSHOT_FIELD_DISAGREES_WITH_OWNING_OBSERVATIONS")
    def test_a_member_after_the_half_open_fence_cannot_be_a_parent(self):
        c, k = setup(); self.assertEqual(code(SC.resolve_and_bind, c, **args(k, fence=8, query_asof=8, member_keys=[k["P4"]], parents_by_tf={"H4": [(k["P4"], True)], "H1": [(k["P1"], True)]})), "PARENT_NOT_IN_SEALED_SNAPSHOT")
if __name__ == "__main__": unittest.main()
