import copy, unittest
from unittest import mock
from tracker_identity import (LookupOutcome, CanonicalEraBoundary, CanonicalIdentityStore, SearchPolicy,
                              MANDATORY_DUPLICATE_CONTROL_SCOPES, governed_normalizer, governed_search_policy)
import tracker_identity.store as baseline_store
from tracker_component.order import ConstructionOrder
from tracker_component.claims import Refusal as ClaimRefusal
from tracker_component import report as R
from stage_a.errors import Refusal, StaleFence, UnknownCommit
from stage_a.coordination import transition_record as T
from stage_a.coordination.recovery import find_orphans, cold_rebuild_head
from stage_a.currentness import resolve_asof, AS_KNOWN, EVENTUAL
from stage_a.replay import replay
from stage_a.tracker import publication
from stage_a.tracker.pipeline import BaselineBinding
from stage_a.tracker.quant_intake_adapter import admit, NO_QUANT_FEATURE, FAILED_REQUESTED_BUILD, QUANT_FEATURE
from stage_a.tracker.authority_bridge import make_construction_authority_resolver
from stage_a.tracker.verification.verification_result import make_result, FAIL, SCOPE_MATERIALIZATION
from .fixtures import qualified_journal_from_simulated, SIM_CONF, Rig, package, momentum_manifest, ANCHOR, IDENTITY_FIELDS

def feature_records(rig, ns="XAUUSD/H4/mom3"):
    return rig.journals.journal(ns).read_from(1)

