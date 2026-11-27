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

class SealedResolution(unittest.TestCase):
    """R31: seal -> per-timeframe selection ONLY among sealed members -> vintage read from the sealed records -> resolve. Candidate mechanics; watermarks are supplied."""
    def core(self):
        st = SimulationStore(InMemoryObjectStore()); j = ObjectStoreJournal(st, "r31", "w"); j.acquire_epoch(); return TrackerCore(j, simulation=True, timeframes=REG())
    def put(self, c, tf, bar, av, v):
        from .test_r24_core import facts
        f = facts(timeframe=tf, bar_identity=bar); c.admit_observation(f, ("p-" + bar).encode(), av, v); return c.obs_key(f)
    def rig(self):
        c = self.core(); k = {n: self.put(c, tf, n, av, v) for n, tf, av, v in (("P4", "H4", 5, "v1"), ("P1", "H1", 8, "v1"), ("P1late", "H1", 12, "v1"))}; return c, k
    def test_positive_selects_from_sealed_records_with_per_tf_vintage_and_journals_the_sealed_hash(self):
        c, k = self.rig(); out = c.resolve_sealed_snapshot("XAUUSD", 10, 10, [k["P4"], k["P1"]], {"H4": [(k["P4"], True)], "H1": [(k["P1"], True)]}, {"H4": 9, "H1": 10})
        r = out["resolution"]; self.assertEqual((out["state"], r.entry("H4").selection.parent_id, r.entry("H4").vintage, r.entry("H1").vintage, r.entry("H1").watermark), (TF.RESOLVED, k["P4"], "v1", "v1", 10))
        self.assertTrue(c.verify_snapshot(out["base_seal_hash"], "XAUUSD", 10, 10, [k["P4"], k["P1"]])); self.assertEqual(out, c.resolve_sealed_snapshot("XAUUSD", 10, 10, [k["P4"], k["P1"]], {"H4": [(k["P4"], True)], "H1": [(k["P1"], True)]}, {"H4": 9, "H1": 10}))
        rec = [x for x in c._j.read_from(1) if x.kind == "SNAPSHOT_RESOLVED"]; self.assertEqual(rec[-1].body()["base_seal_hash"], out["base_seal_hash"])
    def test_fence_excluded_unknown_wrong_timeframe_and_caller_availability_cannot_select(self):
        c, k = self.rig(); mem = [k["P4"], k["P1"], k["P1late"]]
        self.assertEqual(code(c.resolve_sealed_snapshot, "XAUUSD", 10, 10, mem, {"H1": [(k["P1late"], True)]}, {"H1": 10}), "PARENT_NOT_IN_SEALED_SNAPSHOT")         # available 12 >= fence 10: excluded by the half-open fence
        self.assertEqual(code(c.resolve_sealed_snapshot, "XAUUSD", 10, 10, mem, {"H1": [("ghost", True)]}, {"H1": 10}), "PARENT_NOT_IN_SEALED_SNAPSHOT")
        self.assertEqual(code(c.resolve_sealed_snapshot, "XAUUSD", 10, 10, mem, {"H1": [(k["P4"], True)]}, {"H1": 10}), "PARENT_TIMEFRAME_MISMATCH")
        o = c.resolve_sealed_snapshot("XAUUSD", 8, 10, mem, {"H1": [(k["P1"], True)]}, {"H1": 10}); self.assertEqual((o["state"], o["resolution"].entry("H1").reasons), (TF.UNRESOLVED, ("NO_SEALED_PARENT_VISIBLE",)))     # availability 8 not < query 8: the SEALED record decides, not the caller
    def test_missing_watermark_incomplete_parent_and_held_seal_are_unresolved_never_partial(self):
        c, k = self.rig()
        o = c.resolve_sealed_snapshot("XAUUSD", 10, 10, [k["P4"], k["P1"]], {"H4": [(k["P4"], True)], "H1": [(k["P1"], True)]}, {"H4": 9}); self.assertEqual((o["state"], o["resolution"].entry("H1").reasons), (TF.UNRESOLVED, ("WATERMARK_NOT_RESOLVED",)))
        self.assertEqual(c.resolve_sealed_snapshot("XAUUSD", 10, 10, [k["P4"]], {"H4": [(k["P4"], False)]}, {"H4": 9})["state"], TF.UNRESOLVED)
        c2 = self.core(); a = self.put(c2, "H4", "A", 5, "v1"); b = self.put(c2, "H4", "B", 6, "v2"); h = c2.resolve_sealed_snapshot("XAUUSD", 10, 10, [a, b], {"H4": [(a, True)]}, {"H4": 9})
        self.assertEqual((h["state"], h["resolution"], h["reason"]), ("UNRESOLVED_HELD", None, "MIXED_VINTAGE_REFUSED"))                                       # mixed vintage without a policy: no selection at all
        self.assertEqual(code(TrackerCore(c._j, simulation=True).resolve_sealed_snapshot, "XAUUSD", 10, 10, [], {"H4": []}, {}), "TIMEFRAME_REGISTRY_UNBOUND")

    def test_r32_resolved_manifest_identity_changes_with_every_material_resolved_field_and_base_seal_stays_explicit(self):
        c, k = self.rig(); mem = [k["P4"], k["P1"]]
        def run(core=c, wm=None, comp=True, par=None, asof=10, fence=10, members=mem):
            return core.resolve_sealed_snapshot("XAUUSD", asof, fence, members, par or {"H4": [(k["P4"], comp)], "H1": [(k["P1"], True)]}, wm or {"H4": 9, "H1": 10})
        base = run(); self.assertEqual(base["state"], TF.RESOLVED); self.assertNotEqual(base["base_seal_hash"], base["resolved_manifest_hash"])
        self.assertEqual(run()["resolved_manifest_hash"], base["resolved_manifest_hash"]); self.assertEqual(run()["base_seal_hash"], base["base_seal_hash"])      # frozen inputs replay stably
        w6 = run(wm={"H4": 6, "H1": 10}); w7 = run(wm={"H4": 7, "H1": 10})
        self.assertEqual({w6["base_seal_hash"], w7["base_seal_hash"]}, {base["base_seal_hash"]})                                                            # the reproduced finding: same base seal ...
        self.assertEqual(len({base["resolved_manifest_hash"], w6["resolved_manifest_hash"], w7["resolved_manifest_hash"]}), 3)                               # ... but each watermark is its own resolved identity
        self.assertNotEqual(run(wm={"H4": 9, "H1": 11})["resolved_manifest_hash"], base["resolved_manifest_hash"])
        self.assertNotEqual(run(asof=9)["resolved_manifest_hash"], base["resolved_manifest_hash"])                                                          # query as-of (selection changes)
        self.assertNotEqual(run(comp=False)["resolved_manifest_hash"], base["resolved_manifest_hash"])                                                     # supplied completeness is part of the basis
        self.assertNotEqual(run(par={"H4": [(k["P4"], True)]}, wm={"H4": 9})["resolved_manifest_hash"], base["resolved_manifest_hash"])                    # different timeframe set
        st = SimulationStore(InMemoryObjectStore()); j = ObjectStoreJournal(st, "r32b", "w"); j.acquire_epoch(); c2 = TrackerCore(j, simulation=True, timeframes=TF.TimeframeRegistry([("H4", "H1"), ("H1", None)]))
        for n, tf, av in (("P4", "H4", 5), ("P1", "H1", 8)):
            from .test_r24_core import facts
            f = facts(timeframe=tf, bar_identity=n); c2.admit_observation(f, ("p-" + n).encode(), av, "v1")
        from .test_r24_core import facts as _f
        k2 = {"P4": c2.obs_key(_f(timeframe="H4", bar_identity="P4")), "P1": c2.obs_key(_f(timeframe="H1", bar_identity="P1"))}
        o2 = c2.resolve_sealed_snapshot("XAUUSD", 10, 10, [k2["P4"], k2["P1"]], {"H4": [(k2["P4"], True)], "H1": [(k2["P1"], True)]}, {"H4": 9, "H1": 10})
        self.assertNotEqual(o2["resolved_manifest_hash"], base["resolved_manifest_hash"])                                                                    # another registry basis (and keys) => another identity
        m = c.resolved_manifest(w6["resolved_manifest_hash"]); self.assertIn("CANDIDATE", m["label"]); self.assertIn("watermarks", m["supplied_unadmitted"]); [e for e in m["entries"] if e["timeframe"] == "H4"][0]["watermark"] = 999
        self.assertEqual([e for e in c.resolved_manifest(w6["resolved_manifest_hash"])["entries"] if e["timeframe"] == "H4"][0]["watermark"], 6)                                                   # public read is detached
        n = sum(1 for x in c._j.read_from(1) if x.kind == "SNAPSHOT_RESOLVED_MANIFEST"); run(); self.assertEqual(sum(1 for x in c._j.read_from(1) if x.kind == "SNAPSHOT_RESOLVED_MANIFEST"), n)       # identical re-resolution appends no second manifest
        h = c2.resolve_sealed_snapshot("XAUUSD", 10, 10, [k2["P4"]], {"H4": [(k2["P4"], True)]}, {})
        self.assertEqual((h["state"], h["resolved_manifest_hash"] is not None), (TF.UNRESOLVED, True))                                                      # unknown (missing) watermark: a held/UNRESOLVED identity, never RESOLVED
        self.assertIsNone(c.resolved_manifest("nope"))
