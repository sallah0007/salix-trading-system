"""R33: ONE composed candidate path in explicit simulation: ClaimService order (via the order facade) -> build gate -> actual TrackerPipeline.run (CANONICAL_ACCEPTED) -> Core real re-verification of THAT accepted feature -> Core health snapshot -> actual SimulatedGateway.resolve. No second registry/issuer/Gateway. Subject->dependency association, ancestry declarations and the simulated gateway rows are SUPPLIED and UNADMITTED; nothing here is qualified."""
import json, unittest
from stage_a.gateway import contracts as G
from stage_a.tracker import chain_status as C
from stage_a.tracker import reverify_scheduler as S
from stage_a.composer.expression.manifest import Manifest
from stage_a.tracker.quant_intake_adapter import admit
from stage_a.composer import order_authority as OA
from stage_a.composer.build_gate import accept_build_start as abs_
from .fixtures import Rig, package, SIM_CONF, momentum_manifest
from .strict_gateway import sgw
from .test_boundaries import _entry, _row, I, R
from .test_r25_scheduler import core, ver, declared, SIMS
from .test_r29_intake_order import issue, br
from stage_a.identifiers import FeatureKey
from stage_a.storage.authority_class import _PREFIX
RAW = lambda rig, k: rig.store.get(k)
from stage_a.errors import Refusal
from stage_a.tracker import reverification as RV
from stage_a.storage.keys import accepted_materialization_key, artifact_key
from stage_a.storage.byte_primitives import canonical_bytes

def code(f, *a, **k):
    try: f(*a, **k)
    except Refusal as e: return e.code

class ComposedOrderToConsumer(unittest.TestCase):
    def test_order_to_pipeline_to_core_health_to_gateway_with_required_unknown_ancestry_and_unrelated_baseline(self):
        rig = Rig(); oid = OA.order_id_for("cand-1"); p = package(order_id=oid)
        sk = admit(p, accepted_fit_generations=rig.fits, conformance=SIM_CONF).subject_key
        self.assertEqual(issue(rig.claims, subject_key=sk)["order_id"], oid); abs_(rig.claims, oid, br())
        out = rig.pipe.run(p); self.assertEqual(out.accepted.kind, "CANONICAL_ACCEPTED")
        key = json.loads(out.accepted.body_json)["feature_key"]                                                   # the ACCEPTED feature, not a literal
        fk = admit(p, accepted_fit_generations=rig.fits, conformance=SIM_CONF).feature_key; self.assertEqual(fk.key(), key); c = core()
        c.declare_dependency(key, "UP"); ver(c, "UP", version="1", at=9, age=50); ver(c, "BASE", version="1", at=9, age=50)                 # upstream evidence precedes the dependent's
        res, st = RV.reverify_accepted(c, journal=rig.journals.journal(fk.namespace()), store=rig.store, feature_key=fk, now=10, max_age=50)     # the ACCEPTED record as found, not a probe of a supplied manifest
        self.assertEqual((res.status, st), ("PASS", "ACCEPTED_RECORD_AS_FOUND"))
        self.assertEqual(c.recording_health(key, "1", 11).state, "HEALTHY")                                       # same key the pipeline accepted
        F2 = b"\x02" * 16; b1 = G.HealthBinding(I, "1", I, I); b2 = G.HealthBinding(F2, "1", I, I)
        c.associate_subject(key, b1, "assoc-accepted"); c.associate_subject("BASE", b2, "assoc-base"); c.declare_ancestry_complete("BASE", "src")
        gw = sgw(c); gw.publish(_row(fid=F2, ver="1")); gw.status.append(C.StatusFact((F2, "1", I, I, "m1"), 1, C.CURRENT, 1, False))
        def hs(subj, b): return c.gateway_health(subj, "1", 12, R("hl"), 11, binding=b, require_ancestry=True)
        dep = gw.resolve("d1", _entry(ver="1"), I, I, 3, 20, hs(key, b1)); self.assertEqual((type(dep).__name__, dep.reason), ("NonDeliveryResolution", "HEALTH_UNACCEPTABLE"))        # required ancestor undeclared => fail closed
        self.assertIsInstance(gw.resolve("b1", _entry(fid=F2, ver="1"), I, I, 3, 20, hs("BASE", b2)), G.Binding)                                                                 # unrelated baseline delivered
        self.assertEqual(c.recording_health(key, "1", 12).local_state, "HEALTHY")                                    # Build Plan 14A: the carried-upstream denial never overwrites the subject's LOCAL_STATE
        c.declare_ancestry_complete("UP", "src"); c.declare_ancestry_complete(key, "src")
        e2 = _entry(ver="1"); d2 = gw.resolve("d2", e2, I, I, 3, 20, hs(key, b1)); self.assertIsInstance(d2, G.Binding)             # declared complete + healthy => delivered
        from stage_a.fw import receiver as FWR
        from stage_a.ml import receiver as MLR
        from .test_r24_core import T, NONE_
        self.assertIs(FWR.receive_verified(d2, e2, I, I, T, gw), d2)                                               # FW exact read-only receive of the SAME stored Gateway outcome
        self.assertTrue(MLR.build_row("r-composed", R("gen"), [e2], [d2], gw, "ORIGINAL_AS_OBSERVED", NONE_, lambda o: NONE_, tables=gw.t).included)
        self.assertEqual(code(FWR.receive_verified, dep, e2, I, I, T, gw), "NON_DELIVERY")                         # the earlier fail-closed outcome stays a non-delivery to the consumer
    def test_qualified_rig_holds_an_unadmitted_issuer_before_any_pipeline_work(self):
        q = Rig(simulation=False)
        with self.assertRaises(Exception) as cm: abs_(q.claims, issue(q.claims, issued_by="UNADMITTED")["order_id"], br())
        self.assertEqual(getattr(cm.exception, "code", ""), "COMPOSER_BUILD_ORDER_NOT_VERIFIED:ISSUER_NOT_ANCHORED")
