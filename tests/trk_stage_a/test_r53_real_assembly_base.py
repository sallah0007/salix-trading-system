"""R53: the independent-BASE control through the SAME real assembly (not synthetic gateway rows): TWO features accepted by the SAME ClaimService/pipeline/journals, each published by `Composition.accept_and_publish` with the OWNING `StatusEmitter` (committed lifecycle record -> SIM_STATUS_FACT in a committed SimulationPublicationPath), real stored-value L2 recorded in the ONE shared Core, the Gateway fed from the committed projection/rows (`path.feed`), the durable final store, then actual FW (`Composition.deliver`) and ML (`Composition.deliver_ml` -> build_row) windows.
The affected feature (declared upstream, ancestry never declared) is denied for FW and ML before, between and after; its ancestry is never cleared. Candidate SIMULATION: separate Gateway objects per Composition (a path is bound to one feature journal), one shared Core. Not a provider, acceptance or gate."""
import unittest
from stage_a.errors import Refusal
from stage_a.gateway import contracts as G, durable_final_store as D
from stage_a.gateway.v038 import FinalResolutionIdentity as FI
from stage_a.storage.object_store import InMemoryObjectStore
from stage_a.coordination.object_store_journal import ObjectStoreJournal
from stage_a.tracker import composition as CO, sim_publication_path as SP
from stage_a.tracker.status_emitter import StatusEmitter
from stage_a.tracker.quant_intake_adapter import admit
from stage_a.composer import order_authority as OA
from stage_a.composer.build_gate import accept_build_start as abs_
from .fixtures import Rig, package, SIM_CONF, momentum_manifest
from .test_boundaries import T, I, _entry, R
from .test_r29_intake_order import issue, br, rec
from .test_r25_scheduler import core, ver
from .test_r24_core import NONE_
from .test_r37_sim_publication_path import SPEC, supplied
from .test_r37_stored_values import SER, H
from .test_r50_status_emitter import MAP, boundary, AUD
from .test_r38_composition import _g
from stage_a.gateway.contracts import SimulatedGateway
from .test_r24_core import adm, facts
from stage_a.core.tracker_core import TrackerCore
from stage_a.storage.authority_class import SIMULATION
def _gr(proj, c, raw):
    g = SimulatedGateway(T, proj, watermark=100, health_source=c, allow_shape_only_health=False, allow_simulation_status=True); g.final_store = D.DurableFinalResolutionStore(raw); return g
EM = lambda: dict(boundary_evidence=boundary(), context_known=True, audit_fields=AUD)
FA, FB = bytes(range(16, 32)), bytes(range(48, 64))
def code(f, *a, **k):
    try: f(*a, **k)
    except Refusal as e: return e.code
