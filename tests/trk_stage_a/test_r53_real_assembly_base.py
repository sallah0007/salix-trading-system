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
from .test_r24_core import adm, facts
from stage_a.core.tracker_core import TrackerCore
from stage_a.storage.authority_class import SIMULATION
EM = lambda: dict(boundary_evidence=boundary(), context_known=True, audit_fields=AUD)
FA, FB = bytes(range(16, 32)), bytes(range(48, 64))
def code(f, *a, **k):
    try: f(*a, **k)
    except Refusal as e: return e.code
class Assembly(unittest.TestCase):
    def build(self, declare_base=True, base_raw=False):
        rig = Rig(); c = core(); out = {}; raw = None
        if base_raw: adm(c, bar_identity="raw"); raw = c.obs_key(facts(bar_identity="raw"))                          # a persisted RAW observation the BASE derives from (recorded closure)
        for tag, cand, fid, rid, att, win, F in (("A", "cand-1", "mom3", "REQ-1", "ATT-1", 3, FA), ("B", "cand-2", "base7", "REQ-2", "ATT-2", 5, FB)):
            oid = OA.order_id_for(cand); pkg = package(momentum_manifest(feature_id=fid, window=win), order_id=oid, request_id=rid, attempt_id=att, package_id="PKG-" + rid); a = admit(pkg, accepted_fit_generations=rig.fits, conformance=SIM_CONF)
            issue(rig.claims, rec(CANDIDATE_IDENTITY=cand), subject_key=a.subject_key); abs_(rig.claims, oid, br(CANDIDATE_IDENTITY=cand)); fk = a.feature_key
            sj = ObjectStoreJournal(rig.store, "SIMPUB-%s-%s" % (fk.scope.instrument, tag), "w"); sj.acquire_epoch(); path = SP.SimulationPublicationPath(rig.store, rig.journals.journal(fk.namespace()), sj, SPEC)
            co = CO.Composition(pipeline=rig.pipe, journals=rig.journals, store=rig.store, core=c, path=path, gateway_factory=lambda proj, c=c: _g(proj, c), upstream={fk.key(): ("UP",)} if tag == "A" else ({fk.key(): (raw,)} if raw else {}))
            si = dict(bindings={"close": {"ref": "SRC/close", "hash": H(SER)}}, fetch=lambda ref: SER, series_hash=H)
            ver(c, "UP", version="1", at=9, age=50) if tag == "A" else None
            r = co.accept_and_publish(pkg, supplied(feature_id=F), None, sequence=1, now=10, max_age=50, stored_inputs=si, status_emitter=StatusEmitter(path, kind_to_token=MAP), emit=EM())
            self.assertEqual((tag, r.status, r.stored_values["l2"]), (tag, "PUBLISHED_SIMULATION", "PASS")); self.assertGreater(r.published_rows, 0)
            b = G.HealthBinding(F, fk.feature_version, I, I); c.associate_subject(fk.key(), b, "assoc-" + tag); out[tag] = (fk, co, r, b, _entry(fid=F, ver=fk.feature_version))
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
        self.assertIsInstance(fw("f0", "W0"), G.Binding); self.assertTrue(ml("m0", "W0").included)                                                          # healthy baseline
        c.quarantine(k, "R"); self.assertEqual(code(fw, "f1", "W1"), "NON_DELIVERY"); self.assertFalse(ml("m1", "W1").included)                              # QUARANTINED: FW and ML new windows denied
        self.assertEqual(code(fw, "f0", "W0"), None)                                                                                                       # an already-final window outcome is immutable (not retroactively rewritten)
        c2 = TrackerCore(c._j, simulation=True); self.assertTrue(c2._blocked(c2._replay(), k))                                                                # RESTART over the same journal: still blocked
        c.clear_reason(k, "R", "cert", "maker"); self.assertEqual(code(fw, "f2", "W2"), "NON_DELIVERY")                                                      # reason cleared but not reactivated: still denied
        c.reactivate(k); self.assertEqual(c.recording_health(k, fkB.feature_version, 12).state, "UNKNOWN"); self.assertEqual(code(fw, "f3", "W3"), "NON_DELIVERY")   # earlier evidence does not survive reactivation
        coB.register_stored_maintenance(rB); o2 = coB.run_maintenance([(k, "QUARANTINE_CLEARED")], now=13, max_age=50, max_items=4); self.assertEqual([x[2] for x in o2], ["VERIFIED"])
        kw["resolved_at"] = 13; self.assertIsInstance(fw("f4", "W4", 14), G.Binding); self.assertTrue(ml("m4", "W4", 14).included)                          # restored through the trigger-driven re-verification: FW and ML deliver again
        c3 = TrackerCore(c._j, simulation=True); self.assertFalse(c3._blocked(c3._replay(), k))                                                                # restart after restoration: not blocked
if __name__ == "__main__": unittest.main()