class HappyPath(unittest.TestCase):
    def setUp(self):
        self.rig = Rig(); self.pkg = package(); self.rig.issue(self.pkg); self.out = self.rig.pipe.run(self.pkg)
    def test_accepted_with_authority_ref_and_all_evidence(self):
        o = self.out
        self.assertTrue(o.accepted_ok); self.assertEqual(o.stage, "CANONICAL_ACCEPTANCE")
        self.assertTrue(o.authority_ref.startswith("ACCEPTED:XAUUSD/H4/mom3#1:"))
        self.assertEqual(o.certification.status, "CERTIFIED"); self.assertEqual(o.verification.status, "PASS")
        st = replay("XAUUSD/H4/mom3", feature_records(self.rig))["1"]
        self.assertEqual(st.status, T.CANONICAL_ACCEPTED)
        self.assertEqual(st.accepted_body["verification_hash"], o.verification.result_hash)
        self.assertEqual(st.accepted_body["manifest_hash"], o.materialization["manifest_hash"])
    def test_report_has_23_fields_verifies_and_is_tamper_evident(self):
        rep = self.out.report
        R.verify_report(rep); self.assertEqual(len(rep), 23)
        self.assertEqual(rep["INTAKE_VERDICT"], "ACCEPT_FOR_REGISTRY")
        bad = dict(rep, INTAKE_VERDICT="REJECT_FAIL_CLOSED")
        with self.assertRaises(R.ReportError): R.verify_report(bad)
        acc = replay("XAUUSD/H4/mom3", feature_records(self.rig))["1"].accepted_body
        self.assertEqual(acc["safe_intake_report_hash"], rep["FINAL_REPORT_HASH"])
    def test_claim_consumed_exactly_once_and_witnessed(self):
        c = self.rig.claims.claim("CLAIM:REQ-1"); self.assertEqual(c["state"], "CONSUMED")
        w = self.rig.claims.consumed_record("CLAIM:REQ-1")
        acc = replay("XAUUSD/H4/mom3", feature_records(self.rig))["1"].accepted_body
        self.assertEqual(acc["claim_witness"], "claims#%d:%s" % (w.seq, w.record_hash))
    def test_rerun_is_idempotent(self):
        before = len(feature_records(self.rig)); again = self.rig.pipe.run(self.pkg)
        self.assertTrue(again.accepted_ok); self.assertEqual(again.accepted.seq, self.out.accepted.seq)
        self.assertEqual(len(feature_records(self.rig)), before)
        self.assertEqual(len([r for r in self.rig.claims_journal.read_from(1) if r.kind == "CLAIM_CONSUMED"]), 1)
    def test_publish_then_currentness_and_not_delivery(self):
        j = qualified_journal_from_simulated(self.rig); fk = self.out.admission.feature_key
        pr = publication.publish(j, fk, self.out.verification)
        self.assertFalse(pr.delivered)
        recs = j.read_from(1)
        self.assertEqual(resolve_asof("XAUUSD/H4/mom3", recs, mode=EVENTUAL).available_version, "1")
        self.assertIsNone(resolve_asof("XAUUSD/H4/mom3", recs, mode=AS_KNOWN, asof_seq=1).available_version)
        with self.assertRaises(Refusal) as c: publication.publish(j, fk, self.out.verification)
        self.assertEqual(c.exception.code, "ILLEGAL_TRANSITION")
        publication.withdraw(j, fk, "superseded")
        self.assertIsNone(resolve_asof("XAUUSD/H4/mom3", j.read_from(1), mode=EVENTUAL).available_version)
        self.assertEqual(resolve_asof("XAUUSD/H4/mom3", j.read_from(1), mode=AS_KNOWN, asof_seq=2).available_version, "1")
    def test_publish_refuses_failed_or_foreign_verification(self):
        j = qualified_journal_from_simulated(self.rig); fk = self.out.admission.feature_key
        failed = make_result(FAIL, SCOPE_MATERIALIZATION, {}, [("x", False)], ["x"])
        with self.assertRaises(Refusal) as c: publication.publish(j, fk, failed)
        self.assertEqual(c.exception.code, "VERIFICATION_NOT_PASS")
        foreign = make_result("PASS", SCOPE_MATERIALIZATION, {"other": "1"}, [("x", True)], [])
        with self.assertRaises(Refusal) as c: publication.publish(j, fk, foreign)
        self.assertEqual(c.exception.code, "VERIFICATION_NOT_THE_ACCEPTED_ONE")
        wrong_scope = make_result("PASS", "OTHER_SCOPE", {}, [], [])
        with self.assertRaises(Refusal) as c: publication.publish(j, fk, wrong_scope)
        self.assertEqual(c.exception.code, "VERIFICATION_SCOPE_MISMATCH")
    def test_publish_unaccepted_version_refused(self):
        j = qualified_journal_from_simulated(self.rig)
        from stage_a.identifiers import FeatureKey, Scope
        with self.assertRaises(Refusal) as c: publication.publish(j, FeatureKey(Scope("XAUUSD", "H4"), "mom3", "2"), self.out.verification)
        self.assertEqual(c.exception.code, "NOT_ACCEPTED")
    def test_cold_rebuild_and_orphan_free(self):
        j = self.rig.journals.journal("XAUUSD/H4/mom3"); cold_rebuild_head(j)
        self.assertEqual(find_orphans(self.rig.store, "XAUUSD/H4/mom3", j), [])

