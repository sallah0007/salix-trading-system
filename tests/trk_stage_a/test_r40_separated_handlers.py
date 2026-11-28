"""R40: ACTUAL separated materializer/verifier/acceptor handlers in real child processes over a shared file store and reference-only jobs (not the marker harness). SIMULATION carrier; no principal/deployment/provider."""
import json, os, tempfile, unittest
from stage_a.errors import Refusal
from stage_a.ops import workers as W, separated_handlers as SH
from stage_a.ops.process_supervisor import ProcessSupervisor
from stage_a.storage.file_object_store import FileObjectStore
from stage_a.storage.authority_class import approve_test_adapter
from stage_a.storage.keys import artifact_key
from stage_a.storage.byte_primitives import canonical_bytes
from stage_a.composer import order_authority as OA
from stage_a.composer.build_gate import accept_build_start as abs_
from stage_a.composer.expression.canonical_encoding import encode_manifest
from stage_a.tracker.quant_intake_adapter import admit, reserve_authority, build_safe_intake_report
from stage_a.tracker.quant_certification import certify
from stage_a.tracker.verification.independent_hashing import manifest_digest
from stage_a.tracker.verification.stateful_verifier import probe_for
from stage_a.clocks import FixedClock
from .fixtures import Rig, package, SIM_CONF, ANCHOR
from .test_r29_intake_order import issue, br
M = "stage_a.ops.separated_handlers:"
HS = {"tracker.materialize": ("tracker-materializer-worker", M + "materialize"), "tracker.verify": ("tracker-verifier-worker", M + "verify"), "tracker.accept": ("tracker-acceptance-worker", M + "accept")}
approve_test_adapter(FileObjectStore)
def seed(root):
    rig = Rig(store=FileObjectStore(root)); oid = OA.order_id_for("cand-1"); pkg = package(order_id=oid); adm = admit(pkg, accepted_fit_generations=rig.fits, conformance=SIM_CONF); issue(rig.claims, subject_key=adm.subject_key); abs_(rig.claims, oid, br())
    assert reserve_authority(rig.claims, pkg, adm) is not None
    raw = encode_manifest(adm.manifest); mh = manifest_digest(raw); fk = adm.feature_key; assert rig.store.put_if_absent(artifact_key(mh), raw)
    cert = certify(adm.manifest, probe_for(raw)); rep = build_safe_intake_report(pkg, adm, clock=FixedClock(), verdict="ACCEPT_FOR_REGISTRY", identity_decision="NEW_CANONICAL_FEATURE", registry_ref="PROPOSED:" + fk.key())
    for k, v in (("sep/declared/" + mh, {"manifest_hash": mh, "graph_hash": pkg.declared_graph_hash, "program_hash": pkg.declared_program_hash, "scope_key": fk.key()}), ("sep/acceptin/" + mh, {"request_id": pkg.request_id, "attempt_id": pkg.attempt_id, "instrument": fk.scope.instrument, "timeframe": fk.scope.timeframe, "feature_id": fk.feature_id, "feature_version": fk.feature_version, "cert_hash": cert.cert_hash, "report_hash": rep["FINAL_REPORT_HASH"]}), ("sep/anchor", {"issuers": sorted(ANCHOR.issuer_ids), "binding": ANCHOR.source_binding_hash})): assert rig.store.put_if_absent(k, canonical_bytes(v))
    return rig, pkg, adm, mh
