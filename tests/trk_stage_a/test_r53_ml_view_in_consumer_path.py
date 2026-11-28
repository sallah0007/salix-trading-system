"""R53: the Tracker REGISTRY section 14 duties wired INTO the actual MLConsumerPath (not a standalone checker): same separated feature acceptance, real accepted rows of that feature, writer/finalizer + dataset + union + request + reverse H1 + six joins, then `consume(feature_view=...)`.
SIM resolvers/identity/eligibility/split policy are UNADMITTED test stand-ins. Satisfying the duties authorizes nothing (p351); the result stays qualified=False."""
import dataclasses, hashlib, json
from stage_a.ml import consumer_path as CP, dataset_manifest as DM, dataset_authority as DA, generation_lifecycle as GL, writer_finalizer as WF, tracker_ml_contract as TM
from stage_a.tracker import row_acceptance as RA, accepted_manifest as AM
from stage_a.tracker.materialization import row_store as RS
from stage_a.tracker.materialization.state_rows import StateRowBuilder
from . import health_fixtures as HF
from . import test_r43_ml_integration as R43
EXCL, NONE_ = R43.EXCL, R43.NONE_
from .test_r41_separated_caller import FB, supplied, AP, I, T, R, ver
from .test_r35_dataset_manifest import ds
from .test_r29_generation_lifecycle import man, ev
from .test_r53_row_acceptance import T as RT, FX, kw as rkw, SCHEMA, enc, dec, step_fn, Time, CP as CPORT, acc
def ident(body): return hashlib.sha256(json.dumps(body, sort_keys=True, default=str).encode()).hexdigest()