class Rejections(unittest.TestCase):
    def reject(self, pkg, order=True, expect_dim=None, expect_code=None, rig=None):
        rig = rig or Rig()
        if order: rig.issue(pkg)
        o = rig.pipe.run(pkg)
        self.assertFalse(o.accepted_ok)
        self.assertEqual(o.classification, FAILED_REQUESTED_BUILD)
        dims = [d for d, _ in o.failures]; codes = [c for _, c in o.failures]
        if expect_dim: self.assertIn(expect_dim, dims, o.failures)
        if expect_code: self.assertTrue(any(expect_code in c for c in codes), o.failures)
        R.verify_report(o.report)
        self.assertEqual(feature_records(rig), [])
        return rig, o
    def test_declared_hash_mismatch(self):
        self.reject(package(declared_program_hash="0" * 64), order=False, expect_dim="HASH_BINDING")
    def test_capability_declaration_mismatch(self):
        m = momentum_manifest(); m["declared_capabilities"].remove("WINDOW_ROLLING")
        self.reject(package(m), order=False, expect_dim="CAPABILITY", expect_code="CAPABILITY_DECLARATION_MISMATCH")
    def test_scope_binding(self):
        self.reject(package(expected_instrument="EURUSD"), order=False, expect_dim="SCOPE_BINDING")
    def test_stale_and_unknown_fit_generation(self):
        fr = [{"generation": 1, "ref_hash": "a" * 64}]
        rig = Rig(fits={1: "a" * 64, 2: "b" * 64})
        self.reject(package(momentum_manifest(fit_refs=fr)), order=False, expect_dim="FIT_ANCESTRY", expect_code="STALE", rig=rig)
        self.reject(package(momentum_manifest(fit_refs=[{"generation": 9, "ref_hash": "a" * 64}])), order=False, expect_dim="FIT_ANCESTRY", expect_code="UNKNOWN")
    def test_fit_ref_current_generation_alone_is_not_ancestry(self):
        # R54: narrow fit-reference currency passes, but whole ancestry is UNBOUND => held (UNKNOWN), never accepted. The accepting control (genuine closure) is tests/trk_stage_a/test_r54_ancestry.py.
        rig = Rig(fits={1: "a" * 64, 2: "b" * 64}); p = package(momentum_manifest(fit_refs=[{"generation": 2, "ref_hash": "b" * 64}]))
        rig.issue(p); self.assertFalse(rig.pipe.run(p).accepted_ok)
    def test_missing_identity_fields(self):
        idf = copy.deepcopy(IDENTITY_FIELDS); del idf["price_basis"]
        self.reject(package(identity_fields=idf), order=False, expect_dim="IDENTITY_CONTENT_KEY")
    def test_era1_structural_absence_is_not_absence(self):
        self.reject(package(lookup=LookupOutcome.ABSENT_EXACT_STRUCTURAL_IN_ERA_1), order=False, expect_dim="LOOKUP_COMPLETENESS")
        self.reject(package(lookup=LookupOutcome.ABSENT_IN_ERA_1), order=False, expect_dim="LOOKUP_COMPLETENESS")
        self.reject(package(lookup="garbage"), order=False, expect_dim="LOOKUP_COMPLETENESS")
        self.reject(package(lookup=LookupOutcome.INCOMPLETE_LOOKUP), order=False, expect_dim="LOOKUP_COMPLETENESS")
    def test_exact_duplicate_reuse_and_near_review(self):
        rig, o = self.reject(package(lookup=LookupOutcome.EXACT_CANONICAL_IDENTITY), order=False, expect_dim="DUPLICATE")
        self.assertEqual(o.report["INTAKE_VERDICT"], "REUSE_EXISTING")
        rig, o = self.reject(package(lookup=LookupOutcome.NEAR_MATCH), order=False, expect_dim="DUPLICATE")
        self.assertEqual(o.report["INTAKE_VERDICT"], "REVIEW_REQUIRED")
    def test_no_order(self):
        self.reject(package(), order=False, expect_dim="CONSTRUCTION_AUTHORITY", expect_code="NO_ORDER")
    def test_wrong_issuer_binding_subject(self):
        for kw, code in ((dict(issuer="RANDOM_ACTOR"), "ISSUER_NOT_ANCHORED"), (dict(binding="OTHER"), "SOURCE_BINDING_MISMATCH")):
            rig = Rig(); p = package(); rig.issue(p, **kw)
            o = rig.pipe.run(p); self.assertFalse(o.accepted_ok); self.assertIn(code, [c for _, c in o.failures])
        rig = Rig(); p = package(); rig.claims.issue_order(ConstructionOrder("ORD-1", "WRONG-SUBJECT", "SRC-BINDING-1", "MANAGER"))
        o = rig.pipe.run(p); self.assertIn("ORDER_SUBJECT_MISMATCH", [c for _, c in o.failures])
    def test_revoked_order(self):
        rig = Rig(); p = package(); rig.issue(p); rig.claims.revoke_order("ORD-1", "no")
        o = rig.pipe.run(p); self.assertIn("ORDER_REVOKED", [c for _, c in o.failures])
    def test_expired_order(self):
        rig = Rig(); p = package(); adm = admit(p, conformance=SIM_CONF, accepted_fit_generations={})
        rig.claims.issue_order(ConstructionOrder("ORD-1", adm.subject_key, "SRC-BINDING-1", "MANAGER", valid_until_seq=0))
        o = rig.pipe.run(p); self.assertIn("ORDER_EXPIRED", [c for _, c in o.failures])
    def test_subject_already_claimed_by_other_request(self):
        rig = Rig(); p = package(); rig.issue(p)
        rig.claims.reserve(subject_key=admit(p, conformance=SIM_CONF, accepted_fit_generations={}).subject_key, request_id="OTHER", order_id="ORD-1", lookup_outcome=LookupOutcome.ABSENT)
        o = rig.pipe.run(p); self.assertIn("SUBJECT_ALREADY_CLAIMED", [c for _, c in o.failures])
    def test_failed_build_releases_claim_so_subject_is_not_stuck(self):
        rig = Rig(); p = package(); rig.issue(p)
        bad = mock.patch("stage_a.tracker.pipeline.certify", side_effect=lambda m, pr: __import__("stage_a.tracker.quant_certification", fromlist=["x"]).Certification("REFUSED", (), ("forced",), "h"))
        with bad: o = rig.pipe.run(p)
        self.assertFalse(o.accepted_ok); self.assertEqual(rig.claims.claim("CLAIM:REQ-1")["state"], "RELEASED")
        p2 = package(request_id="REQ-2", attempt_id="ATT-2"); rig.claims.issue_order(ConstructionOrder("ORD-2", admit(p2, conformance=SIM_CONF, accepted_fit_generations={}).subject_key, "SRC-BINDING-1", "MANAGER"))
        self.assertTrue(rig.pipe.run(package(request_id="REQ-2", attempt_id="ATT-2", order_id="ORD-2")).accepted_ok)