class Assembly(unittest.TestCase):
    def build(self, declare_base=True, base_raw=False, stored=True):
        rig = Rig(); c = core(); out = {}; raw = None; self.rig, self.raws, self.fks, self.pkgs = rig, {}, {}, {}
        if base_raw: adm(c, bar_identity="raw"); raw = c.obs_key(facts(bar_identity="raw"))                          # a persisted RAW observation the BASE derives from (recorded closure)
        for tag, cand, fid, rid, att, win, F in (("A", "cand-1", "mom3", "REQ-1", "ATT-1", 3, FA), ("B", "cand-2", "base7", "REQ-2", "ATT-2", 5, FB)):
            oid = OA.order_id_for(cand); pkg = package(momentum_manifest(feature_id=fid, window=win), order_id=oid, request_id=rid, attempt_id=att, package_id="PKG-" + rid); a = admit(pkg, accepted_fit_generations=rig.fits, conformance=SIM_CONF)
            issue(rig.claims, rec(CANDIDATE_IDENTITY=cand), subject_key=a.subject_key); abs_(rig.claims, oid, br(CANDIDATE_IDENTITY=cand)); fk = a.feature_key
            sj = ObjectStoreJournal(rig.store, "SIMPUB-%s-%s" % (fk.scope.instrument, tag), "w"); sj.acquire_epoch(); path = SP.SimulationPublicationPath(rig.store, rig.journals.journal(fk.namespace()), sj, SPEC)
            co = CO.Composition(pipeline=rig.pipe, journals=rig.journals, store=rig.store, core=c, path=path, gateway_factory=lambda proj, c=c, rw=self.raws.setdefault(tag, InMemoryObjectStore()): _gr(proj, c, rw), upstream={fk.key(): ("UP",)} if tag == "A" else ({fk.key(): (raw,)} if raw else {}))
            si = dict(bindings={"close": {"ref": "SRC/close", "hash": H(SER)}}, fetch=lambda ref: SER, series_hash=H)
            ver(c, "UP", version="1", at=9, age=50) if tag == "A" else None
            r = co.accept_and_publish(pkg, supplied(feature_id=F), None, sequence=1, now=10, max_age=50, stored_inputs=si if stored else None, l2_applicability=None if stored else CO.L2Applicability('SCOPE-REF-SUPPLIED', 'CONTRACT-REF-SUPPLIED', False), status_emitter=StatusEmitter(path, kind_to_token=MAP), emit=EM())
            self.assertEqual((tag, r.status), (tag, "PUBLISHED_SIMULATION" if stored else "PUBLISHED_SIMULATION_L2_NOT_PASS")); self.assertGreater(r.published_rows, 0)
            b = G.HealthBinding(F, fk.feature_version, I, I); c.associate_subject(fk.key(), b, "assoc-" + tag); self.fks[tag] = fk; out[tag] = (fk, co, r, b, _entry(fid=F, ver=fk.feature_version))
        self.assertNotEqual(out["A"][0].key(), out["B"][0].key()); (c.declare_ancestry_complete(out["B"][0].key(), "src-base") if declare_base else None)                                            # ONLY the BASE feature's own ancestry (supplied ref)
        return c, out
    def test_base_actually_delivers_to_fw_and_ml_through_the_real_assembly_while_the_affected_ancestry_stays_unknown(self):
        c, o = self.build(); fkA, coA, rA, bA, eA = o["A"]; fkB, coB, rB, bB, eB = o["B"]; kw = lambda b: dict(binding=b, now=12, ref=R("hl"), resolved_at=11, tables=T)
        ml = lambda co, rid, win, r, e, b, F, row: co.deliver_ml(rid, FI("ML", "DS-" + row, "XAUUSD", win), e, I, I, 3, 20, r, row_id=row, generation_ref=R("gen"), vintage_mode="ORIGINAL_AS_OBSERVED", omissions=NONE_, exclusion_reason=lambda x: ("ENUM", "REASON", "REQUIRED_DEPENDENCY_ABSENT"), **kw(b))
        self.assertEqual(code(coA.deliver, "fw-a1", FI("FW", "M-A", "XAUUSD", "W1"), eA, I, I, 3, 20, rA, **kw(bA)), "NON_DELIVERY")                                                    # BEFORE (FW)
        fw = coB.deliver("fw-b1", FI("FW", "M-B", "XAUUSD", "W1"), eB, I, I, 3, 20, rB, **kw(bB)); self.assertIsInstance(fw, G.Binding)                                                    # BASE -> FW, real committed rows
        ra = ml(coA, "ml-a1", "W1", rA, eA, bA, FA, "row-a"); self.assertFalse(ra.included)                                                                                                  # BETWEEN: affected ML window denied (explicit exclusion reason)
        rb = ml(coB, "ml-b1", "W1", rB, eB, bB, FB, "row-b"); self.assertTrue(rb.included); self.assertEqual(len(rb.bindings), 1)                                                            # BASE -> ML
        self.assertIsNot(fw, rb.bindings[0]); self.assertEqual(code(coA.deliver, "fw-a2", FI("FW", "M-A", "XAUUSD", "W2"), eA, I, I, 3, 20, rA, **kw(bA)), "NON_DELIVERY"); self.assertFalse(ml(coA, "ml-a2", "W2", rA, eA, bA, FA, "row-a2").included)   # AFTER
        self.assertTrue(c._ancestry_blocks(c._replay(), fkA.key())); self.assertFalse(c._ancestry_blocks(c._replay(), fkB.key())); self.assertEqual(c.recording_health(fkA.key(), fkA.feature_version, 12).local_state, "HEALTHY")
    def test_r52_stored_source_l2_failure_on_the_affected_feature_refuses_FW_and_excludes_ML_while_the_unrelated_BASE_still_delivers_to_both(self):
        """R52 (Manager 20:38): ONE assembly, real committed rows: the affected feature's stored source changes after acceptance, the all-segment maintenance pass RECORDS NOT_PASS, FW is refused and ML excluded for it (before and after the pass), and the UNRELATED BASE feature still delivers to FW and ML; the affected ancestry is still UNKNOWN. SIM/candidate only; no gate cleared."""
        c, o = self.build(); fkA, coA, rA, bA, eA = o["A"]; fkB, coB, rB, bB, eB = o["B"]; kw = lambda b: dict(binding=b, now=14, ref=R("hl"), resolved_at=13, tables=T)
        ml = lambda co, rid, win, r, e, b, F, row: co.deliver_ml(rid, FI("ML", "DS-" + row, "XAUUSD", win), e, I, I, 3, 20, r, row_id=row, generation_ref=R("gen"), vintage_mode="ORIGINAL_AS_OBSERVED", omissions=NONE_, exclusion_reason=lambda x: ("ENUM", "REASON", "ALL_SEGMENT_FAIL"), **kw(b))
        coA.register_stored_maintenance(rA); saved = list(SER)
        try:
            SER[-1] = SER[-1] + 1000                                                                                           # the stored source changes AFTER acceptance (only A is registered for maintenance)
            self.assertEqual([x[2] for x in coA.run_maintenance([(fkA.key(), "SCHEDULED")], now=13, max_age=50, max_items=4)], ["RECORDED_NOT_PASS"])
            self.assertEqual(code(coA.deliver, "fw-a9", FI("FW", "M-A9", "XAUUSD", "W9"), eA, I, I, 3, 20, rA, **kw(bA)), "NON_DELIVERY")        # FW refused for the affected feature
            ra = ml(coA, "ml-a9", "W9", rA, eA, bA, FA, "row-a9"); self.assertFalse(ra.included); self.assertEqual(ra.row_exclusion_reason, ("ENUM", "REASON", "ALL_SEGMENT_FAIL"))  # ML excluded with the explicit reason
            fw = coB.deliver("fw-b9", FI("FW", "M-B9", "XAUUSD", "W9"), eB, I, I, 3, 20, rB, **kw(bB)); self.assertIsInstance(fw, G.Binding)           # unrelated BASE -> FW (actual rows)
            rb = ml(coB, "ml-b9", "W9", rB, eB, bB, FB, "row-b9"); self.assertTrue(rb.included); self.assertEqual(len(rb.bindings), 1)               # unrelated BASE -> ML
            self.assertTrue(c._ancestry_blocks(c._replay(), fkA.key())); self.assertFalse(c._ancestry_blocks(c._replay(), fkB.key()))                # affected ancestry still UNKNOWN; BASE declared
        finally: SER[:] = saved
    def test_r52_control_without_the_source_change_the_same_pass_is_not_a_failure(self):
        c, o = self.build(); fkA, coA, rA, *_ = o["A"]; coA.register_stored_maintenance(rA)
        self.assertNotIn("RECORDED_NOT_PASS", [x[2] for x in coA.run_maintenance([(fkA.key(), "SCHEDULED")], now=13, max_age=50, max_items=4)])
    def test_control_the_BASE_is_denied_when_its_own_ancestry_was_never_declared_so_the_positive_is_not_vacuous(self):
        c, o = self.build(declare_base=False); fkB, coB, rB, bB, eB = o["B"]
        self.assertEqual(code(coB.deliver, "fw-x", FI("FW", "M-B", "XAUUSD", "WX"), eB, I, I, 3, 20, rB, binding=bB, now=12, ref=R("hl"), resolved_at=11, tables=T), "NON_DELIVERY")
