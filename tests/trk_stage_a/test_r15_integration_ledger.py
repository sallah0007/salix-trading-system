"""R15: ties the 'integrated vs reference-only' claims in the closeout to the actual import graph, and pins the exact journal->status-fact field gap.
A row cannot be labelled INTEGRATED without a non-test import path from the Tracker pipeline entry; a REFERENCE_ONLY row that becomes reachable fails this test so the
closeout is re-derived. Reachability is NOT correctness and NOT operational qualification."""
import unittest
from dataclasses import fields
from stage_a.coordination import transition_record as T
from stage_a.tracker.chain_status import StatusFact
from tests.trk_stage_a.integration_reach import reachable, import_graph

ENTRY = ("stage_a.tracker.pipeline",)
# (component module, expected class). Derived by reading the graph; the test enforces it.
INTEGRATED = ("stage_a.tracker.quant_intake_adapter", "stage_a.tracker.build_output_check", "stage_a.composer.expression.ceilings", "stage_a.composer.request_record",
              "stage_a.coordination.transition_record", "stage_a.tracker.quant_certification", "stage_a.tracker.materialization.stateful_materializer",
              "stage_a.tracker.verification.stateful_verifier", "stage_a.authority")
REFERENCE_ONLY = ("stage_a.context.news_hub_v2", "stage_a.tracker.lifecycle_status_event", "stage_a.tracker.status_projection", "stage_a.health.blast_radius",
                  "stage_a.gateway.v038", "stage_a.gateway.contracts", "stage_a.fw.receiver", "stage_a.fw.return_lineage", "stage_a.fw.descriptor_crosswalk",
                  "stage_a.ml.receiver", "stage_a.composer.expression.sqe_opset", "stage_a.health.envelope", "stage_a.health.evidence", "stage_a.tracker.publication", "stage_a.tracker.feature_lineage", "stage_a.tracker.version_relationship")

class Reachability(unittest.TestCase):
    def test_integrated_rows_have_a_non_test_path_from_the_pipeline(self):
        r = reachable(ENTRY)
        for m in INTEGRATED: self.assertIn(m, r, m)
    def test_reference_only_rows_have_no_production_path(self):
        r = reachable(ENTRY)
        for m in REFERENCE_ONLY: self.assertNotIn(m, r, m + " became reachable: re-derive the closeout row")
    def test_the_check_can_fail(self):
        g = import_graph()
        self.assertIn("stage_a.errors", reachable(("stage_a.tracker.pipeline",)))
        self.assertNotIn("stage_a.tracker.pipeline", reachable(("stage_a.errors",)))      # direction matters: a reversed graph would pass the tests above
        self.assertTrue(any(g.values()))

class JournalToStatusFactGap(unittest.TestCase):
    """The mapping record -> StatusFact is undefined by any source read (R7 names no status-origin principal). This pins the exact field mismatch so the claim
    stays tied to code: a decoder would have to INVENT every missing field."""
    def test_no_status_fact_field_is_a_journal_body_field(self):
        need = {f.name for f in fields(StatusFact)}
        have = set()
        for k in T.KINDS: have |= set(T._REQUIRED[k])
        self.assertEqual(need & have, set())                                    # exact: sequence/status/available_asof/correction_marked/mv are NOT in any body
        self.assertEqual(need, {"mv", "sequence", "status", "available_asof", "correction_marked", "tracker_designated"})
    def test_lifecycle_kinds_are_not_chain_statuses(self):
        from stage_a.tracker import chain_status as C
        self.assertTrue(set(T.KINDS).isdisjoint(set(C.ALL)))                    # vocabulary mismatch: no mapping source read
class FunctionInvocation(unittest.TestCase):
    """Import is not invocation (R16 counterexample: check_outcome_access was imported-adjacent but never called from intake). These pin which helpers the production intake
    path actually CALLS and which it does not, so the closeout cannot call a helper 'integrated' by import alone."""
    def test_intake_calls_these_checks(self):
        from tests.trk_stage_a.integration_reach import called_names
        c = called_names("stage_a/tracker/quant_intake_adapter.py")
        for f in ("check_build_output", "check_conformance", "check_capability_declaration", "check_request_record", "check_fit_refs", "check_declared"):
            self.assertIn(f, c, f)
    def test_conformance_calls_outcome_access_but_nothing_calls_the_open_helpers(self):
        from tests.trk_stage_a.integration_reach import called_names
        self.assertIn("check_outcome_access", called_names("stage_a/tracker/build_output_check.py"))
        for mod in ("stage_a/tracker/quant_intake_adapter.py", "stage_a/tracker/pipeline.py", "stage_a/tracker/build_output_check.py"):
            c = called_names(mod)
            self.assertNotIn("check_inputs_resolve", c, mod); self.assertNotIn("check_reproduction", c, mod)      # OPEN helpers: if this fails, re-derive the closeout row
    def test_pipeline_does_not_call_consumer_seam_validators(self):
        from tests.trk_stage_a.integration_reach import called_names
        c = called_names("stage_a/tracker/pipeline.py")
        for f in ("resolve_context", "blast_radius", "check_fw_augmented", "check_generation", "journal_to_status_event", "feature_deps_from_quant_manifests"): self.assertNotIn(f, c, f)
class BaselineConnectionLimits(unittest.TestCase):
    """R18: D1 hard-False construction seam and the OPTIONAL baseline path are real connection limitations, pinned (not hidden behind the quant path map)."""
    def test_optional_baseline_none_accepts_with_no_baseline_identity_registration(self):
        from tests.trk_stage_a.fixtures import Rig, package
        rig = Rig(baseline=None); p = package(); rig.issue(p); o = rig.pipe.run(p)
        self.assertTrue(o.accepted_ok)                                         # journaled acceptance WITHOUT any baseline identity registration: a limitation, not a feature
        self.assertIsNone(rig.pipe._baseline)
    def test_production_seam_is_hard_false_and_installed_nowhere_in_non_test_code(self):
        import pathlib, re
        from tracker_identity import store
        self.assertIs(store._governed_construction_authority({}), False)
        for f in pathlib.Path(__file__).resolve().parents[2].joinpath("stage_a").rglob("*.py"):
            self.assertNotRegex(f.read_text(), r"_governed_construction_authority\s*=|patch\.object\([^)]*_governed_construction_authority", str(f))
if __name__ == "__main__": unittest.main()