class TR06(unittest.TestCase):
    def test_failed_requested_build_never_becomes_no_quant_feature(self):
        for m in ({"garbage": 1}, None, "string", []):
            o = Rig().pipe.run(package(m, declared_manifest_hash=None, expected_instrument="XAUUSD", expected_timeframe="H4"))
            self.assertEqual(o.classification, FAILED_REQUESTED_BUILD, m); self.assertFalse(o.accepted_ok)
            self.assertIsNotNone(o.report); self.assertEqual(o.report["INTAKE_VERDICT"], "REJECT_FAIL_CLOSED")
    def test_explicit_no_quant_request_has_no_effects(self):
        rig = Rig(); o = rig.pipe.run(package(None, quant=False))
        self.assertEqual(o.classification, NO_QUANT_FEATURE); self.assertIsNone(o.report); self.assertFalse(o.accepted_ok)
        self.assertEqual(rig.claims_journal.read_from(1), [])
    def test_no_quant_request_with_manifest_is_a_failure(self):
        o = Rig().pipe.run(package(quant=False))
        self.assertEqual(o.classification, FAILED_REQUESTED_BUILD)

class IsolationAndConflict(unittest.TestCase):
    def test_same_id_version_different_instrument_timeframe_are_independent(self):
        rig = Rig()
        for i, (ins, tf) in enumerate((("XAUUSD", "H4"), ("EURUSD", "H4"), ("XAUUSD", "H1"))):
            p = package(momentum_manifest(instrument=ins, timeframe=tf), request_id="R%d" % i, attempt_id="A%d" % i, order_id="O%d" % i,
                        identity_fields=dict(IDENTITY_FIELDS, scope_universe="%s/ERA_1" % ins))
            rig.issue(p); o = rig.pipe.run(p); self.assertTrue(o.accepted_ok, o.failures)
            self.assertEqual(o.authority_ref.split("#")[0], "ACCEPTED:%s/%s/mom3" % (ins, tf))
        for ns in ("XAUUSD/H4/mom3", "EURUSD/H4/mom3", "XAUUSD/H1/mom3"):
            self.assertEqual(len(rig.journals.journal(ns).read_from(1)), 1)
    def test_same_version_different_program_is_version_conflict(self):
        rig = Rig(); p1 = package(); rig.issue(p1); self.assertTrue(rig.pipe.run(p1).accepted_ok)
        p2 = package(momentum_manifest(window=4), request_id="R2", attempt_id="A2", order_id="O2",
                     identity_fields=dict(IDENTITY_FIELDS, parameters={"lookback_bars": 4}))
        rig.issue(p2)
        with self.assertRaises(Refusal) as c: rig.pipe.run(p2)
        self.assertEqual(c.exception.code, "VERSION_CONFLICT")
        self.assertEqual(rig.claims.claim("CLAIM:R2")["state"], "RELEASED")
        self.assertEqual(len(feature_records(rig)), 1)
    def test_content_duplicate_under_new_id_is_blocked_by_subject_claim(self):
        rig = Rig(); p1 = package(); rig.issue(p1); rig.pipe.run(p1)
        alias = package(momentum_manifest(feature_id="alias"), request_id="R3", attempt_id="A3", order_id="O3")
        k1, k2 = admit(p1, conformance=SIM_CONF, accepted_fit_generations={}).subject_key, admit(alias, conformance=SIM_CONF, accepted_fit_generations={}).subject_key
        self.assertEqual(k1, k2)       # baseline content key excludes identity: same program+semantics = same subject
        rig.claims.issue_order(ConstructionOrder("O3", k2, "SRC-BINDING-1", "MANAGER"))
        o = rig.pipe.run(alias)
        self.assertFalse(o.accepted_ok); self.assertIn("SUBJECT_ALREADY_CLAIMED", [c for _, c in o.failures])

