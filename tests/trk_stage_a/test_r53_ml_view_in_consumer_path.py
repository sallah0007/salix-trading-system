"""R53: the Tracker REGISTRY section 14 duties wired INTO the actual MLConsumerPath (not a standalone checker): same separated feature acceptance, real accepted rows of that feature, writer/finalizer + dataset + union + request + reverse H1 + six joins, then `consume(feature_view=...)`.
SIM resolvers/identity/eligibility/split policy are UNADMITTED test stand-ins. Satisfying the duties authorizes nothing (p351); the result stays qualified=False."""
import dataclasses, hashlib, json
from stage_a.ml import consumer_path as CP, dataset_manifest as DM, dataset_authority as DA, generation_lifecycle as GL, writer_finalizer as WF, tracker_ml_contract as TM
import dataclasses as dc
from stage_a.gateway import contracts as G
from stage_a.gateway.v038 import FinalResolutionIdentity as FI
from stage_a.storage.object_store import InMemoryObjectStore
from stage_a.tracker import row_acceptance as RA, accepted_manifest as AM, row_publication as RP
from stage_a.tracker.materialization import row_store as RS
from stage_a.tracker.materialization.state_rows import StateRowBuilder
from . import health_fixtures as HF
from . import test_r43_ml_integration as R43
EXCL, NONE_ = R43.EXCL, R43.NONE_
from .test_r41_separated_caller import FB, supplied, AP, I, T, R, ver, _entry
from .test_r53_row_route_delivery import GTAB, _gw, RH
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
        rig = self.rig; mh = AM.read_accepted_manifest(rig.journals.journal(fkb.namespace()), rig.store, fkb).manifest_hash; rows = RS.PendingRowStore(rig.store, RT); a = RA.RowAcceptor(rig.journals, rows, RT, Time(20), CPORT()); hs = []
        fixed = dict(FX, feature_id=FB, feature_version=fkb.feature_version, quant_manifest_hash=bytes.fromhex(mh), instrument_id=I, timeframe_id=I, materialization_version="mrow"); ch = RS.CommittedRowChain(StateRowBuilder(SCHEMA, RT, enc, dec, fixed), rows); ph = None
        for i, x in enumerate([1.0, 2.0]):
            row, rc = ch.step(step_fn, ph, {"x": x}, **rkw(i, origin=ph is None)); acc(a, rc.row_hash); hs.append(rc.row_hash); ph = rc.row_hash
        ns = RA.row_namespace(row); j = rig.journals.journal(ns); cob._gf = lambda proj: _gw(proj, self.c, InMemoryObjectStore())
        rp = RP.RowPublication(cob._path, rig.journals, rows, RT, rig.store)
        for i, h in enumerate(hs): cob.publish_accepted_row(rb, rp, h, "SIM_CUR", sequence=i + 1, visible_at=50, published_projection_hash=RH, data_vintage_mode="ORIGINAL_AS_OBSERVED", source_or_causal_policy_ref=R("pol"))
        fixed2 = dict(fixed, materialization_version="mother"); row5, rc5 = RS.CommittedRowChain(StateRowBuilder(SCHEMA, RT, enc, dec, fixed2), rows).step(step_fn, None, {"x": 4.0}, **rkw(2, origin=True)); acc(a, rc5.row_hash)       # SAME feature/version, a DIFFERENT real MV + step, accepted+published, NOT in the view
        cob.publish_accepted_row(rb, rp, rc5.row_hash, "SIM_CUR", sequence=1, visible_at=50, published_projection_hash=RH, data_vintage_mode="ORIGINAL_AS_OBSERVED", source_or_causal_policy_ref=R("pol"))
        nss = {RA.row_namespace(row): j, RA.row_namespace(row5): rig.journals.journal(RA.row_namespace(row5))}
        def bridge(ref):                                                                                                                      # SUPPLIED subject-bound: read the committed ROW_ACCEPTED record the transition ref names, verify its hash/version
            if getattr(ref, "ref_type", None) != "CANONICAL_TRANSITION_REF": return None
            for n_, jj in nss.items():
                for r_ in (jj.read_from(1) if jj.head().seq else []):
                    if r_.record_hash == ref.target_id.hex():
                        b_ = json.loads(r_.body_json); rw = rows.load(b_["row_content_hash"])
                        return (b_["row_content_hash"], rw.materialization_version, rw.step_index) if b_["transition_hash"] == ref.target_hash.hex() and RA.VERSION_TAG.encode() == ref.target_version else None
            return None
        def window(step, tag, bind):
            e = dc.replace(_entry(fid=FB, ver=fkb.feature_version), expected_projection=row.published_projection_name)
            health = self.c.gateway_health(fkb.key(), fkb.feature_version, 12, R("hl-" + tag), 11, binding=G.HealthBinding(FB, fkb.feature_version, I, I), require_ancestry=True)
            return e, cob.gateway.resolve_window("ml-" + tag, FI("ML", bind, "XAUUSD", tag), e, I, I, step, 60, health)
        avail = lambda h: [json.loads(r.body_json)["available_asof"] for r in j.read_from(1) if json.loads(r.body_json)["row_content_hash"] == h][-1]
        eb, ob = self._ml(cob, fkb, rb, "B1", FB, "BIND-B1"); self.assertIsInstance(ob, G.Binding)                                      # LEGACY feature-version window (step 3), issued by the rebuilt gateway
        ee, oe = window(0, "E", "BIND-E"); eo, oo = window(2, "O", "BIND-O"); self.assertIsInstance(oe, G.Binding); self.assertIsInstance(oo, G.Binding)
        win = {"legacy": (eb, ob, "BIND-B1", "B1"), "exact": (ee, oe, "BIND-E", "E"), "outside": (eo, oo, "BIND-O", "O")}
        res = dict(accepted_hash=lambda f, v: mh if (f, v) == (fkb.feature_id, fkb.feature_version) else None, row_availability=avail, row_scope=lambda h: (I.hex(), I.hex()), row_fit_ref=lambda h: None, eligible=lambda *x: True, identity_fn=ident,
                   row_owner=lambda h: (fkb.feature_id, rows.load(h).feature_version, rows.load(h).quant_manifest_hash.hex()) if rows.load(h).feature_id == FB else None, lineage_of=lambda f, v: {"SRC/close"}, target_known=lambda t, h: True, split_policy=lambda sp: True)
        m = TM.FeatureViewManifest("fv-1", ((fkb.feature_id, fkb.feature_version, mh),), (("SRC/close", "ab" * 32),), "ORIGINAL_AS_OBSERVED", "tgt-1", "h-1", ("LBL/outcome",), (("train", 0, 100), ("validation", 100, 150), ("test", 150, 200)), (("w1", 0, 90),), (), (("standard-scaler", "s-1", "w1"),), 10_000, ((I.hex(), I.hex()),), tuple((fkb.feature_id, h) for h in hs), (), "")
        m = dataclasses.replace(m, replay_identity=ident(TM._body(m))); st = TM.FeatureViewStore({"ml-writer"}); st.register("ml-writer", m)
        fv = dict(store=st, manifest_id="fv-1", resolvers=res, symbol_of=lambda fid: fkb.feature_id if fid == FB else None, row_of_transition=bridge)
        def go(which="exact", **k):
            e_, o_, bind, tag = win[which]; kw = dict(row_id="row-" + tag, generation_ref=R("gen"), generation_manifest_id="G1", event=ev(100), request_start_ts=100, fence=10, eligibility_reason=NONE_, exclusion_reason_for_missing=lambda x: EXCL, health=HF.ml_supplier(e_, "D1"))
            kw.update(k); j = self.joins(e_, bind, "D1", "G1", reg.manifest_of("G1"), reg)
            return CP.MLConsumerPath(gateway=cob.gateway, final_store=cob.gateway.final_store, authority=auth, generations=reg, writer=wf, tables=GTAB).consume("w", ds("D1"), e_, o_, "ml-" + tag, joins=j, catalog_snapshot={(e_.feature_id.hex(), e_.feature_version): ("d", "f", "g")}, **kw)
        return go, fv, m, st, res
    def test_the_view_duties_gate_the_actual_consumption_and_an_unbound_or_failing_duty_blocks_it(self):
        go, fv, m, st, res = self.build(); base = go(); self.assertEqual(base.blockers, ()); self.assertIn("TRACKER_ML_FEATURE_VIEW_NOT_SUPPLIED", base.held)                      # legacy no-view: not blocked, named HELD (NOT all-13 validated)
        ok = go(feature_view=fv); self.assertEqual(ok.blockers, ()); self.assertTrue(ok.usable_for_simulation); self.assertFalse(ok.qualified); self.assertNotIn("TRACKER_ML_FEATURE_VIEW_NOT_SUPPLIED", ok.held)   # genuine exact-row delivery
        self.assertEqual(go(feature_view=dict(fv, resolvers=dict(res, lineage_of=None))).blockers, ("TRACKER_ML_DUTY_p339_HELD", "TRACKER_ML_DUTY_p341_HELD"))                          # unbound relation: HELD blocks
        self.assertEqual(go(feature_view=dict(fv, resolvers=dict(res, eligible=lambda *a: False))).blockers, ("TRACKER_ML_DUTY_p347_FAIL",))
        self.assertEqual(go(feature_view=dict(fv, manifest_id="nope")).blockers, ("TRACKER_ML_VIEW_NOT_REGISTERED",)); self.assertEqual(go(feature_view={"store": st}).blockers, ("TRACKER_ML_VIEW_INPUT_INVALID",))
    def test_a_consumed_feature_the_view_does_not_declare_or_cannot_be_mapped_blocks(self):
        go, fv, m, st, res = self.build()
        self.assertEqual(go(feature_view=dict(fv, symbol_of=lambda fid: None)).blockers, ("CONSUMED_FEATURE_SYMBOL_UNMAPPED_HELD",))                                                  # no guessed string/byte equality
        self.assertEqual(go(feature_view=dict(fv, symbol_of=lambda fid: "other-feature")).blockers, ("CONSUMED_FEATURE_NOT_DECLARED_IN_VIEW",))
    def test_the_consumed_ROW_must_be_one_of_the_views_declared_rows_a_same_feature_other_MV_row_and_a_legacy_row_are_not(self):
        go, fv, m, st, res = self.build()
        self.assertEqual(go("outside", feature_view=fv).blockers, ("CONSUMED_ROW_NOT_IN_VIEW",))                                          # same feature/version, real accepted+published row of ANOTHER MV/step, not in the view
        self.assertEqual(go("legacy", feature_view=fv).blockers, ("CONSUMED_ROW_NOT_BOUND_TO_VIEW_HELD",))                               # legacy feature-version row: no row relation => explicit HELD, not a pass
        no_bridge = {k: v for k, v in fv.items() if k != "row_of_transition"}; self.assertEqual(go("exact", feature_view=no_bridge).blockers, ("CONSUMED_ROW_NOT_BOUND_TO_VIEW_HELD",))
        self.assertEqual(go("exact", feature_view=dict(fv, row_of_transition=lambda ref: (res["row_owner"] and "x" * 64, "mrow", 99))).blockers, ("CONSUMED_ROW_DIFFERS_FROM_DELIVERED_ENTRY",))   # bridge result must equal the delivered entry's MV/step
        self.assertEqual(go("exact", feature_view=dict(fv, row_of_transition=lambda ref: (_ for _ in ()).throw(RuntimeError()))).blockers, ("CONSUMED_ROW_NOT_BOUND_TO_VIEW_HELD",))
