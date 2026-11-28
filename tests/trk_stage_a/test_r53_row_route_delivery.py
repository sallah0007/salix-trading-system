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