def job(kind, name, *refs): return W.Job("j-" + name, kind, "idem-" + name, tuple(refs))
class Sep(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.TemporaryDirectory(); self.root = os.path.join(self.d.name, "store"); self.crash = os.path.join(self.d.name, "crash"); os.makedirs(self.crash); os.environ["SALIX_SEP_ROOT"] = self.root
        self.rig, self.pkg, self.adm, self.mh = seed(self.root); self.ns = self.adm.feature_key.namespace(); self.ver = self.adm.feature_key.feature_version
    def tearDown(self): os.environ.pop("SALIX_SEP_ROOT", None); os.environ.pop("SALIX_SEP_CRASH_ONCE_DIR", None); self.d.cleanup()
    def _ptr(self, kind, h): g = self.rig.store.get("sep/%s/%s" % (kind, h)); return None if g is None else g[0].decode()
    def _chain(self, s, tag=""):
        out = []; q = s._q
        q.submit(job("tracker.materialize", "m" + tag, ("manifest", self.mh))); out += s.run_until_idle(); matH = self._ptr("mat-by-manifest", self.mh)
        if matH is None: return out, None, None
        q.submit(job("tracker.verify", "v" + tag, ("materialization", matH), ("declared", self.mh))); out += s.run_until_idle(); rh = self._ptr("ver-by-mat", matH)
        if rh is None: return out, matH, None
        q.submit(job("tracker.accept", "a" + tag, ("verification", rh), ("materialization", matH), ("acceptin", self.mh))); out += s.run_until_idle(); return out, matH, rh
    def _accepted(self): return [r for r in self.rig.journals.journal(self.ns).read_from(1) if r.kind == "CANONICAL_ACCEPTED"]
    def test_the_chain_runs_in_three_real_processes_and_matches_the_in_process_pipeline_acceptance(self):
        with ProcessSupervisor(W.JobQueue(), HS, reply_timeout=60) as s:
            out, matH, rh = self._chain(s); self.assertEqual([r[1] for r in out], ["DONE"] * 3); pids = s.pids(); self.assertEqual(len(set(pids.values())), 10)
        acc = self._accepted(); self.assertEqual(len(acc), 1); body = json.loads(acc[0].body_json)
        ref = Rig(); oid = OA.order_id_for("cand-1"); p2 = package(order_id=oid); a2 = admit(p2, accepted_fit_generations={}, conformance=SIM_CONF); issue(ref.claims, subject_key=a2.subject_key); abs_(ref.claims, oid, br()); o = ref.pipe.run(p2); rb = json.loads(ref.journals.journal(self.ns).read_from(1)[0].body_json)
        for k in ("manifest_hash", "graph_hash", "program_hash", "materialization_hash", "verification_hash", "certification_hash", "safe_intake_report_hash", "attempt_id", "feature_key"): self.assertEqual(body[k], rb[k], k)       # same canonical result through the SEPARATED path
        self.assertEqual((body["materialization_hash"], body["verification_hash"]), (matH, rh))
    def test_crash_after_effect_before_reply_retries_in_a_new_process_and_the_effect_lands_exactly_once(self):
        os.environ["SALIX_SEP_CRASH_ONCE_DIR"] = self.crash
        with ProcessSupervisor(W.JobQueue(), HS, reply_timeout=60) as s:
            out, matH, rh = self._chain(s); self.assertEqual([r[1] for r in out], ["RETRY", "DONE", "RETRY", "DONE", "RETRY", "DONE"]); self.assertEqual(s.respawns, 3)
        self.assertEqual(len(self._accepted()), 1); self.assertEqual(sorted(os.listdir(self.crash)), ["j-a.crashed", "j-m.crashed", "j-v.crashed"])
    def test_a_duplicate_accept_job_is_an_idempotent_replay_not_a_second_acceptance(self):
        with ProcessSupervisor(W.JobQueue(), HS, reply_timeout=60) as s:
            out, matH, rh = self._chain(s); s._q.submit(job("tracker.accept", "a2", ("verification", rh), ("materialization", matH), ("acceptin", self.mh))); self.assertEqual(s.run_until_idle(), [("idem-a2", "DONE")])
        self.assertEqual(len(self._accepted()), 1)
    def test_wrong_hash_wrong_refs_and_tampered_inputs_never_produce_an_acceptance(self):
        with ProcessSupervisor(W.JobQueue(), HS, reply_timeout=60, max_attempts=1) as s:
            s._q.submit(job("tracker.materialize", "bad", ("manifest", "0" * 64))); self.assertEqual(s.run_one(), ("idem-bad", "DEAD")); self.assertEqual(s.dead["idem-bad"][1], "SEP_MANIFEST_ABSENT")
            self.rig.store.put_if_absent(artifact_key("1" * 64), b"not the manifest"); s._q.submit(job("tracker.materialize", "bad2", ("manifest", "1" * 64))); self.assertEqual(s.run_one(), ("idem-bad2", "DEAD")); self.assertEqual(s.dead["idem-bad2"][1], "SEP_MANIFEST_HASH_MISMATCH")
            s._q.submit(job("tracker.materialize", "bad3", ("manifest", self.mh), ("manifest", self.mh))); self.assertEqual(s.run_one(), ("idem-bad3", "DEAD")); self.assertEqual(s.dead["idem-bad3"][1], "SEP_JOB_REF_MISSING_OR_DUPLICATE")
            s._q.submit(job("tracker.materialize", "m", ("manifest", self.mh))); self.assertEqual(s.run_one(), ("idem-m", "DONE")); matH = self._ptr("mat-by-manifest", self.mh)
            s._q.submit(job("tracker.verify", "v0", ("materialization", "2" * 64), ("declared", self.mh))); self.assertEqual(s.run_one(), ("idem-v0", "DEAD")); self.assertEqual(s.dead["idem-v0"][1], "SEP_MATERIALIZATION_ABSENT")
            s._q.submit(job("tracker.accept", "a0", ("verification", "3" * 64), ("materialization", matH), ("acceptin", self.mh))); self.assertEqual(s.run_one(), ("idem-a0", "DEAD")); self.assertEqual(s.dead["idem-a0"][1], "SEP_VERIFICATION_ABSENT")
            raw = self.rig.store._i; key = "SIMULATION/sep/materialization/" + matH; rec = json.loads(raw.get(key)[0]); rec["probe_batch"] = ["tampered"]; raw.put_if_match(key, canonical_bytes(rec), raw.get(key)[1])          # altered stored record: verification must not PASS
            s._q.submit(job("tracker.verify", "v1", ("materialization", matH), ("declared", self.mh))); self.assertEqual(s.run_one(), ("idem-v1", "DEAD")); self.assertEqual(s.dead["idem-v1"][1], "SEP_VERIFICATION_NOT_PASS")
        self.assertEqual(self._accepted(), []); self.assertIsNone(self._ptr("ver-by-mat", matH))
    def test_a_stale_epoch_writer_cannot_append_after_the_separated_acceptor_committed(self):
        old = self.rig.journals.journal(self.ns)
        with ProcessSupervisor(W.JobQueue(), HS, reply_timeout=60) as s: self._chain(s)
        body = json.loads(self._accepted()[0].body_json); body = dict(body, feature_version="2", feature_key=body["feature_key"][:-1] + "2")
        from stage_a.errors import StaleFence
        from tracker_component.journal_port import HeadMismatch
        with self.assertRaises(StaleFence): old.append(old.head(), "CANONICAL_ACCEPTED", body)
        self.assertEqual(len(self._accepted()), 1)
if __name__ == "__main__": unittest.main()
