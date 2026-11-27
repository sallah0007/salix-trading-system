"""R24: (1) Core health evidence produced by the REAL materializer + independent verifier (not an injected callable); (2) B02 time-family logic that needs no calendar instance.
Simulation-labelled; never qualified; no calendar/registry/DST value is invented."""
import unittest
from stage_a.errors import Refusal
from stage_a.storage.object_store import InMemoryObjectStore
from stage_a.storage.authority_class import SimulationStore
from stage_a.coordination.object_store_journal import ObjectStoreJournal
from stage_a.composer.expression.manifest import Manifest
from stage_a.composer.expression.hashing import manifest_hash, graph_hash, program_hash
from stage_a.core.tracker_core import TrackerCore, COMPOSED_RECOMPUTATION
from stage_a.core import time_family as TF
from stage_a.tracker import reverification as RV
from stage_a.tracker.verification.verification_result import make_result, FAIL, INSUFFICIENT_EVIDENCE, SCOPE_MATERIALIZATION, PASS_PROFILE
from .fixtures import momentum_manifest
from .test_r24_core import code

def core(sim=True):
    st = InMemoryObjectStore(); st = SimulationStore(st) if sim else st
    j = ObjectStoreJournal(st, "rv", "w"); j.acquire_epoch(); return TrackerCore(j, simulation=sim)
SIMS = lambda: SimulationStore(InMemoryObjectStore())        # R25: a simulation Core's carrier must itself be simulation-class
def declared(m):
    from stage_a.composer.expression.artifacts import build_artifact
    a = build_artifact(m); return {"manifest_hash": a.manifest_hash, "graph_hash": a.graph_hash, "program_hash": a.program_hash}

class ComposedReverification(unittest.TestCase):
    def setUp(self):
        self.m = Manifest.from_dict(momentum_manifest()); self.key = "XAUUSD/H4/mom3/1"
    def test_real_materializer_and_verifier_produce_positive_core_health_evidence(self):
        c = core(); store = SIMS(); res = RV.reverify_manifest(c, manifest=self.m, declared=declared(self.m), store=store, now=10, max_age=5)
        self.assertEqual(res.status, "PASS"); r = c.recording_health(self.key, "1", 11)
        self.assertEqual((r.state, r.evidence_class, r.qualified), ("HEALTHY", "SIMULATION_COMPOSED_RECOMPUTATION", False))
        h = c._replay()["health"][self.key]; self.assertEqual(h["result_digest"], res.result_hash); self.assertEqual(h["verifier_id"], RV.VERIFIER_ID); self.assertEqual(h["evidence_class"], COMPOSED_RECOMPUTATION)
    def test_qualified_core_still_holds_health_over_the_same_evidence(self):
        c = core(False); RV.reverify_manifest(c, manifest=self.m, declared=declared(self.m), store=InMemoryObjectStore(), now=10, max_age=5)
        r = c.recording_health(self.key, "1", 11); self.assertEqual((r.state, r.local_state, r.qualified), ("HELD", "HEALTHY", False))
    def test_declared_hashes_must_be_supplied_and_a_wrong_declaration_fails_the_verifier_not_the_artifact(self):
        c = core(); self.assertEqual(code(RV.reverify_manifest, c, manifest=self.m, declared=None, store=SIMS(), now=10, max_age=5), "DECLARED_HASHES_REQUIRED")
        bad = dict(declared(self.m), program_hash="0" * 64); res = RV.reverify_manifest(c, manifest=self.m, declared=bad, store=SIMS(), now=10, max_age=5)
        self.assertEqual(res.status, "FAIL"); self.assertEqual(c.recording_health(self.key, "1", 11).state, "NOT_HEALTHY")          # a failing verification is NOT_HEALTHY evidence, never skipped
    def test_tampered_stored_bytes_fail_closed_and_never_clear_an_invalidation(self):
        class Tamper(InMemoryObjectStore):
            def get(self, k):
                g = super().get(k); return None if g is None else (g[0][:-1] + bytes([g[0][-1] ^ 1]),) + tuple(g[1:])
        from stage_a.storage.authority_class import approve_test_adapter; approve_test_adapter(Tamper)      # exact-type approved fault-injection adapter, wrapped in the simulation carrier
        c = core(); c.declare_dependency(self.key, "UP"); c.advance_epoch("UP", 1)
        RV.reverify_manifest(c, manifest=self.m, declared=declared(self.m), store=SimulationStore(Tamper()), now=10, max_age=5)
        self.assertEqual(code(c.reresolve, self.key, "1", 11), "WITNESS_NOT_POSITIVE"); self.assertIn("EPOCH_INVALIDATED", c.blocked(self.key))
        RV.reverify_manifest(c, manifest=self.m, declared=declared(self.m), store=SIMS(), now=12, max_age=5); c.reresolve(self.key, "1", 13); self.assertEqual(c.blocked(self.key), [])   # positive control
    def test_level_split_never_falls_back_from_l2_to_l1(self):
        mk = lambda st, ch: make_result(st, SCOPE_MATERIALIZATION, {}, ch, [])
        self.assertEqual(RV.split_levels(mk(INSUFFICIENT_EVIDENCE, [("artifact_present", False)])), ("FAIL", "UNAVAILABLE"))
        self.assertEqual(RV.split_levels(mk(INSUFFICIENT_EVIDENCE, [("structure_sound", True), ("equivalence_probe_batch", True), ("equivalence_probe_incremental", True)])), ("FAIL", "UNAVAILABLE"))   # the typed status wins over the check list
        self.assertEqual(RV.split_levels(mk(FAIL, [("record_field_set", False)])), ("FAIL", "UNAVAILABLE"))            # early return: recomputation never ran
        self.assertEqual(RV.split_levels(mk(FAIL, [("structure_sound", True), ("equivalence_probe_batch", False), ("equivalence_probe_incremental", True)])), ("PASS", "FAIL"))
        self.assertEqual(RV.split_levels(mk("PASS", [(n, True) for n in sorted(PASS_PROFILE)])), ("PASS", "PASS"))       # R26: only a COMPLETE PASS profile yields PASS/PASS
    def test_unknown_evidence_class_is_refused(self):
        c = core(); self.assertEqual(code(c.record_verification, "S", "1", "REQUIRED", "PASS", "PASS", 1, 5, "v", "d", None, "FORGED_QUALIFIED"), "HEALTH_EVIDENCE_CLASS_UNKNOWN")