class ViewInPath(R43.MLIntegration):
    test_r53_separated_child_acceptance_then_BOTH_FW_and_ML_deny_the_unknown_ancestry_feature_and_the_unrelated_BASE_delivers_to_both_before_between_after = None
    test_separated_acceptance_to_both_consumers_then_ml_writer_dataset_union_request_reverse_h1_and_six_joins_on_the_same_objects = None
    def build(self):
        pb, fkb, cob = self._feature("mom4", 2); rb = cob.accept_and_publish(pb, supplied(feature_id=FB), "SIM_CUR", sequence=1, now=10, max_age=50, l2_applicability=AP, accept_fn=self.acc); self.assertEqual(rb.status, "PUBLISHED_SIMULATION"); self.c.declare_ancestry_complete(fkb.key(), "src")
        reg = GL.GenerationRegistry(); wf = WF.GenerationAuthority(reg, {"MANIFEST_WRITER": {"w1"}, "FINALIZER": {"f1"}}, "TEST-LABELS-NOT-PRINCIPALS"); wf.write_manifest("w1", man("G1")); wf.finalize("f1", "G1", 10, "cert")
        dsr = DM.DatasetRegistry({"w"}, "TEST-GRANT-LABEL"); auth = DA.DatasetAuthority(dsr, reg); dsr.register("w", ds("D1")); auth.declare_union("w", "D1", ())
        eb, ob = self._ml(cob, fkb, rb, "B1", FB, "BIND-B1"); self.assertIsInstance(ob, __import__("stage_a.gateway.contracts", fromlist=["x"]).Binding)
        rig = self.rig; mh = AM.read_accepted_manifest(rig.journals.journal(fkb.namespace()), rig.store, fkb).manifest_hash; rows = RS.PendingRowStore(rig.store, RT); a = RA.RowAcceptor(rig.journals, rows, RT, Time(20), CPORT()); hs = []
        fixed = dict(FX, feature_id=FB, feature_version=fkb.feature_version, quant_manifest_hash=bytes.fromhex(mh), instrument_id=I, timeframe_id=I, materialization_version="mrow"); ch = RS.CommittedRowChain(StateRowBuilder(SCHEMA, RT, enc, dec, fixed), rows); ph = None
        for i, x in enumerate([1.0, 2.0]):
            row, rc = ch.step(step_fn, ph, {"x": x}, **rkw(i, origin=ph is None)); acc(a, rc.row_hash); hs.append(rc.row_hash); ph = rc.row_hash
        ns = RA.row_namespace(row); j = rig.journals.journal(ns)
        avail = lambda h: [json.loads(r.body_json)["available_asof"] for r in j.read_from(1) if json.loads(r.body_json)["row_content_hash"] == h][-1]
        res = dict(accepted_hash=lambda f, v: mh if (f, v) == (fkb.feature_id, fkb.feature_version) else None, row_availability=avail, row_scope=lambda h: (I.hex(), I.hex()), row_fit_ref=lambda h: None, eligible=lambda *x: True, identity_fn=ident,
                   row_owner=lambda h: (fkb.feature_id, rows.load(h).feature_version, rows.load(h).quant_manifest_hash.hex()) if rows.load(h).feature_id == FB else None, lineage_of=lambda f, v: {"SRC/close"}, target_known=lambda t, h: True, split_policy=lambda sp: True)
        m = TM.FeatureViewManifest("fv-1", ((fkb.feature_id, fkb.feature_version, mh),), (("SRC/close", "ab" * 32),), "ORIGINAL_AS_OBSERVED", "tgt-1", "h-1", ("LBL/outcome",), (("train", 0, 100), ("validation", 100, 150), ("test", 150, 200)), (("w1", 0, 90),), (), (("standard-scaler", "s-1", "w1"),), 10_000, ((I.hex(), I.hex()),), tuple((fkb.feature_id, h) for h in hs), (), "")
        m = dataclasses.replace(m, replay_identity=ident(TM._body(m))); st = TM.FeatureViewStore({"ml-writer"}); st.register("ml-writer", m)
        fv = dict(store=st, manifest_id="fv-1", resolvers=res, symbol_of=lambda fid: fkb.feature_id if fid == FB else None)
        def go(**k):
            kw = dict(row_id="row-1", generation_ref=R("gen"), generation_manifest_id="G1", event=ev(100), request_start_ts=100, fence=10, eligibility_reason=NONE_, exclusion_reason_for_missing=lambda x: EXCL, health=HF.ml_supplier(eb, "D1"))
            kw.update(k); j = self.joins(eb, "BIND-B1", "D1", "G1", reg.manifest_of("G1"), reg); return CP.MLConsumerPath(gateway=cob.gateway, final_store=cob.gateway.final_store, authority=auth, generations=reg, writer=wf, tables=T).consume("w", ds("D1"), eb, ob, "ml-B1", joins=j, catalog_snapshot={(eb.feature_id.hex(), eb.feature_version): ("d", "f", "g")}, **kw)
        return go, fv, m, st, res
    def test_the_view_duties_gate_the_actual_consumption_and_an_unbound_or_failing_duty_blocks_it(self):
        go, fv, m, st, res = self.build(); base = go(); self.assertEqual(base.blockers, ()); self.assertIn("TRACKER_ML_FEATURE_VIEW_NOT_SUPPLIED", base.held)                      # no view: not blocked, but named HELD
        ok = go(feature_view=fv); self.assertEqual(ok.blockers, ()); self.assertTrue(ok.usable_for_simulation); self.assertFalse(ok.qualified); self.assertNotIn("TRACKER_ML_FEATURE_VIEW_NOT_SUPPLIED", ok.held)
        self.assertEqual(go(feature_view=dict(fv, resolvers=dict(res, lineage_of=None))).blockers, ("TRACKER_ML_DUTY_p339_HELD", "TRACKER_ML_DUTY_p341_HELD"))                          # unbound relation: HELD blocks
        self.assertEqual(go(feature_view=dict(fv, resolvers=dict(res, eligible=lambda *a: False))).blockers, ("TRACKER_ML_DUTY_p347_FAIL",))                                          # failing duty blocks
        self.assertEqual(go(feature_view=dict(fv, manifest_id="nope")).blockers, ("TRACKER_ML_VIEW_NOT_REGISTERED",)); self.assertEqual(go(feature_view={"store": st}).blockers, ("TRACKER_ML_VIEW_INPUT_INVALID",))
    def test_a_consumed_feature_the_view_does_not_declare_or_cannot_be_mapped_blocks(self):
        go, fv, m, st, res = self.build()
        self.assertEqual(go(feature_view=dict(fv, symbol_of=lambda fid: None)).blockers, ("CONSUMED_FEATURE_SYMBOL_UNMAPPED_HELD",))                                                  # no guessed string/byte equality
        self.assertEqual(go(feature_view=dict(fv, symbol_of=lambda fid: "other-feature")).blockers, ("CONSUMED_FEATURE_NOT_DECLARED_IN_VIEW",))