class QuarantineRestorationRestart(unittest.TestCase):
    """R53: quarantine -> denial at FW AND ML -> restoration (clear_reason, reactivate over a RECONSTRUCTABLE recorded closure) -> earlier health does NOT survive -> maintenance trigger re-records L2 -> delivery returns; a restart (new TrackerCore over the SAME journal) reproduces the blocked state. Same objects as the assembly above."""
    def test_cycle(self):
        c, o = Assembly("test_control_the_BASE_is_denied_when_its_own_ancestry_was_never_declared_so_the_positive_is_not_vacuous").build(base_raw=True); fkB, coB, rB, bB, eB = o["B"]; k = fkB.key(); raw = list(c._replay()["ups"][k])[0]; c.declare_ancestry_complete(raw, "src-raw")        # the raw root declares its own (supplied) ancestry
        kw = dict(binding=bB, now=12, ref=R("hl"), resolved_at=11, tables=T)
        fw = lambda rid, w, now=12: coB.deliver(rid, FI("FW", "M-" + rid, "XAUUSD", w), eB, I, I, 3, 20, rB, **dict(kw, now=now))
        ml = lambda rid, w, now=12: coB.deliver_ml(rid, FI("ML", "D-" + rid, "XAUUSD", w), eB, I, I, 3, 20, rB, row_id="r-" + rid, generation_ref=R("gen"), vintage_mode="ORIGINAL_AS_OBSERVED", omissions=NONE_, exclusion_reason=lambda x: ("ENUM", "REASON", "QUARANTINED"), **dict(kw, now=now))
        b0 = fw("f0", "W0"); self.assertIsInstance(b0, G.Binding); m0 = ml("m0", "W0"); self.assertTrue(m0.included)                                                          # healthy baseline
        c.quarantine(k, "R"); self.assertEqual(code(fw, "f1", "W1"), "NON_DELIVERY"); self.assertFalse(ml("m1", "W1").included)                              # QUARANTINED: FW and ML new windows denied
        self.assertEqual(fw("f0", "W0"), b0); self.assertEqual(ml("m0", "W0").bindings, m0.bindings); self.assertEqual(coB.gateway.final_store.identity_of("FW", "f0"), FI("FW", "M-f0", "XAUUSD", "W0")); self.assertEqual(coB.gateway.final_store.identity_of("ML", "m0"), FI("ML", "D-m0", "XAUUSD", "W0"))                                                                                                       # an already-final window outcome is immutable (not retroactively rewritten)
        c2 = TrackerCore(c._j, simulation=True); self.assertTrue(c2._blocked(c2._replay(), k))                                                                # RESTART over the same journal: still blocked
        c.clear_reason(k, "R", "cert", "maker"); self.assertEqual(code(fw, "f2", "W2"), "NON_DELIVERY")                                                      # reason cleared but not reactivated: still denied
        c.reactivate(k); self.assertEqual(c.recording_health(k, fkB.feature_version, 12).state, "UNKNOWN"); self.assertEqual(code(fw, "f3", "W3"), "NON_DELIVERY")   # earlier evidence does not survive reactivation
        coB.register_stored_maintenance(rB); o2 = coB.run_maintenance([(k, "QUARANTINE_CLEARED")], now=13, max_age=50, max_items=4); self.assertEqual([x[2] for x in o2], ["VERIFIED"])
        kw["resolved_at"] = 13; self.assertIsInstance(fw("f4", "W4", 14), G.Binding); self.assertTrue(ml("m4", "W4", 14).included)                          # restored through the trigger-driven re-verification: FW and ML deliver again
        c3 = TrackerCore(c._j, simulation=True); self.assertFalse(c3._blocked(c3._replay(), k))                                                                # restart after restoration: not blocked
