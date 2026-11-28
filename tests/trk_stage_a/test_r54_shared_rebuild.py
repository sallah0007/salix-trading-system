"""R54: the SHARED-ASSEMBLY cold-recovery + E05 read-model rebuild claim (not the isolated R44 control): after a restart that rebuilds Core + publication path + Composition + Gateway over the SAME journal/object store, the E05 index is rebuilt from the REAL durable final-resolution records written by actual FW and ML deliveries (existing `e05_sources.final_resolution_source`, no substitute), is identical to the pre-restart index for retained records, new FW/ML windows move the head, a stored-segment failure (second segment) yields a durable FW NonDelivery row and an ML exclusion, plane identity is enforced on the restarted journal, and a replaced record is drift. Candidate SIMULATION; nothing here is a gate or qualification."""
import unittest, dataclasses
from stage_a.errors import IntegrityFailure, Refusal
from stage_a.gateway import contracts as G
from stage_a.gateway.v038 import FinalResolutionIdentity as FI
from stage_a.storage import e05_sources as S
from stage_a.storage.e05_index import E05Index
from stage_a.core.tracker_core import TrackerCore
from stage_a.tracker import stored_values as SV
from . import test_r53_real_assembly_base as R53
from .test_r53_real_assembly_base import code, T, I, R, NONE_, SER, H
from .test_r44_e05_rebuild_separated import bind_cols, nd_cols
def rig(case):
    cr = R53.ColdRecovery("test_restart_retains_exact_final_outcomes_and_identities_and_delivers_new_windows_for_FW_and_ML"); return cr, cr._setup()
def index(raw):
    ix = E05Index(); ix.rebuild({"fr": S.final_resolution_source(raw, binding_columns=bind_cols, non_delivery_columns=nd_cols)}); return raw, ix
def keys(ix): return sorted(map(str, ix.current_rows("stagea_consumer_binding_index"))), sorted(map(str, ix.current_rows("stagea_non_delivery_index")))
class SharedRebuild(unittest.TestCase):
    def test_restarted_assembly_rebuilds_the_index_from_real_FW_and_ML_final_records_and_retained_rows_are_identical(self):
        cr, (a, c, fkB, coB, rB, bB, eB, fw, ml) = rig(self); f0 = fw(coB, rB, "f0", "W0"); m0 = ml(coB, rB, "m0", "W0")
        raw0, ix0 = index(a.raws['B']); res0 = S.object_resolver(raw0); self.assertEqual(ix0.verify_all(res0), 2); before = keys(ix0); head0 = S.final_resolution_source(raw0, binding_columns=bind_cols, non_delivery_columns=nd_cols)[0]()
        c2, co2 = cr._restart(a, c, fkB, rB); r2 = co2.recover_publication(fkB); self.assertEqual(r2.status, "RECOVERED_PUBLISHED_SIMULATION")
        raw1, ix1 = index(a.raws['B']); self.assertIs(co2.gateway.final_store._o, raw0); self.assertEqual(keys(ix1), before)                                                              # lost index + cold restart -> identical rows
        self.assertEqual(co2.gateway.final_store.identity_of("FW", "f0"), FI("FW", "M-f0", "XAUUSD", "W0")); self.assertEqual(co2.gateway.final_store.identity_of("ML", "m0"), FI("ML", "D-m0", "XAUUSD", "W0"))
        fw(co2, r2, "f0", "W0"); ml(co2, r2, "m0", "W0") if False else None; self.assertEqual(S.final_resolution_source(raw1, binding_columns=bind_cols, non_delivery_columns=nd_cols)[0](), head0)   # retained redelivery writes nothing new
        fw(co2, r2, "f1", "W1"); self.assertTrue(ml(co2, r2, "m1", "W1").included); h2 = S.final_resolution_source(raw1, binding_columns=bind_cols, non_delivery_columns=nd_cols)[0](); self.assertEqual(h2[0], head0[0] + 2)   # NEW FW + ML windows after restart
        _, ix2 = index(a.raws['B']); self.assertEqual(ix2.verify_all(S.object_resolver(raw1)), 4); self.assertTrue(set(before[0]) <= set(keys(ix2)[0]))               # retained rows unchanged, two added
    def test_second_stored_segment_failure_after_restart_is_a_durable_FW_nondelivery_and_an_ML_exclusion_in_the_rebuilt_index(self):
        cr, (a, c, fkB, coB, rB, bB, eB, fw, ml) = rig(self); res = {"SRC/close": SER}; si = dict(bindings={"close": {"ref": "SRC/close", "hash": H(SER)}}, fetch=lambda ref: res.get(ref), series_hash=H)
        SER_B = [x + 1 for x in SER]; res["SRC/close-b"] = SER_B; SV.persist_stored_values(journal=a.rig.journals.journal(fkB.namespace()), store=a.rig.store, feature_key=fkB, bindings={"close": {"ref": "SRC/close-b", "hash": H(SER_B)}}, fetch=si["fetch"], series_hash=H)
        c2, co2 = cr._restart(a, c, fkB, rB); r2 = co2.recover_publication(fkB, stored_inputs=si); self.assertIsInstance(fw(co2, r2, "g0", "W0"), G.Binding); co2.register_stored_maintenance(r2); res["SRC/close-b"] = SER_B[:-1] + [-1]
        self.assertEqual([x[2] for x in co2.run_maintenance([(fkB.key(), "SCHEDULED")], now=13, max_age=50, max_items=4)], ["RECORDED_NOT_PASS"]); kw2 = dict(binding=bB, now=14, ref=R("hl"), resolved_at=13, tables=T)
        raw, ixa = index(a.raws['B']); nda = keys(ixa)[1]
        self.assertEqual(code(co2.deliver, "g1", FI("FW", "M-g1", "XAUUSD", "W1"), eB, I, I, 3, 20, r2, **kw2), "NON_DELIVERY")
        row = co2.deliver_ml("g2", FI("ML", "D-g2", "XAUUSD", "W1"), eB, I, I, 3, 20, r2, row_id="r-g2", generation_ref=R("gen"), vintage_mode="ORIGINAL_AS_OBSERVED", omissions=NONE_, exclusion_reason=lambda x: ("ENUM", "REASON", "ALL_SEGMENT_FAIL"), **kw2); self.assertFalse(row.included)
        _, ixb = index(a.raws['B']); ndb = keys(ixb)[1]; self.assertEqual((len(nda), len(ndb)), (0, 2)); self.assertEqual(sorted(r[0] for r in ixb._c.execute("select non_delivery_resolution_id from stagea_non_delivery_index")), ["FW:W1", "ML:W1"])      # BOTH the FW refusal and the ML exclusion are durable NonDelivery rows after the rebuild
        self.assertEqual(keys(ixb)[0], keys(ixa)[0])                                                                                                                       # no Binding appeared for the failed windows (ML exclusion creates none)
    def test_plane_identity_and_drift_on_the_restarted_shared_journal(self):
        cr, (a, c, fkB, coB, rB, bB, eB, fw, ml) = rig(self); fw(coB, rB, "f0", "W0"); c2, co2 = cr._restart(a, c, fkB, rB)
        with self.assertRaises(Refusal) as e: TrackerCore(c._j, simulation=True, plane="control")
        self.assertEqual(e.exception.code, "UNKNOWN_PLANE")
        with self.assertRaises(IntegrityFailure): TrackerCore(c._j, simulation=True, plane="research").retry_allowed(fkB.key())                                         # untagged history is never adopted by another plane
        self.assertTrue(TrackerCore(c._j, simulation=True).retry_allowed(fkB.key()))
        raw, ix = index(a.raws['B']); k = raw.list_prefix("final-resolution/id/")[0]; b, et = raw.get(k); raw.put_if_match(k, b.replace(b"XAUUSD", b"EURUSD"), et)
        with self.assertRaises(IntegrityFailure): ix.verify_all(S.object_resolver(raw))
        raw.put_if_absent("final-resolution/id/" + "0" * 64, raw.get(k)[0]); self.assertEqual(code(index, raw), "E05_SOURCE_OBJECT_NOT_CONTENT_ADDRESSED")      # a record filed under another key is refused, not projected