if __name__ == "__main__": unittest.main()


class AcceptedRecordVerification(unittest.TestCase):
    """R34: maintenance verifies the accepted receipt/materialization AS FOUND. Same feature key + version with a different manifest/record cannot pass; nothing is rebuilt or repaired."""
    def accepted(self):
        rig = Rig(); oid = OA.order_id_for("cand-1"); p = package(order_id=oid)
        adm = admit(p, accepted_fit_generations=rig.fits, conformance=SIM_CONF); self.assertEqual(issue(rig.claims, subject_key=adm.subject_key)["order_id"], oid)
        out = rig.pipe.run(p); self.assertEqual(out.accepted.kind, "CANONICAL_ACCEPTED"); fk = adm.feature_key
        return rig, fk, rig.journals.journal(fk.namespace()), json.loads(out.accepted.body_json)
    def ver(self, rig, fk, j, c=None, now=10):
        c = c or core(); res, st = RV.reverify_accepted(c, journal=j, store=rig.store, feature_key=fk, now=now, max_age=50); return c, res, st
    def put(self, rig, key, data): g = rig.store.get(key); rig.raw_store._d[_PREFIX + key] = (data, g[1] if g else 1)
    def test_genuine_accepted_record_passes_and_a_restarted_core_passes_again(self):
        rig, fk, j, body = self.accepted()
        self.assertEqual(RAW(rig, accepted_materialization_key(body["materialization_hash"]))[0][:1], b"{")                             # the verified record is persisted and named by the acceptance
        c, res, st = self.ver(rig, fk, j); self.assertEqual((res.status, st, c.recording_health(fk.key(), "1", 11).state), ("PASS", "ACCEPTED_RECORD_AS_FOUND", "HEALTHY"))
        c2, res2, _ = self.ver(rig, fk, j); self.assertEqual((res2.status, c2.recording_health(fk.key(), "1", 11).state), ("PASS", "HEALTHY"))      # restart: fresh Core, same stored facts
    def test_altered_record_manifest_or_absence_is_found_failing_and_never_repaired(self):
        rig, fk, j, body = self.accepted(); mk = accepted_materialization_key(body["materialization_hash"]); ak = artifact_key(body["manifest_hash"])
        rec = json.loads(RAW(rig, mk)[0]); good_rec = RAW(rig, mk)[0]; good_art = RAW(rig, ak)[0]
        rec2 = dict(rec, probe_batch=rec["probe_batch"][1:]); self.put(rig, mk, canonical_bytes(rec2))                                          # altered value, hash left as recorded
        c, res, st = self.ver(rig, fk, j); self.assertEqual((res.status, c.recording_health(fk.key(), "1", 11).state), ("FAIL", "NOT_HEALTHY"))
        self.put(rig, mk, good_rec); self.put(rig, ak, good_art[:-1] + bytes([good_art[-1] ^ 1]))                                                         # altered manifest bytes
        c, res, st = self.ver(rig, fk, j); self.assertEqual((res.status, c.recording_health(fk.key(), "1", 11).state), ("FAIL", "NOT_HEALTHY"))
        self.assertNotEqual(RAW(rig, ak)[0], good_art)                                                                                          # as found: the corrupt bytes were NOT overwritten
        self.put(rig, ak, good_art); del rig.raw_store._d[_PREFIX + mk]                                                                                            # absent record
        c, res, st = self.ver(rig, fk, j); self.assertEqual((res.status, st, c.recording_health(fk.key(), "1", 11).state), ("FAIL", "ACCEPTED_RECORD_UNBOUND_OR_ABSENT", "NOT_HEALTHY")); self.assertIsNone(RAW(rig, mk))
        self.put(rig, mk, good_rec); c, res, st = self.ver(rig, fk, j); self.assertEqual(res.status, "PASS")                                              # positive control after restoring the genuine bytes
    def test_a_different_manifest_under_the_same_feature_key_and_version_cannot_pass(self):
        rig, fk, j, body = self.accepted(); mk = accepted_materialization_key(body["materialization_hash"])
        other = momentum_manifest(); other["nodes"][3]["n"] = 4                                                                  # root's window4 case: SAME feature id/version/instrument/timeframe, different manifest
        from stage_a.tracker.materialization.stateful_materializer import StatefulMaterializer
        from stage_a.tracker.verification.stateful_verifier import probe_for
        from stage_a.composer.expression.canonical_encoding import encode_manifest
        m2 = Manifest.from_dict(other)
        scratch = SIMS(); rec2 = StatefulMaterializer(scratch).materialize(m2, probe_for(encode_manifest(m2)))
        self.assertNotEqual(rec2["manifest_hash"], body["manifest_hash"])
        for k in (artifact_key(rec2["manifest_hash"]),): self.put(rig, k, scratch.get(k)[0])
        self.put(rig, mk, canonical_bytes(rec2))                                                                                                         # a self-consistent record of ANOTHER manifest planted at the accepted key
        c, res, st = self.ver(rig, fk, j); self.assertEqual((res.status, st, c.recording_health(fk.key(), "1", 11).state), ("FAIL", "ACCEPTED_RECORD_UNBOUND_OR_ABSENT", "NOT_HEALTHY"))
    def test_scheduler_verifies_the_accepted_binding_and_no_accepted_record_refuses(self):
        rig, fk, j, body = self.accepted(); c = core(); b = {fk.key(): S.AcceptedBinding(j, rig.store, fk)}
        r = S.run_reverification_pass(c, b, [fk.key()], now=10, max_age=50); self.assertEqual([(i.outcome, i.detail, i.evidence) for i in r], [("VERIFIED", "PASS", "ACCEPTED_RECORD_AS_FOUND")])
        rig2 = Rig(); other = FeatureKey(fk.scope, fk.feature_id, "9")
        self.assertEqual(code(RV.reverify_accepted, core(), journal=rig2.journals.journal(fk.namespace()), store=rig2.store, feature_key=fk, now=10, max_age=50), "NO_ACCEPTED_RECORD")
        self.assertEqual(code(RV.reverify_accepted, core(), journal=j, store=rig.store, feature_key=other, now=10, max_age=50), "NO_ACCEPTED_RECORD")
if __name__ == "__main__": unittest.main()
