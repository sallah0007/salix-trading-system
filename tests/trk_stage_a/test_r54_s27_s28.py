"""R54: Composer V9 s27 (33 semicolon groups, source order, re-read from the live document this pass) and s28 TRACKER_SAFE_INTAKE_REPORT (23 entries) compared group by group with the code. The earlier "35" count is WITHDRAWN (not the source grouping). Generic gaps closed: (1) learned-derived upstream-generation absence no longer leaves ANCESTRY_COMPLETENESS=PASS; (2) the report's OUTCOME_INFORMATION_ACCESS_VERDICT is computed from the intake's own conformance result instead of a constant; (3) the report states which s27 token groups are absent and which groups carry no source key (none invented). Candidate SIMULATION; nothing here is a gate."""
import dataclasses, unittest
from stage_a.clocks import FixedClock
from stage_a.tracker import build_output_check as B
from stage_a.tracker.quant_intake_adapter import admit, build_safe_intake_report
from tracker_component import report as R
from tests.trk_stage_a.fixtures import SIM_CONF, package, momentum_manifest, build_output_for
SRC = ("CREATION_REQUEST_ID/ORDER_ID/CLAIM_ID", "REQUEST_SCHEMA_VERSION", "BUILDER_BUILD_ID", "request context", "purpose/hypothesis", "research mode", "PURPOSE_PROFILE_ID/HASH", "SIMULATION_OR_AUTHORITY_CLASS", "INSTRUMENT_PROFILE_ID/HASH", "SOURCE_CONFIG_ID/HASH", "BUILDER_VERSION/HASH", "TRACKER_CATALOG_SNAPSHOT_ID/HASH", "CATALOG_WATERMARK", "construction graph ID/hash", "exact input IDs/versions/hashes", "resolved feature identities/versions", "dependency graph/closures", "source/vintage/time semantics", "operation/grammar versions", "parameters", "search/candidate set/exclusions")
def rep(pkg, fits=None, ev=SIM_CONF, verdict="REJECT_FAIL_CLOSED", dec="REJECTED_INVALID"):
    a = admit(pkg, conformance=ev, accepted_fit_generations=fits or {}); return a, build_safe_intake_report(pkg, a, clock=FixedClock(), verdict=verdict, identity_decision=dec, registry_ref=None)
class Groups(unittest.TestCase):
    def test_33_groups_in_source_order_and_the_report_has_exactly_23_entries(self):
        self.assertEqual(len(B.SECTION27_GROUPS), 33); self.assertNotEqual(len(B.SECTION27_GROUPS), 35); self.assertEqual(tuple(g[1] for g in B.SECTION27_GROUPS[:21]), SRC); self.assertEqual(len(R.REPORT_FIELDS), 23)
    def test_every_keyed_group_names_only_source_named_keys(self):
        keys = {k for g in B.SECTION27_GROUPS for k in g[3]}; self.assertTrue(keys <= B.KNOWN_TOKEN_FIELDS | {"CLAIM_ID"}); self.assertEqual(B.KNOWN_TOKEN_FIELDS - keys, set())
    def test_status_distinguishes_present_absent_manifest_prose_and_learned_applicability(self):
        bo = build_output_for(momentum_manifest()); st = dict(B.section27_status(bo, learned_derived=False, manifest_verified=True))
        self.assertEqual(st[26], "NOT_APPLICABLE_NOT_LEARNED_DERIVED"); self.assertEqual(st[14], "CARRIED_BY_VERIFIED_MANIFEST"); self.assertEqual(st[4], "NO_SOURCE_KEY")
        del bo["BUILDER_BUILD_ID"]; st = dict(B.section27_status(bo, learned_derived=True, manifest_verified=False)); self.assertEqual(st[3], "ABSENT_TOKEN:BUILDER_BUILD_ID"); self.assertEqual(st[14], "MANIFEST_NOT_VERIFIED"); self.assertTrue(st[26].startswith("ABSENT_TOKEN") or st[26] == "PRESENT")
        self.assertEqual(B.section27_status(None, learned_derived=False, manifest_verified=False)[0][1], "ABSENT_TOKEN:CREATION_REQUEST_ID,ORDER_ID")
class Report(unittest.TestCase):
    FITS = {2: "b" * 64}
    def test_learned_derived_without_upstream_generation_is_not_ancestry_PASS(self):
        m = momentum_manifest(fit_refs=[{"generation": 2, "ref_hash": "b" * 64}]); bo = {k: v for k, v in build_output_for(m).items() if not k.startswith("UPSTREAM") and k != "GENERATION_AUTHORITY_CLASS"}
        a, r = rep(package(m, build_output=bo), self.FITS); self.assertEqual(r["FAILED_DIMENSION_REASON_CODES"], ["LEARNED_DERIVED_WITHOUT_UPSTREAM_GENERATION_IDENTITY"]); self.assertEqual(r["ANCESTRY_COMPLETENESS"], "FAIL")
    def test_oia_verdict_is_computed_from_the_conformance_result(self):
        p = package(); a = admit(p, conformance=SIM_CONF, accepted_fit_generations={}); r = build_safe_intake_report(p, a, clock=FixedClock(), verdict="ACCEPT_FOR_REGISTRY", identity_decision="NEW_CANONICAL_FEATURE", registry_ref="PROPOSED:x")
        self.assertEqual(r["OUTCOME_INFORMATION_ACCESS_VERDICT"], "PASS_ON_SUPPLIED_CONFORMANCE_EVIDENCE"); self.assertNotIn("OUTCOME_ACCESS_NOT_ASSESSED_BOUNDARY", r["OMISSIONS_EXCLUSIONS_REASONS"])
        bad = dataclasses.replace(p, build_output=dict(p.build_output, OUTCOME_INFORMATION_ACCESS="PERMITTED_UNDER_DECLARED_FITTING_CONTRACT")); a, r = rep(bad); self.assertEqual(r["OUTCOME_INFORMATION_ACCESS_VERDICT"], "FAIL:OUTCOME_ACCESS_DECLARATION_CONFLICT")
        a, r = rep(p, ev=None); self.assertEqual(r["OUTCOME_INFORMATION_ACCESS_VERDICT"], "FAIL:OUTCOME_ACCESS_UNVERIFIED_UNDER_FORBIDDEN")
        a, r = rep(dataclasses.replace(p, build_output=None)); self.assertEqual(r["OUTCOME_INFORMATION_ACCESS_VERDICT"], "NOT_ASSESSED"); self.assertIn("OUTCOME_ACCESS_NOT_ASSESSED_BOUNDARY", r["OMISSIONS_EXCLUSIONS_REASONS"])
    def test_report_lists_absent_token_groups_and_prose_groups_without_inventing_keys(self):
        p = package(); bo = {k: v for k, v in p.build_output.items() if k != "BUILDER_BUILD_ID"}; q = dataclasses.replace(p, build_output=bo); a = admit(q, conformance=SIM_CONF, accepted_fit_generations={}); r = build_safe_intake_report(q, a, clock=FixedClock(), verdict="ACCEPT_FOR_REGISTRY", identity_decision="NEW_CANONICAL_FEATURE", registry_ref="PROPOSED:x"); om = r["OMISSIONS_EXCLUSIONS_REASONS"]
        self.assertIn("S27_GROUP_3_ABSENT_TOKEN=BUILDER_BUILD_ID", om); self.assertIn("S27_PROSE_GROUPS_NO_SOURCE_KEY_NOT_ASSESSED=4,5,6,18,21,23,27,28,30,32,33", om)
if __name__ == "__main__": unittest.main()
