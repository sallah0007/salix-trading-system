"""R53: the per-ROW route end to end on the REAL assembly (SIMULATION): CommittedRowChain -> independent row-step verification (+registry/invariant stages) -> epoch-fenced RowAcceptor -> RowPublication (derived SIM_STATUS_FACT) -> Composition.recover_publication -> Core health -> Gateway -> BOTH FW and ML.
Legacy probe/materializer paths untouched. Candidate: SIM codec/clock/commit-point/mapping/profile, none admitted; clears no gate/hold."""
import unittest, json
from stage_a.errors import Refusal
from stage_a.gateway.contracts import SimulatedGateway
from stage_a.gateway import durable_final_store as D
from stage_a.gateway import contracts as G
from stage_a.gateway.v038 import FinalResolutionIdentity as FI
from stage_a.tracker import row_acceptance as RA, row_publication as RP, accepted_manifest as AM
from stage_a.tracker.materialization import row_store as RS
from stage_a.tracker.materialization.state_rows import StateRowBuilder
from . import test_r53_real_assembly_base as AB
FA, FB, code = AB.FA, AB.FB, AB.code
from .test_boundaries import T as GT, I, _entry, R
from .test_r24_core import NONE_
from .test_r53_row_acceptance import T, FX, CP, Time, kw as rkw, acc, SCHEMA, enc, dec, step_fn, H as RH
from tests.trk_stage_a.test_r53_row_acceptance import R as _R

from stage_a.schema.encoding import CodeTables
GTAB = CodeTables(enums=dict(GT.enums, **{k: v for k, v in T.enums.items()}), ref_types=dict(T.ref_types, R=max(T.ref_types.values()) + 1), admitted_source=None)   # SIM merge: candidate row tables + the Gateway's test enums; code values UNADMITTED
def _gw(proj, c, raw):
    g = SimulatedGateway(GTAB, proj, watermark=100, health_source=c, allow_shape_only_health=False, allow_simulation_status=True); g.final_store = D.DurableFinalResolutionStore(raw); return g