REG = lambda: TF.TimeframeRegistry([("H4", "H1"), ("H1", "M15"), ("M15", None)])           # TEST registry handed in by the test: the module ships none
class TimeFamilyWiring(unittest.TestCase):
    def test_core_refuses_an_unregistered_timeframe_only_when_a_governed_registry_is_supplied(self):
        from .test_r24_core import facts, adm
        st = SimulationStore(InMemoryObjectStore()); j = ObjectStoreJournal(st, "tf", "w"); j.acquire_epoch(); c = TrackerCore(j, simulation=True, timeframes=TF.TimeframeRegistry([("H4", "H1"), ("H1", None)]))
        self.assertEqual(adm(c), "NEW")                                                   # facts() default timeframe H4 is registered
        self.assertEqual(code(c.admit_observation, facts(timeframe="D1"), b"p", 5, "V1"), "UNKNOWN_TIMEFRAME")
        self.assertEqual(len([r for r in j.read_from(0) if r.kind == "OBS_ADMITTED"]), 1)   # nothing was appended for the refused observation
        j2 = ObjectStoreJournal(st, "tf2", "w"); j2.acquire_epoch(); self.assertEqual(TrackerCore(j2, simulation=True).admit_observation(facts(timeframe="D1"), b"p", 5, "V1"), "NEW")   # no registry bound: legacy behaviour, explicitly scoped
class TimeFamily(unittest.TestCase):
    def test_empty_registry_knows_no_timeframe_and_ships_no_defaults(self):
        self.assertEqual(code(TF.TimeframeRegistry().require, "H4"), "UNKNOWN_TIMEFRAME"); self.assertEqual(code(REG().require, "D1"), "UNKNOWN_TIMEFRAME")
        self.assertEqual(code(TF.TimeframeRegistry, [("H4", None), ("H4", None)]), "TIMEFRAME_ENTRY_INVALID")
    def test_parent_completeness_needs_a_supplied_segmentation_and_exact_children(self):
        seg = {"P1": ["c1", "c2", "c3", "c4"]}; r = REG()
        self.assertEqual(TF.parent_completeness(r, "H4", "P1", seg, ["c1", "c2", "c3", "c4"]), (TF.COMPLETE, ""))
        self.assertEqual(TF.parent_completeness(r, "H4", "P1", seg, ["c1", "c3"]), (TF.INCOMPLETE, "MISSING:c2,c4"))
        self.assertEqual(TF.parent_completeness(r, "H4", "P2", seg, ["c1"])[0], TF.UNDETERMINED)                 # no segmentation supplied: never inferred from a count
        self.assertEqual(TF.parent_completeness(r, "H4", "P1", None, [])[0], TF.UNDETERMINED); self.assertEqual(TF.parent_completeness(r, "H4", "P1", {"P1": []}, [])[0], TF.UNDETERMINED)
        self.assertEqual(code(TF.parent_completeness, r, "H4", "P1", seg, ["c1", "cX"]), "CHILD_NOT_IN_PARENT_SEGMENTATION")
        self.assertEqual(code(TF.parent_completeness, r, "H4", "P1", seg, ["c1", "c1"]), "DUPLICATE_CHILD_OBSERVATION")        # four rows by repetition are not four children
        self.assertEqual(code(TF.parent_completeness, r, "M15", "P1", seg, []), "TIMEFRAME_HAS_NO_CHILD_LEVEL"); self.assertEqual(code(TF.parent_completeness, r, "W1", "P1", seg, []), "UNKNOWN_TIMEFRAME")
    def test_no_back_projection_half_open_and_incomplete_parents_never_exposed(self):
        self.assertFalse(TF.parent_visible_asof(10, 10)); self.assertTrue(TF.parent_visible_asof(9, 10)); self.assertFalse(TF.parent_visible_asof(11, 10))
        ps = [("A", 5, True), ("B", 8, True), ("C", 9, False), ("D", 10, True)]
        self.assertEqual(TF.latest_visible_parent(ps, 10).parent_id, "B"); self.assertEqual(TF.latest_visible_parent(ps, 11).parent_id, "D"); self.assertEqual(TF.latest_visible_parent(ps, 5).state, TF.NONE_VISIBLE)
        for bad in ((True, 5), (5, -1), ("5", 5), (5.0, 5)): self.assertEqual(code(TF.parent_visible_asof, *bad), "ASOF_MALFORMED")
if __name__ == "__main__": unittest.main()
