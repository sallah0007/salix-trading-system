"""R43: the ML writer/finalizer + dataset manifest -> union -> request -> reverse-H1 + six joins wired into the SAME separated acceptance -> committed SIM status -> Core -> Gateway -> consumer path (stage_a/ml/consumer_path.py). Legitimate same-generation positive for the unrelated baseline and for the denied feature once its ancestry is declared; negatives: required non-delivery, mixed generation, mixed J1 manifest, foreign binding id, a Binding from ANOTHER gateway, a forged Binding, dataset revocation, generation revocation around the facade, an ungranted caller. qualified is ALWAYS False; grants are test labels; the catalog snapshot is a TEST-SUPPLIED slot (the accepted-record -> definition/formula/graph hash mapping is not source-defined)."""
import dataclasses, unittest
from stage_a.errors import Refusal
from stage_a.gateway import contracts as G
from stage_a.gateway.v038 import FinalResolutionIdentity as FI
from stage_a.ml import consumer_path as CP, dataset_manifest as DM, dataset_authority as DA, generation_lifecycle as GL, writer_finalizer as WF, six_joins as SJ
from .test_r41_separated_caller import Caller as _Caller, FB, supplied, AP, I, T, R, _entry, ver
from .test_r35_dataset_manifest import ds
from .test_r29_generation_lifecycle import man, ev
NONE_ = ("ENUM", "REASON", "NONE"); EXCL = ("ENUM", "REASON", "REQUIRED_DEPENDENCY_NOT_DELIVERED")
def code(f, *a, **k):
    try: f(*a, **k)
    except Refusal as e: return e.code