if __name__ == "__main__": unittest.main()
class OwningSubjectCorrelation(unittest.TestCase):
    """R54: deliver/deliver_ml select Core health from the result's feature key; the result must be THIS Composition's own publication for that subject and the entry/binding must name that subject."""
    def test_foreign_or_mutated_results_and_mismatched_entry_binding_are_refused_before_any_health_is_read_and_the_genuine_call_delivers(self):
        import copy, dataclasses
        c, o = Assembly("test_control_the_BASE_is_denied_when_its_own_ancestry_was_never_declared_so_the_positive_is_not_vacuous").build(); fkA, coA, rA, bA, eA = o["A"]; fkB, coB, rB, bB, eB = o["B"]
        kw = dict(now=12, ref=R("hl"), resolved_at=11, tables=T); n = lambda: len(c._j.read_all()) if hasattr(c._j, "read_all") else None
        fwd = lambda co, r, e, b, rid: code(co.deliver, rid, FI("FW", "M-" + rid, "XAUUSD", "W-" + rid), e, I, I, 3, 20, r, binding=b, **kw)
        self.assertEqual(fwd(coB, rA, eB, bB, "x1"), "COMPOSITION_RESULT_NOT_THIS_PUBLICATION")                                          # another subject's result of the SAME assembly family
        mut = copy.copy(rB); mut.feature_key = fkA; self.assertEqual(fwd(coB, mut, eA, bA, "x2"), "COMPOSITION_RESULT_NOT_THIS_PUBLICATION")      # a mutated copy selecting A's health
        self.assertEqual(fwd(coA, rB, eA, bA, "x3"), "COMPOSITION_RESULT_NOT_THIS_PUBLICATION")                                          # B's REAL result presented to A's Composition with A's entry/binding
        self.assertEqual(fwd(coB, rB, eA, bB, "x4"), "COMPOSITION_ENTRY_BINDING_SUBJECT_MISMATCH")                                       # B's result, B's binding, A's entry
        self.assertEqual(fwd(coB, rB, eB, bA, "x5"), "COMPOSITION_ENTRY_BINDING_SUBJECT_MISMATCH")                                       # B's result, B's entry, A's binding
        self.assertEqual(fwd(coB, rB, dataclasses.replace(eB, feature_version="9"), bB, "x6"), "COMPOSITION_ENTRY_BINDING_SUBJECT_MISMATCH")
        ml = lambda co, r, e, b, rid: code(co.deliver_ml, rid, FI("ML", "D-" + rid, "XAUUSD", "W-" + rid), e, I, I, 3, 20, r, binding=b, row_id=rid, generation_ref=R("gen"), vintage_mode="ORIGINAL_AS_OBSERVED", omissions=NONE_, exclusion_reason=lambda x: None, **kw)
        self.assertEqual(ml(coB, rA, eB, bB, "y1"), "COMPOSITION_RESULT_NOT_THIS_PUBLICATION"); self.assertEqual(ml(coB, rB, eA, bB, "y2"), "COMPOSITION_ENTRY_BINDING_SUBJECT_MISMATCH")
        self.assertIsNone(fwd(coB, rB, eB, bB, "ok1")); self.assertIsNone(ml(coB, rB, eB, bB, "ok2"))                                    # genuine control: the owning subject/entry/binding delivers (FW and ML)
        self.assertEqual(coB.gateway.final_store.identity_of("FW", "x1"), None)                                                           # the refusals reached no window store