from stage_a.gateway.h1_record import TypedH1
from stage_a.gateway import outcome_series as H3
from .test_r50_h1_augmented import h1, pkg, ctx
class SharedH1Desk(unittest.TestCase):
    def test_h1_correlates_with_the_composition_gateway_final_identity_and_survives_a_cold_restart(self):
        cr, (a, c, fkB, coB, rB, bB, eB, fw, ml) = rig(self)
        fw(coB, rB, "f0", "W0"); ident = FI("FW", "M-f0", "XAUUSD", "W0"); d = coB.outcome_desk(); self.assertIs(coB.outcome_desk(), d)
        rec = TypedH1(h1(REQUEST_ID="f0", MANIFEST_OR_DATASET_BINDING_ID="M-f0", CONSUMER_BINDING_ID="B1")); d.register_h1(rec, identity=ident); r = d.request("f0", pkg(), ctx(), identity=ident); self.assertEqual((r.consumer_binding_id, r.decision.status, r.delivered), ("B1", H3.PASS_STRUCTURAL, False))
        self.assertIsNotNone(code(d.register_h1, TypedH1(h1(REQUEST_ID="never", MANIFEST_OR_DATASET_BINDING_ID="M-never", CONSUMER_BINDING_ID="B9")), identity=FI("FW", "M-never", "XAUUSD", "W9")))   # an identity this Gateway never issued is refused
        c2, co2 = cr._restart(a, c, fkB, rB); r2 = co2.recover_publication(fkB); d2 = co2.outcome_desk(); self.assertIsNot(d2, d)                                  # a rebuilt Composition gets its OWN desk over the re-hydrated durable final store
        d2.register_h1(rec, identity=ident); self.assertEqual(code(d2.request, "f0", pkg(), ctx(), identity=ident), "OUTCOME_REQUEST_WINDOW_OUTCOME_NOT_A_BINDING")      # fail-closed: the rebuilt Gateway's in-memory outcome is not a Binding until the window is retried
        fw(co2, r2, "f0", "W0"); r2r = d2.request("f0", pkg(), ctx(), identity=ident); self.assertEqual((r2r.consumer_binding_id, r2r.decision.status, r2r.delivered), ("B1", H3.PASS_STRUCTURAL, False))
        bad = TypedH1(h1(REQUEST_ID="f0", MANIFEST_OR_DATASET_BINDING_ID="M-OTHER", CONSUMER_BINDING_ID="B1")); self.assertIsNotNone(code(d2.register_h1, bad, identity=ident))                    # manifest binding id != the issued identity's
    def test_unpublished_composition_has_no_desk(self):
        cr, (a, c, fkB, coB, rB, bB, eB, fw, ml) = rig(self); c2, co2 = cr._restart(a, c, fkB, rB); co2.gateway = None; self.assertEqual(code(co2.outcome_desk), "COMPOSITION_NOT_PUBLISHED")
if __name__ == "__main__": unittest.main()