class Crash(unittest.TestCase):
    def test_revocation_between_verification_and_acceptance_refuses(self):
        rig = Rig(); p = package(); rig.issue(p)
        real = rig.pipe._mat.materialize
        def hooked(m, probe):
            r = real(m, probe); rig.claims.revoke_order("ORD-1", "late"); return r
        rig.pipe._mat.materialize = hooked
        with self.assertRaises(Refusal) as c: rig.pipe.run(p)
        self.assertEqual(c.exception.code, "ORDER_REVOKED")
        self.assertEqual(feature_records(rig), []); self.assertEqual(rig.claims.claim("CLAIM:REQ-1")["state"], "RELEASED")
    def test_crash_after_consume_before_accept_then_restart_completes_once(self):
        rig = Rig(); p = package(); rig.issue(p)
        j = rig.journals.journal("XAUUSD/H4/mom3"); real = j.append
        j.append = lambda *a, **k: (_ for _ in ()).throw(RuntimeError("crash"))
        with self.assertRaises(RuntimeError): rig.pipe.run(p)
        self.assertEqual(rig.claims.claim("CLAIM:REQ-1")["state"], "CONSUMED"); self.assertEqual(feature_records(rig), [])
        rig2 = Rig(store=rig.raw_store)          # restart: fresh epochs, fresh projections, same durable store
        o = rig2.pipe.run(p); self.assertTrue(o.accepted_ok)
        self.assertEqual(len([r for r in rig2.claims_journal.read_from(1) if r.kind == "CLAIM_CONSUMED"]), 1)
        self.assertEqual(len(feature_records(rig2)), 1)
    def test_stale_fence_refuses_before_authority_is_spent(self):
        rig = Rig(); p = package(); rig.issue(p)
        rig.journals.journal("XAUUSD/H4/mom3")
        from stage_a.tracker.registry import FeatureJournalSet
        FeatureJournalSet(rig.store, "usurper").journal("XAUUSD/H4/mom3")
        with self.assertRaises(StaleFence): rig.pipe.run(p)
        self.assertEqual(rig.claims.claim("CLAIM:REQ-1")["state"], "BOUND")          # not consumed
        rig.journals.reacquire("XAUUSD/H4/mom3"); self.assertTrue(rig.pipe.run(p).accepted_ok)
    def test_unknown_commit_ack_lost_is_resolved_to_committed(self):
        rig = Rig(); p = package(); rig.issue(p); s = rig.store; real = s.put_if_match
        def lose(key, data, etag):
            ok = real(key, data, etag)
            if ok and key == "head/XAUUSD/H4/mom3": s.put_if_match = real; raise UnknownCommit("ack lost")
            return ok
        s.put_if_match = lose
        o = rig.pipe.run(p); self.assertTrue(o.accepted_ok); self.assertEqual(len(feature_records(rig)), 1)
    def test_unknown_commit_dropped_write_is_retried_not_assumed(self):
        rig = Rig(); p = package(); rig.issue(p); s = rig.store; real = s.put_if_match
        def drop(key, data, etag):
            if key == "head/XAUUSD/H4/mom3": s.put_if_match = real; raise UnknownCommit("dropped")
            return real(key, data, etag)
        s.put_if_match = drop
        o = rig.pipe.run(p); self.assertTrue(o.accepted_ok); self.assertEqual(len(feature_records(rig)), 1)
        # the dropped HEAD swap left the record object behind; the identical retry is content-addressed to the SAME
        # object, so it became the accepted record rather than an orphan
        self.assertEqual(find_orphans(rig.store, "XAUUSD/H4/mom3", rig.journals.journal("XAUUSD/H4/mom3")), [])