class ColdRecovery(unittest.TestCase):
    """R54: restart of the OWNING connection, not just Core._blocked: a new Core over the same journal, a rebuilt publication path (new writer epoch), a NEW Composition + Gateway over the same durable final store, then FW and ML again."""
    def _setup(self):
        a = Assembly("test_control_the_BASE_is_denied_when_its_own_ancestry_was_never_declared_so_the_positive_is_not_vacuous"); c, o = a.build(base_raw=True); fkB, coB, rB, bB, eB = o["B"]; k = fkB.key()
        raw = list(c._replay()["ups"][k])[0]; c.declare_ancestry_complete(raw, "src-raw")
        kw = dict(now=12, ref=R("hl"), resolved_at=11, tables=T)
        fw = lambda co, r, rid, w: co.deliver(rid, FI("FW", "M-" + rid, "XAUUSD", w), eB, I, I, 3, 20, r, binding=bB, **kw)
        ml = lambda co, r, rid, w: co.deliver_ml(rid, FI("ML", "D-" + rid, "XAUUSD", w), eB, I, I, 3, 20, r, binding=bB, row_id="r-" + rid, generation_ref=R("gen"), vintage_mode="ORIGINAL_AS_OBSERVED", omissions=NONE_, exclusion_reason=lambda x: ("ENUM", "REASON", "ALL_SEGMENT_FAIL"), **kw)
        return a, c, fkB, coB, rB, bB, eB, fw, ml
    def _restart(self, a, c, fkB, rB):
        from stage_a.core.tracker_core import TrackerCore
        c2 = TrackerCore(c._j, simulation=True); fj = a.rig.journals.journal(fkB.namespace()); sj = ObjectStoreJournal(a.rig.store, "SIMPUB-%s-B" % fkB.scope.instrument, "w2"); sj.acquire_epoch()
        path2 = SP.SimulationPublicationPath(a.rig.store, fj, sj, SPEC); co2 = CO.Composition(pipeline=a.rig.pipe, journals=a.rig.journals, store=a.rig.store, core=c2, path=path2, gateway_factory=lambda proj: _gr(proj, c2, a.raws["B"]))
        return c2, co2
    def test_restart_retains_exact_final_outcomes_and_identities_and_delivers_new_windows_for_FW_and_ML(self):
        a, c, fkB, coB, rB, bB, eB, fw, ml = self._setup(); f0 = fw(coB, rB, "f0", "W0"); m0 = ml(coB, rB, "m0", "W0"); self.assertIsInstance(f0, G.Binding); self.assertTrue(m0.included)
        c2, co2 = self._restart(a, c, fkB, rB); self.assertEqual(code(co2.deliver, "z", FI("FW", "M", "XAUUSD", "W"), eB, I, I, 3, 20, rB, binding=bB, now=12, ref=R("hl"), resolved_at=11, tables=T), "COMPOSITION_NOT_PUBLISHED")       # nothing survives in memory; the OLD result is not accepted
        r2 = co2.recover_publication(fkB); self.assertEqual((r2.status, r2.published_rows > 0), ("RECOVERED_PUBLISHED_SIMULATION", True)); self.assertEqual(code(co2.deliver, "z", FI("FW", "M", "XAUUSD", "W"), eB, I, I, 3, 20, rB, binding=bB, now=12, ref=R("hl"), resolved_at=11, tables=T), "COMPOSITION_RESULT_NOT_THIS_PUBLICATION")
        self.assertEqual(co2.gateway.final_store.identity_of("FW", "f0"), FI("FW", "M-f0", "XAUUSD", "W0")); self.assertEqual(co2.gateway.final_store.identity_of("ML", "m0"), FI("ML", "D-m0", "XAUUSD", "W0"))
        f0b = fw(co2, r2, "f0", "W0"); self.assertEqual((f0b.request_id, f0b.delivered_feature_hash), (f0.request_id, f0.delivered_feature_hash)); m0b = ml(co2, r2, "m0", "W0"); self.assertTrue(m0b.included); self.assertEqual([b.delivered_feature_hash for b in m0b.bindings], [b.delivered_feature_hash for b in m0.bindings])
        self.assertIsInstance(fw(co2, r2, "f1", "W1"), G.Binding); self.assertTrue(ml(co2, r2, "m1", "W1").included)                                                                                             # new windows after restart
    def test_all_segment_failure_after_restart_refuses_FW_and_excludes_ML_and_foreign_state_is_not_adopted(self):
        a, c, fkB, coB, rB, bB, eB, fw, ml = self._setup(); res = {"SRC/close": SER}; si = dict(bindings={"close": {"ref": "SRC/close", "hash": H(SER)}}, fetch=lambda ref: res.get(ref), series_hash=H)
        from stage_a.tracker import stored_values as SV
        SER_B = [x + 1 for x in SER]; res["SRC/close-b"] = SER_B; SV.persist_stored_values(journal=a.rig.journals.journal(fkB.namespace()), store=a.rig.store, feature_key=fkB, bindings={"close": {"ref": "SRC/close-b", "hash": H(SER_B)}}, fetch=si["fetch"], series_hash=H)
        c2, co2 = self._restart(a, c, fkB, rB); r2 = co2.recover_publication(fkB, stored_inputs=si); self.assertIn(("stored_basis", "RESTORED_FROM_STORED_SEGMENTS", "VERIFIED_STORED_EQUALS_RECOMPUTED"), r2.steps)
        self.assertIsInstance(fw(co2, r2, "g0", "W0"), G.Binding); co2.register_stored_maintenance(r2); res["SRC/close-b"] = SER_B[:-1] + [-1]                                                                  # a stored segment's source changes after restart
        o = co2.run_maintenance([(fkB.key(), "SCHEDULED")], now=13, max_age=50, max_items=4); self.assertEqual([x[2] for x in o], ["RECORDED_NOT_PASS"])
        kw2 = dict(binding=bB, now=14, ref=R("hl"), resolved_at=13, tables=T); self.assertEqual(code(co2.deliver, "g1", FI("FW", "M-g1", "XAUUSD", "W1"), eB, I, I, 3, 20, r2, **kw2), "NON_DELIVERY")                  # FW refused
        row = co2.deliver_ml("g2", FI("ML", "D-g2", "XAUUSD", "W1"), eB, I, I, 3, 20, r2, row_id="r-g2", generation_ref=R("gen"), vintage_mode="ORIGINAL_AS_OBSERVED", omissions=NONE_, exclusion_reason=lambda x: ("ENUM", "REASON", "ALL_SEGMENT_FAIL"), **kw2)
        self.assertFalse(row.included); self.assertEqual(row.row_exclusion_reason, ("ENUM", "REASON", "ALL_SEGMENT_FAIL"))                                                                                 # ML excluded with the explicit reason
        self.assertEqual(code(co2.recover_publication, a.fks["A"]), "COMPOSITION_RECOVERY_NO_COMMITTED_STATUS")                                                                                               # another subject's accepted record without a committed status in THIS path is not adopted
    def test_recovery_refusals_advanced_head_unaccepted_subject_no_stored_segments_and_binding_version(self):
        import dataclasses
        from stage_a.tracker import publication as PUB
        a, c, fkB, coB, rB, bB, eB, fw, ml = self._setup(); c2, co2 = self._restart(a, c, fkB, rB)
        self.assertEqual(code(co2.recover_publication, dataclasses.replace(fkB, feature_id="never-accepted"))[:34], "COMPOSITION_RECOVERY_NO_ACCEPTED_R")
        r2 = co2.recover_publication(fkB, stored_inputs=dict(fetch=lambda ref: None, series_hash=H)); self.assertIn("stored_basis", [x[0] for x in r2.steps])                                                          # segments exist: basis restored (verification itself may be UNAVAILABLE)
        PUB.withdraw(a.rig.journals.journal(fkB.namespace()), fkB, "x"); c3, co3 = self._restart(a, c, fkB, rB); self.assertEqual(code(co3.recover_publication, fkB), "COMPOSITION_RECOVERY_SOURCE_HEAD_ADVANCED")        # owning HEAD advanced (withdrawn): not recovered as published
        self.assertEqual(code(co2.deliver, "q", FI("FW", "M-q", "XAUUSD", "WQ"), eB, I, I, 3, 20, r2, binding=dataclasses.replace(bB, feature_version="9"), now=12, ref=R("hl"), resolved_at=11, tables=T), "COMPOSITION_ENTRY_BINDING_SUBJECT_MISMATCH")
    def test_recovery_without_stored_segments_does_not_restore_a_maintenance_basis(self):
        a = Assembly("test_control_the_BASE_is_denied_when_its_own_ancestry_was_never_declared_so_the_positive_is_not_vacuous"); c, o = a.build(stored=False); fkB, coB, rB, bB, eB = o["B"]
        c2, co2 = ColdRecovery("test_restart_retains_exact_final_outcomes_and_identities_and_delivers_new_windows_for_FW_and_ML")._restart(a, c, fkB, rB); r2 = co2.recover_publication(fkB, stored_inputs=dict(fetch=lambda ref: None, series_hash=H))
        self.assertIn(("stored_basis", "NOT_RESTORED", "STORED_VALUES_ABSENT"), r2.steps); self.assertEqual(code(co2.register_stored_maintenance, r2), "COMPOSITION_MAINTENANCE_NOT_PUBLISHED")