class RowRoute(unittest.TestCase):
    def setUp(self):
        a = AB.Assembly("build"); self.a = a; self.c, o = a.build(); self.o = o; rig = a.rig; self.rows = RS.PendingRowStore(rig.store, T); self.acc = RA.RowAcceptor(rig.journals, self.rows, T, Time(20), CP()); self.chain = {}
        for tag, F in (("A", FA), ("B", FB)):
            fk = o[tag][0]; mh = AM.read_accepted_manifest(rig.journals.journal(fk.namespace()), rig.store, fk).manifest_hash
            fixed = dict(FX, feature_id=F, feature_version=fk.feature_version, quant_manifest_hash=bytes.fromhex(mh), instrument_id=I, timeframe_id=I, materialization_version="mrow")
            ch = RS.CommittedRowChain(StateRowBuilder(SCHEMA, T, enc, dec, fixed), self.rows); out, ph = [], None
            for i, x in enumerate([1.0, 2.0, 4.0]):
                row, rc = ch.step(step_fn, ph, {"x": x}, **dict(rkw(i, origin=ph is None), event_time=30 + i)); out.append((row, rc)); ph = rc.row_hash
            self.chain[tag] = out
            o[tag][1]._gf = lambda proj, c=self.c, rw=a.raws[tag]: _gw(proj, c, rw)       # the Gateway must encode with the SAME (candidate) code tables as the row store: the row carries a CANONICAL_TRANSITION_REF
    def publish(self, tag, i):
        fk, co = self.o[tag][0], self.o[tag][1]; h = self.chain[tag][i][1].row_hash; acc(self.acc, h)
        return RP.RowPublication(co._path, self.a.rig.journals, self.rows, T, self.a.rig.store).publish(fk, h, "SIM_CUR", sequence=i + 1, visible_at=50, published_projection_hash=RH, data_vintage_mode="ORIGINAL_AS_OBSERVED", source_or_causal_policy_ref=R("pol"))
    def both(self, tag, res, step, ev, n):
        import dataclasses; fk, co, r0, b, e = self.o[tag]; e = dataclasses.replace(e, expected_projection=self.chain[tag][0][0].published_projection_name); k = dict(binding=b, now=12, ref=R("hl"), resolved_at=11, tables=GTAB)
        fw = lambda: co.deliver("fw-" + n, FI("FW", "M-" + n, "XAUUSD", "W" + n), e, I, I, step, 60, res, **k)
        ml = co.deliver_ml("ml-" + n, FI("ML", "D-" + n, "XAUUSD", "W" + n), e, I, I, step, 60, res, row_id="row-" + n, generation_ref=R("gen"), vintage_mode="ORIGINAL_AS_OBSERVED", omissions=NONE_, exclusion_reason=lambda x: ("ENUM", "REASON", "REQUIRED_DEPENDENCY_ABSENT"), **k)
        return fw, ml
    def test_accepted_rows_publish_recover_and_deliver_to_both_FW_and_ML_and_unpublished_windows_are_not_delivered(self):
        self.publish("B", 0); self.publish("B", 1); co = self.o["B"][1]; res = co.recover_publication(self.o["B"][0]); self.assertEqual(res.status, "RECOVERED_PUBLISHED_SIMULATION")
        for step, n in ((0, "0"), (1, "1")):
            fw, ml = self.both("B", res, step, 30 + step, n); self.assertIsInstance(fw(), G.Binding); self.assertTrue(ml.included)                  # PER-ROW windows (the 8th argument is the FENCE: rows are visible_at 50 <= 60)
        self.assertEqual(code(self.both("B", res, 2, 32, "2")[0]), "NON_DELIVERY")                                                                   # row 2: not accepted, not published
    def test_accepted_but_unpublished_is_not_delivered_and_an_unaccepted_row_cannot_be_published(self):
        h = self.chain["B"][0][1].row_hash; acc(self.acc, h); res = self.o["B"][1].recover_publication(self.o["B"][0])
        self.assertEqual(code(self.both("B", res, 0, 30, "u")[0]), "NON_DELIVERY")
        with self.assertRaises(Refusal) as e: self.publish_unaccepted()
        self.assertEqual(e.exception.code, "ROW_NOT_ACCEPTED")
    def publish_unaccepted(self):
        fk, co = self.o["B"][0], self.o["B"][1]; return RP.RowPublication(co._path, self.a.rig.journals, self.rows, T, self.a.rig.store).publish(fk, self.chain["B"][2][1].row_hash, "SIM_CUR", sequence=1, visible_at=50, published_projection_hash=RH, data_vintage_mode="v", source_or_causal_policy_ref=R("p"))
    def test_control_the_affected_feature_with_undeclared_ancestry_is_denied_for_both_consumers_even_with_an_accepted_published_row(self):
        self.publish("A", 0); res = self.o["A"][1].recover_publication(self.o["A"][0]); fw, ml = self.both("A", res, 0, 30, "a")
        self.assertEqual(code(fw), "NON_DELIVERY"); self.assertFalse(ml.included)

    def test_e05_rebuild_over_the_per_row_route_projects_rows_transitions_and_the_durable_FW_ML_final_resolutions_and_a_replaced_record_is_drift(self):
        from stage_a.storage import e05_sources as S, e05_row_sources as RW
        from stage_a.storage.e05_index import E05Index
        from .test_r44_e05_rebuild_separated import bind_cols, nd_cols
        self.publish("B", 0); self.publish("B", 1); fk, co = self.o["B"][0], self.o["B"][1]; res = co.recover_publication(fk)
        for step, n in ((0, "0"), (1, "1")): fw, ml = self.both("B", res, step, 0, n); fw(); self.assertTrue(ml.included)
        rig = self.a.rig; raw = self.a.raws["B"]; row0 = self.chain["B"][0][0]; ns = RA.row_namespace(row0); j = rig.journals.journal(ns)
        src = {"rows": RW.pending_row_source(rig.store, self.rows, lambda h: "HELD_STATE"), "tx": RW.row_transition_source(j, ns, self.rows), "fr": S.final_resolution_source(raw, binding_columns=bind_cols, non_delivery_columns=nd_cols)}
        ix = E05Index(); heads = ix.rebuild(src); resolver = S.combined_resolver(S.object_resolver(rig.store), S.journal_resolver({ns: j}), S.object_resolver(raw))
        self.assertGreaterEqual(ix.verify_all(resolver), 8)                                                                                # 6 pending rows (A+B) + 2 transitions + 4 final resolutions (FW+ML x 2 windows) all re-resolve
        st = ix.current_status(row0.feature_id.hex(), row0.materialization_version, "tx", heads["tx"], resolver); self.assertEqual(json.loads(st["payload"])["head_seq"], 2)
        k = sorted(raw.list_prefix("final-resolution/id/"))[0]; g = raw.get(k); raw._d[k] = (g[0][:-1] + bytes([g[0][-1] ^ 1]), g[1])
        with self.assertRaises(Exception): ix.verify_all(resolver)                                                                          # a replaced durable record is DRIFT, never silently re-read

    def test_cold_restart_of_the_owning_connection_keeps_per_row_final_outcomes_and_delivers_new_row_windows_to_FW_and_ML_but_not_unpublished_rows(self):
        from stage_a.core.tracker_core import TrackerCore
        from stage_a.coordination.object_store_journal import ObjectStoreJournal
        from stage_a.tracker import composition as CO, sim_publication_path as SP
        from .test_r37_sim_publication_path import SPEC
        self.publish("B", 0); fk, co = self.o["B"][0], self.o["B"][1]; r1 = co.recover_publication(fk); fw0, ml0 = self.both("B", r1, 0, 0, "0"); b0 = fw0(); self.assertTrue(ml0.included)
        rig = self.a.rig; c2 = TrackerCore(self.c._j, simulation=True); sj = ObjectStoreJournal(rig.store, "SIMPUB-%s-B" % fk.scope.instrument, "w2"); sj.acquire_epoch()
        co2 = CO.Composition(pipeline=rig.pipe, journals=rig.journals, store=rig.store, core=c2, path=SP.SimulationPublicationPath(rig.store, rig.journals.journal(fk.namespace()), sj, SPEC), gateway_factory=lambda proj: _gw(proj, c2, self.a.raws["B"]))
        self.assertEqual(code(co2.deliver, "z", FI("FW", "M", "XAUUSD", "W"), self.o["B"][4], I, I, 0, 60, r1, binding=self.o["B"][3], now=12, ref=R("hl"), resolved_at=11, tables=GTAB), "COMPOSITION_NOT_PUBLISHED")   # nothing survives in memory
        r2 = co2.recover_publication(fk); self.assertEqual(r2.status, "RECOVERED_PUBLISHED_SIMULATION"); self.o["B"] = (fk, co2) + tuple(self.o["B"][2:])
        b0b = self.both("B", r2, 0, 0, "0")[0](); self.assertEqual((b0b.request_id, b0b.delivered_feature_hash), (b0.request_id, b0.delivered_feature_hash))   # the exact stored outcome
        self.publish("B", 1); r3 = co2.recover_publication(fk); fw1, ml1 = self.both("B", r3, 1, 0, "1"); self.assertIsInstance(fw1(), G.Binding); self.assertTrue(ml1.included)  # a row accepted+published AFTER the restart
        self.assertEqual(code(self.both("B", r3, 2, 0, "2")[0]), "NON_DELIVERY")

    def test_composition_publishes_an_accepted_row_first_class_and_refuses_foreign_result_foreign_path_and_unaccepted_rows(self):
        fk, co = self.o["B"][0], self.o["B"][1]; res = co.recover_publication(fk); rp = RP.RowPublication(co._path, self.a.rig.journals, self.rows, T, self.a.rig.store)
        kws = dict(sequence=1, visible_at=50, published_projection_hash=RH, data_vintage_mode="ORIGINAL_AS_OBSERVED", source_or_causal_policy_ref=R("pol")); h0 = self.chain["B"][0][1].row_hash
        self.assertEqual(code(co.publish_accepted_row, res, rp, h0, "SIM_CUR", **kws), "ROW_NOT_ACCEPTED")                                                  # unaccepted: nothing published
        self.assertEqual(code(self.both("B", res, 0, 0, "p")[0]), "NON_DELIVERY"); acc(self.acc, h0)
        self.assertEqual(code(co.publish_accepted_row, self.o["B"][2], rp, h0, "SIM_CUR", **kws), "COMPOSITION_RESULT_NOT_THIS_PUBLICATION")                 # the build-time result is not the recovered one
        other = RP.RowPublication(self.o["A"][1]._path, self.a.rig.journals, self.rows, T, self.a.rig.store); self.assertEqual(code(co.publish_accepted_row, res, other, h0, "SIM_CUR", **kws), "COMPOSITION_ROW_PUBLICATION_FOREIGN_PATH")
        rec = co.publish_accepted_row(res, rp, h0, "SIM_CUR", **kws); self.assertEqual(res.published_rows >= 1, True)
        fw, ml = self.both("B", res, 0, 0, "q"); self.assertIsInstance(fw(), G.Binding); self.assertTrue(ml.included)                                         # delivered with NO second recover_publication
        self.assertEqual(co.publish_accepted_row(res, rp, h0, "SIM_CUR", **kws), rec)                                                                           # replay: same record

    def test_all_segment_stored_value_failure_after_publication_denies_the_ROW_windows_for_FW_and_excludes_ML_while_the_control_before_it_delivers(self):
        from .test_r37_stored_values import SER, H as SH
        res_ = {"SRC/close": SER}; si = dict(bindings={"close": {"ref": "SRC/close", "hash": SH(SER)}}, fetch=lambda ref: res_.get(ref), series_hash=SH)
        self.publish("B", 0); self.publish("B", 1); fk, co = self.o["B"][0], self.o["B"][1]; res = co.recover_publication(fk, stored_inputs=si)
        self.assertIn(("stored_basis", "RESTORED_FROM_STORED_SEGMENTS", "VERIFIED_STORED_EQUALS_RECOMPUTED"), res.steps)                                              # the stored segment is the feature-version one the rows belong to
        fw0, ml0 = self.both("B", res, 0, 0, "s0"); self.assertIsInstance(fw0(), G.Binding); self.assertTrue(ml0.included)                                           # control: healthy before
        co.register_stored_maintenance(res); res_["SRC/close"] = SER[:-1] + [-1]                                                                                       # the source of a stored segment changes
        self.assertEqual([x[2] for x in co.run_maintenance([(fk.key(), "SCHEDULED")], now=13, max_age=50, max_items=4)], ["RECORDED_NOT_PASS"])
        import dataclasses as dc; fk_, co_, r0, b, e = self.o["B"]; e = dc.replace(e, expected_projection=self.chain["B"][0][0].published_projection_name); k = dict(binding=b, now=14, ref=R("hl-2"), resolved_at=13, tables=GTAB)
        self.assertEqual(code(co.deliver, "fw-s1", FI("FW", "M-s1", "XAUUSD", "Ws1"), e, I, I, 1, 60, res, **k), "NON_DELIVERY")                                           # FW refused for a published, accepted ROW window
        row = co.deliver_ml("ml-s1", FI("ML", "D-s1", "XAUUSD", "Ws1"), e, I, I, 1, 60, res, row_id="row-s1", generation_ref=R("gen"), vintage_mode="ORIGINAL_AS_OBSERVED", omissions=NONE_, exclusion_reason=lambda x: ("ENUM", "REASON", "ALL_SEGMENT_FAIL"), **k)
        self.assertFalse(row.included); self.assertEqual(row.row_exclusion_reason, ("ENUM", "REASON", "ALL_SEGMENT_FAIL"))                                               # ML excluded with the explicit reason