class ProducerSideDefects(unittest.TestCase):
    """Defects injected into the PRODUCER side must be stopped by independent evidence, not by the producer's own checks."""
    def run_with(self, patcher):
        rig = Rig(); p = package(); rig.issue(p)
        with patcher: return rig, rig.pipe.run(p)
    def test_evaluator_defect_caught_by_independent_reference(self):
        import stage_a.composer.expression.evaluator as ev
        real = ev.op_value
        def bad(node, t, get):
            v = real(node, t, get)
            return v if node["op"] != "rolling_mean" or v is None else v * 1.0000000001
        rig, o = self.run_with(mock.patch.object(ev, "op_value", bad))
        self.assertFalse(o.accepted_ok); self.assertEqual(o.stage, "RECORDING_VERIFICATION")
        self.assertTrue(any("equivalence_probe_batch" in c for _, c in o.failures))
        self.assertEqual(feature_records(rig), [])
    def test_incremental_path_defect_caught(self):
        import stage_a.tracker.materialization.stateful_materializer as sm
        real = sm.IncrementalEvaluator.push
        def bad(self, row):
            v = real(self, row); return None if self.n == 20 else v
        rig, o = self.run_with(mock.patch.object(sm.IncrementalEvaluator, "push", bad))
        self.assertFalse(o.accepted_ok); self.assertTrue(any("equivalence_probe_incremental" in c for _, c in o.failures))
    def test_materializer_encoding_defect_caught(self):
        import stage_a.composer.expression.canonical_encoding as ce
        real = ce._dump
        def bad(obj):
            if isinstance(obj, dict) and "fit_refs" in obj and "schema" in obj:
                obj = {k: v for k, v in obj.items() if k != "declared_capabilities"}
            return real(obj)
        rig, o = self.run_with(mock.patch.object(ce, "_dump", bad))
        self.assertFalse(o.accepted_ok); self.assertEqual(feature_records(rig), [])
    def test_hash_domain_defect_caught_at_binding(self):
        import stage_a.composer.expression.hashing as hs
        rig, o = self.run_with(mock.patch.object(hs, "PROGRAM_DOMAIN", b"WRONG\x00"))
        self.assertFalse(o.accepted_ok)
    def test_verifier_side_defect_is_caught_by_the_cross_check(self):
        import stage_a.tracker.verification.independent_traversal as it
        real = it.reference_evaluate
        def bad(p, series):
            out = real(p, series); return [None if x is None else x + 1.0 for x in out]
        with mock.patch.object(it, "reference_evaluate", bad), mock.patch("stage_a.tracker.verification.stateful_verifier.reference_evaluate", bad):
            rig = Rig(); p = package(); rig.issue(p); o = rig.pipe.run(p)
        self.assertFalse(o.accepted_ok); self.assertEqual(o.stage, "RECORDING_VERIFICATION")
    def test_poisoned_artifact_key_refused(self):
        rig = Rig(); p = package(); rig.issue(p)
        from stage_a.composer.expression.manifest import Manifest
        from stage_a.composer.expression.hashing import manifest_hash
        key = "artifact/" + manifest_hash(Manifest.from_dict(p.manifest)); rig.store.put_if_absent(key, b"poison")
        o = rig.pipe.run(p); self.assertFalse(o.accepted_ok); self.assertIn("MATERIALIZATION", [d for d, _ in o.failures])

# ---------------------------------------------------------------- baseline integration
def _policy():
    p = SearchPolicy("safe-intake", "1", "", ("current_active",), ("current_active",), {})
    return SearchPolicy(p.policy_id, p.version, p.computed_hash(), p.required_scopes, p.searched_scopes, p.scope_exclusions)