class MLIntegration(_Caller):
    test_separated_child_acceptance_then_committed_status_core_gateway_with_unknown_ancestry_denied_and_the_unrelated_baseline_delivered = None
    test_a_failed_child_job_never_yields_an_acceptance_or_publication = None
    test_a_non_admissible_package_is_not_staged_claimed_or_run = None
    def _ml(self, co, fk, r, tag, fid, bind):
        self.c.declare_ancestry_complete(fk.key(), "src"); b = G.HealthBinding(fid, fk.feature_version, I, I); self.c.associate_subject(fk.key(), b, "assoc"); e = _entry(fid=fid, ver=fk.feature_version)
        health = self.c.gateway_health(fk.key(), fk.feature_version, 12, R("hl-" + tag), 11, binding=b, require_ancestry=True)
        return e, co.gateway.resolve_window("ml-" + tag, FI("ML", bind, "XAUUSD", tag), e, I, I, 3, 20, health)
    def joins(self, e, bind, dsid, gid, gm, reg, **o):
        j = {"J1_DATASET_MANIFEST": {"binding_id": bind, "dataset_manifest_id": dsid, "dataset_manifest_hash": "h-" + dsid},
             "J2_INCLUDED_FEATURES": [{"feature_id": e.feature_id.hex(), "feature_version": e.feature_version, "definition_hash": "d", "formula_hash": "f", "graph_hash": "g", "closure_ref": "c"}],
             "J3_BIND_TIME_HEALTH": {"EVIDENCE_REF": "ev"}, "J4_GENERATION_COMPONENTS": {"manifest_id": gid, "manifest_hash": gm.manifest_hash, "components": dict(gm.components)},
             "J5_LIFECYCLE_LEDGER": {"manifest_id": gid, "manifest_hash": gm.manifest_hash, "epoch": reg.epoch}, "J6_RESEARCH_FAMILY_EXPOSURE": {"family_ref": "fam", "ledger_ref": "l", "ledger_version": "1", "ledger_hash": "lh", "consulted_available_asof": 5}}
        j.update(o); return j
    def test_separated_acceptance_to_both_consumers_then_ml_writer_dataset_union_request_reverse_h1_and_six_joins_on_the_same_objects(self):
        pa, fka, coa = self._feature("mom3", 1); pb, fkb, cob = self._feature("mom4", 2); coa._up = {fka.key(): ("UP",)}; ver(self.c, "UP", version="1", at=9, age=50)
        ra = coa.accept_and_publish(pa, supplied(), "SIM_CUR", sequence=1, now=10, max_age=50, l2_applicability=AP, accept_fn=self.acc)
        rb = cob.accept_and_publish(pb, supplied(feature_id=FB), "SIM_CUR", sequence=1, now=10, max_age=50, l2_applicability=AP, accept_fn=self.acc)
        self.assertEqual((ra.status, rb.status), ("PUBLISHED_SIMULATION", "PUBLISHED_SIMULATION")); self.c.declare_ancestry_complete(fkb.key(), "src")
        reg = GL.GenerationRegistry(); wf = WF.GenerationAuthority(reg, {"MANIFEST_WRITER": {"w1"}, "FINALIZER": {"f1"}}, "TEST-LABELS-NOT-PRINCIPALS")
        for g in ("G1", "G2"): wf.write_manifest("w1", man(g)); wf.finalize("f1", g, 10, "cert")
        dsr = DM.DatasetRegistry({"w"}, "TEST-GRANT-LABEL"); auth = DA.DatasetAuthority(dsr, reg)
        for d in ("D1", "D2", "D3", "D4"): dsr.register("w", ds(d)); auth.declare_union("w", d, ())
        cat = {}
        def path(co): return CP.MLConsumerPath(gateway=co.gateway, final_store=co.gateway.final_store, authority=auth, generations=reg, writer=wf, tables=T)
        def go(co, e, o, tag, bind, dsid, gid="G1", **k):
            kw = dict(row_id="row-" + tag, generation_ref=R("gen"), generation_manifest_id=gid, event=ev(100), request_start_ts=100, fence=10, eligibility_reason=NONE_, exclusion_reason_for_missing=lambda x: EXCL, catalog_snapshot=cat or None)
            kw.update(k); j = kw.pop("joins", None) or self.joins(e, bind, dsid, gid, reg.manifest_of(gid), reg)
            return path(co).consume("w", ds(dsid), e, o, "ml-" + tag, joins=j, **kw)
        # ---- required unknown ancestry: the ML row is EXCLUDED, nothing is consumed
        ea, oa = self._ml(coa, fka, ra, "A1", supplied().feature_id, "BIND-A1"); self.assertEqual(type(oa).__name__, "NonDeliveryResolution")
        x = go(coa, ea, oa, "A1", "BIND-A1", "D1"); self.assertEqual(x.blockers, ("ROW_EXCLUDED_REQUIRED_DEPENDENCY_NOT_DELIVERED",)); self.assertFalse(x.qualified); self.assertEqual(dsr.binding_index(), {})
        # ---- unrelated baseline: a genuine same-generation positive through every step
        eb, ob = self._ml(cob, fkb, rb, "B1", FB, "BIND-B1"); self.assertIsInstance(ob, G.Binding); cat[(eb.feature_id.hex(), eb.feature_version)] = ("d", "f", "g")
        y = go(cob, eb, ob, "B1", "BIND-B1", "D1"); self.assertEqual(y.blockers, ()); self.assertTrue(y.usable_for_simulation); self.assertFalse(y.qualified); self.assertTrue(y.row.included)
        self.assertEqual((y.binding_health["binding_id"], y.binding_health["dataset_manifest_id"]), ("BIND-B1", "D1")); self.assertEqual(y.gate["verdict"], "CLEAR"); self.assertEqual(y.generation["status"], "VERIFIED_AGAINST_REGISTRY")
        self.assertEqual({s for _, s, _ in y.joins.statuses}, {SJ.VERIFIED_AGAINST_REGISTRY, SJ.PRESENT_UNVERIFIED}); self.assertEqual(dict((c, s) for c, s, _ in y.joins.correlation)["REQUEST_SNAPSHOT_SAME_GENERATION"], SJ.VERIFIED_AGAINST_REGISTRY); self.assertIn("J3_BIND_TIME_HEALTH_SERVICE_INSTANCE", y.held)
        # ---- mixed generation / mixed J1 manifest / foreign binding id (same Binding, altered join record)
        g2 = reg.manifest_of("G2"); mixed = self.joins(eb, "BIND-B2", "D2", "G2", g2, reg)
        z = go(cob, eb, ob, "B1", "BIND-B1", "D1", joins=mixed); self.assertIn("J1_BINDING_ID_NOT_THE_ISSUED_IDENTITYS", z.blockers)
        z = go(cob, eb, ob, "B1", "BIND-B1", "D1", joins=self.joins(eb, "BIND-B1", "D1", "G2", g2, reg)); self.assertIn("JOINS_REQUEST_SNAPSHOT_SAME_GENERATION_MISMATCH", z.blockers)        # J4/J5 name G2, the issued snapshot is G1
        z = go(cob, eb, ob, "B1", "BIND-B1", "D1", joins=self.joins(eb, "BIND-B1", "D2", "G1", reg.manifest_of("G1"), reg)); self.assertIn("JOIN_J1_DATASET_MANIFEST_MISMATCH", z.blockers)                # reverse index resolves BIND-B1 to D1, not D2
        z = go(cob, eb, ob, "B1", "BIND-B1", "D1", joins=self.joins(eb, "BIND-B1", "D1", "G1", reg.manifest_of("G1"), reg, J4_GENERATION_COMPONENTS={"manifest_id": "G1", "manifest_hash": "forged", "components": {}})); self.assertTrue(any(b.startswith("JOIN_J4") for b in z.blockers))
        # ---- a Binding from ANOTHER gateway, a forged copy, an unlinked/other manifest, an ungranted caller: refused before anything is written
        forged = G.Binding(ob.request_id, ob.entry, ob.delivered_feature_hash, ob.fence); self.assertEqual(code(go, cob, eb, forged, "B1", "BIND-B1", "D1"), "DATASET_BINDING_OUTCOME_NOT_GATEWAY_ISSUED")
        self.assertEqual(code(go, coa, eb, ob, "B1", "BIND-B1", "D1"), "DATASET_REQUEST_NOT_ISSUED_FOR_ML_BINDING")                                  # cob's Binding on coa's gateway/final store
        self.assertEqual(code(lambda: path(cob).consume("x", ds("D1"), eb, ob, "ml-B1", row_id="r", generation_ref=R("gen"), generation_manifest_id="G1", event=ev(100), request_start_ts=100, joins={}, fence=10, eligibility_reason=NONE_, exclusion_reason_for_missing=lambda x: EXCL)), "ML_CALLER_NOT_GRANTED")
        self.assertEqual(code(go, cob, eb, ob, "B1", "BIND-B1", "D2"), "DATASET_LINK_IMMUTABLE")                                                      # BIND-B1 cannot be re-pointed at another manifest
        # ---- the denied feature, after its ancestry is declared, is delivered and consumed the same way (the denial was the ancestry)
        self.c.declare_ancestry_complete("UP", "src"); ea2, oa2 = self._ml(coa, fka, ra, "A2", supplied().feature_id, "BIND-A2"); self.assertIsInstance(oa2, G.Binding); cat[(ea2.feature_id.hex(), ea2.feature_version)] = ("d", "f", "g")
        w = go(coa, ea2, oa2, "A2", "BIND-A2", "D3"); self.assertEqual(w.blockers, ())
        # ---- revocation: dataset revoked -> BLOCKED; generation revoked around the facade -> no snapshot / correlate mismatch
        dsr.revoke("w", "D3", 20, "contamination", "AUTH"); self.assertIn("DATASET_REVOKED", go(coa, ea2, oa2, "A2", "BIND-A2", "D3").blockers)
        reg.append_lifecycle("G1", "REVOKED", 30, "bad", "ROGUE")
        v = go(cob, eb, ob, "B1", "BIND-B1", "D1"); self.assertIn("SNAPSHOT_ML_GENERATION_NOT_SERVING_ELIGIBLE", v.blockers); self.assertFalse(v.usable_for_simulation)
    def test_ports_must_be_supplied(self):
        self.assertEqual(code(CP.MLConsumerPath, gateway=None, final_store=1, authority=1, generations=1, writer=1, tables=1), "ML_CONSUMER_PATH_PORT_MISSING")
if __name__ == "__main__": unittest.main()
