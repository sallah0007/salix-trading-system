"""R17: the combined closeout must not silently drop a requirement row or cite a code path that does not exist. Pins presence, not truth: the rows' CONTENT is reviewed by humans."""
import pathlib, re, unittest
ROOT = pathlib.Path(__file__).resolve().parents[2]
DOC = (ROOT / "docs/closeout/TRK-STAGE-A-TRACKER-COMBINED-CLOSEOUT.md").read_text()
E03 = """authority identifiers errors clocks currentness replay observability composer/request_classification composer/governed_order_adapter composer/build_executor composer/refit_executor composer/build_output
expression/manifest expression/schema expression/canonical_encoding expression/hashing expression/opcodes expression/capability expression/evaluator expression/fit_generation expression/artifacts
tracker/quant_intake_adapter tracker/quant_certification tracker/publication materialization/stateful_materializer verification/stateful_verifier verification/verification_result
context/event_identity context/coverage context/applicability context/resolver context/causal_gate gateway/dependency_resolution gateway/binding gateway/non_delivery gateway/settlement gateway/health_snapshot
fw/request_adapter fw/input_binding fw/return_lineage ml/dataset_binding ml/standalone_ancestry ml/fw_augmented_rebind ml/generation_lineage health/b0_adapter health/quant_evidence health/blast_radius health/expectation
coordination/interface coordination/transition_record coordination/object_store_journal coordination/fencing coordination/recovery coordination/scheduler storage/object_store storage/postgres_read_model storage/keys""".split()
class Closeout(unittest.TestCase):
    def test_the_e03_tree_is_57_paths_and_each_has_a_row(self):
        self.assertEqual(len(E03), 57)
        for i, p in enumerate(E03, 1): self.assertRegex(DOC, r"\| %d \| (stage_a/)?%s\.py \|" % (i, re.escape(p)), p)
    def test_every_tr_d_and_a07_row_is_present(self):
        for i in range(1, 16): self.assertIn("| TR-%02d |" % i, DOC)
        for i in range(1, 19): self.assertIn("| D%d |" % i, DOC)
        self.assertIn("| D12' |", DOC)
        for i in range(1, 5): self.assertIn("| A07-%d |" % i, DOC)
        self.assertIn("100", DOC); self.assertIn("RAISE_FOR_SOURCE_OWNER_DISPOSITION", DOC)
    def test_every_baseline_obligation_row_is_present(self):
        for i in range(1, 25): self.assertIn("| B%02d |" % i, DOC)
        for h in ("ecaa9af35c712dbc38bdfe8a22b1cb81406a13a6db46cf640caeca89b5f3de4c", "ea9e7949397dd1e9ad001334425fdfeb96706d7eadca67bd043496d6ec91dfc0", "cd47a366f4cd49bef008bc97bfb8fcf04c5bb49f50fbd883cd875bcc82d20013"): self.assertIn(h, DOC)
    def test_a07_2_is_recorded_as_settled_staffing_not_reasked(self):
        self.assertIn("SETTLED STAFFING DECISION (not re-asked)", DOC); self.assertNotIn("meet or waive in writing", DOC)
    def test_every_cited_code_path_exists(self):
        for p in set(re.findall(r"`((?:stage_a|tests|tracker_component)/[A-Za-z0-9_/]+\.py)`", DOC)): self.assertTrue((ROOT / p).exists(), p)
    def test_no_completion_or_signoff_claim(self):
        self.assertIn("NOT a completion claim", DOC); self.assertIn("NOT pre-approved sign-off", DOC)
class R20Appendix(unittest.TestCase):
    APP = (ROOT / "docs/proposals/TRK_ENGINEERING_APPENDIX_PROPOSED.md").read_text()
    def test_appendix_covers_every_b_family_with_the_required_fields_and_is_linked(self):
        self.assertIn("TRK_ENGINEERING_APPENDIX_PROPOSED.md", DOC)
        for i in range(1, 25):
            blk = self.APP.split("### B%02d - " % i)[1].split("\n### ")[0]
            for f in ("SOURCE:", "REUSE:", "PORT:", "OWNERS:", "STATE:", "REFUSALS:", "CALLPATH:", "TEST:", "EVIDENCE:", "INPUT:"): self.assertIn("- " + f, blk, "B%02d %s" % (i, f))
        for i in range(1, 16): self.assertIn("| TR-%02d |" % i, self.APP)
        for i in range(1, 19): self.assertIn("| D%d |" % i, self.APP)
        self.assertIn("PROPOSED INTERNAL ENGINEERING DESIGN", self.APP); self.assertIn("NOT an adopted governing schema", self.APP)
    def test_current_view_has_no_stale_blueprint_or_optional_baseline_wording(self):
        body = DOC.split("## 1. Integration ledger")[1]
        self.assertNotIn("Recommend: Manager decides whether baseline may be None", body)
        self.assertNotIn("whether E03 stands in for the blueprint", body)
        self.assertNotIn("whether Core observation storage is in this component's scope", body)
        self.assertIn("NOT_LOCATED_IN_NAMED_SOURCES", body); self.assertIn("SOURCE_INPUT_UNBOUND", DOC)
if __name__ == "__main__": unittest.main()