def _boundary():
    vals = dict(era_id="ERA_1", version="1", boundary_hash="", effective_ts="2026-09-19T20:47:37+10:00",
                predecessor_era_id="ERA_0", registry_id="SALIX-ERA1-REGISTRY", catalogue_id="SALIX-ERA1-FEATURE-CATALOGUE",
                source_universe_id="SALIX-ERA1-SOURCE-UNIVERSE-001", pre_era_content_default="UNRESOLVED_NON_IMPORTABLE",
                historical_gap_status="UNRESOLVED", historical_gap_owner="MANAGER",
                revisit_trigger="IF_ERA0_ARTIFACT_LOCATED_REVIEW_BEFORE_IMPORT", absent_proven=False,
                created_by="SALIX_MANAGER", approval_authority="OWNER", created_ts="2026-09-19T20:47:37+10:00")
    x = CanonicalEraBoundary(**vals); vals["boundary_hash"] = x.computed_hash(); return CanonicalEraBoundary(**vals)

def baseline_binding():
    st = CanonicalIdentityStore()
    for sc in MANDATORY_DUPLICATE_CONTROL_SCOPES: st.declare_scope(sc, "EMPTY_VERIFIED")
    return BaselineBinding(st, _boundary(), governed_search_policy(), governed_normalizer())

class BaselineIntegration(unittest.TestCase):
    def test_production_seam_is_untouched_and_false(self):
        self.assertIs(baseline_store._governed_construction_authority({}), False)
    def test_without_installed_resolver_baseline_registration_fails_closed(self):
        bb = baseline_binding(); rig = Rig(baseline=bb); p = package(); rig.issue(p)
        o = rig.pipe.run(p)
        self.assertFalse(o.accepted_ok); self.assertEqual(o.stage, "BASELINE_REGISTRATION")
        self.assertEqual(bb.store.all(), ()); self.assertEqual(feature_records(rig), [])
        self.assertEqual(rig.claims.claim("CLAIM:REQ-1")["state"], "RELEASED")
    def test_with_resolver_installed_as_TEST_INSTRUMENTATION_full_path_registers_and_accepts(self):
        bb = baseline_binding(); rig = Rig(baseline=bb); p = package(); rig.issue(p)
        resolver = make_construction_authority_resolver(rig.claims)
        with mock.patch.object(baseline_store, "_governed_construction_authority", resolver):
            o = rig.pipe.run(p)
        self.assertTrue(o.accepted_ok, o.failures)
        rows = bb.store.all(); self.assertEqual(len(rows), 1); self.assertEqual(rows[0].feature_id, "mom3")
        self.assertIs(baseline_store._governed_construction_authority({}), False)     # patch scope ended
    def test_resolver_follows_journal_not_caller(self):
        rig = Rig(); p = package(); adm = rig.issue(p); res = make_construction_authority_resolver(rig.claims)
        v = {"content_key_composite": adm.subject_key, "request_id": "REQ-1"}
        self.assertFalse(res(v))                                      # order exists, no claim yet
        rig.claims.reserve(subject_key=adm.subject_key, request_id="REQ-1", order_id="ORD-1", lookup_outcome=LookupOutcome.ABSENT)
        self.assertTrue(res(v))
        self.assertFalse(res(dict(v, request_id="OTHER"))); self.assertFalse(res(dict(v, content_key_composite="x")))
        for junk in ({}, None, {"content_key_composite": 1}, "str"): self.assertFalse(res(junk))
        rig.claims.revoke_order("ORD-1", "r"); self.assertFalse(res(v))
    def test_resolver_false_after_consumption(self):
        rig = Rig(); p = package(); adm = rig.issue(p); res = make_construction_authority_resolver(rig.claims)
        rig.claims.reserve(subject_key=adm.subject_key, request_id="REQ-1", order_id="ORD-1", lookup_outcome=LookupOutcome.ABSENT)
        rig.claims.consume("CLAIM:REQ-1", "x"); self.assertFalse(res({"content_key_composite": adm.subject_key, "request_id": "REQ-1"}))

if __name__ == "__main__":
    unittest.main()
