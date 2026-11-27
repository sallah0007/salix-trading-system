"""R26 per-timeframe vintage/watermark carriage and seal -> cross-timeframe selection (registry instance supplied by the TEST; none shipped)."""
import unittest
from stage_a.core import time_family as TF
from stage_a.storage.object_store import InMemoryObjectStore
from stage_a.storage.authority_class import SimulationStore
from stage_a.coordination.object_store_journal import ObjectStoreJournal
from stage_a.core.tracker_core import TrackerCore
from .test_r24_core import code
REG = lambda: TF.TimeframeRegistry([("H4", "H1"), ("H1", "M15"), ("M15", None)])
SV = TF.StreamView
def good(): return {"H4": SV((("P4a", 5, True), ("P4b", 3, True)), "v-h4", 9), "H1": SV((("P1", 8, True),), "v-h1", 10)}
class Snapshot(unittest.TestCase):
    def test_unique_positive_keeps_per_timeframe_vintage_and_watermark(self):
        r = TF.resolve_snapshot(REG(), 10, good()); self.assertEqual(r.state, TF.RESOLVED)
        a, b = r.entry("H4"), r.entry("H1"); self.assertEqual((a.selection.parent_id, a.vintage, a.watermark), ("P4a", "v-h4", 9)); self.assertEqual((b.selection.parent_id, b.vintage, b.watermark), ("P1", "v-h1", 10))
    def test_half_open_no_back_projection_and_equal_availability_excluded(self):
        r = TF.resolve_snapshot(REG(), 8, good()); self.assertEqual(r.state, TF.UNRESOLVED); self.assertEqual(r.entry("H1").reasons, ("NO_SEALED_PARENT_VISIBLE",))       # H1 parent available at 8 is not visible at query 8
        self.assertEqual(r.entry("H4").selection.parent_id, "P4a")
    def test_ambiguity_missing_vintage_bad_watermark_and_incomplete_leave_unresolved_in_any_order(self):
        for st in ({"H4": SV((("A", 5, True), ("B", 5, True)), "v", 1)}, {"H4": SV((("A", 5, False),), "v", 1)}, {"H4": SV((("A", 5, True),), "", 1)}, {"H4": SV((("A", 5, True),), "v", -1)},
                   {"H4": SV((("A", 5, True),), "v", True)}, {"H4": SV((("A", 5, True),), None, None)}):
            self.assertEqual(TF.resolve_snapshot(REG(), 10, st).state, TF.UNRESOLVED, st)
        rev = {k: SV(tuple(reversed(v.parents)), v.vintage, v.watermark) for k, v in {"H4": SV((("A", 5, True), ("B", 5, True)), "v", 1)}.items()}
        self.assertEqual(TF.resolve_snapshot(REG(), 10, rev).entry("H4").selection.candidates, ("A", "B"))
    def test_one_unresolved_timeframe_makes_the_whole_snapshot_unresolved_no_false_simultaneity(self):
        s = good(); s["M15"] = SV((), "v-m15", 10); r = TF.resolve_snapshot(REG(), 10, s); self.assertEqual((r.state, r.entry("H4").state, r.entry("M15").state), (TF.UNRESOLVED, TF.RESOLVED, TF.UNRESOLVED))
    def test_refusals(self):
        self.assertEqual(code(TF.resolve_snapshot, REG(), 10, {"D1": SV((), "v", 1)}), "UNKNOWN_TIMEFRAME")
        self.assertEqual(code(TF.resolve_snapshot, REG(), 10, {"H4": ("A", 5, True)}), "SNAPSHOT_STREAM_NOT_PER_TIMEFRAME")          # a shared scalar/untyped stream is not per-timeframe carriage
        self.assertEqual(code(TF.resolve_snapshot, REG(), -1, good()), "ASOF_MALFORMED"); self.assertEqual(code(TF.resolve_snapshot, REG(), 10, {}), "SNAPSHOT_STREAMS_INVALID")
        self.assertEqual(code(TF.resolve_snapshot, TF.TimeframeRegistry(), 10, good()), "UNKNOWN_TIMEFRAME")
    def test_core_callpath_journals_result_and_refuses_without_registry(self):
        j = ObjectStoreJournal(SimulationStore(InMemoryObjectStore()), "sn", "w"); j.acquire_epoch()
        self.assertEqual(code(TrackerCore(j, simulation=True).resolve_snapshot, 10, good()), "TIMEFRAME_REGISTRY_UNBOUND")
        c = TrackerCore(j, simulation=True, timeframes=REG()); r = c.resolve_snapshot(10, good()); self.assertEqual(r.state, TF.RESOLVED)
        rec = [x for x in j.read_from(0) if x.kind == "SNAPSHOT_RESOLVED"]; self.assertEqual(len(rec), 1)
if __name__ == "__main__": unittest.main()
