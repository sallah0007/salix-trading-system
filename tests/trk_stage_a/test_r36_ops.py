import io, json, os, tempfile, unittest
from stage_a.errors import Refusal
from stage_a.ops import jsonlog as JL, workers as W, read_model as RM, keys_v1 as K, rehearsal as RH
def code(f, *a, **k):
    try: f(*a, **k)
    except Refusal as e: return e.code
class JsonLog(unittest.TestCase):
    def test_stable_fields_extra_and_never_authoritative(self):
        b = io.StringIO(); s = JL.JsonEventSink(stream=b); s.emit("job_done", service_role="tracker-verifier", job_id="j1", reason_code="OK", duration_ns=5, weird=1)
        d = json.loads(b.getvalue()); self.assertEqual((d["event_name"], d["service_role"], d["authoritative"], d["extra"]), ("job_done", "tracker-verifier", False, {"weird": 1})); self.assertFalse(hasattr(s, "health")); self.assertFalse(hasattr(s, "status"))
        self.assertEqual(code(s.emit, "x", duration_ns=float("nan")), "LOG_EVENT_NOT_JSON"); self.assertEqual(code(s.emit, ""), "LOG_EVENT_NAME_INVALID"); self.assertEqual(code(JL.JsonEventSink, stream=b, path="/x"), "LOG_TRANSPORT_AMBIGUOUS")
    def test_file_transport_appends_lines(self):
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "l.jsonl"); s = JL.JsonEventSink(path=p); s.emit("a"); s.emit("b"); self.assertEqual([json.loads(l)["event_name"] for l in open(p)], ["a", "b"])
class Workers(unittest.TestCase):
    def good(self): return {w: (100 + i, W.WORKER_PRINCIPAL[w]) for i, w in enumerate(W.WORKERS)}
    def test_separation_positive_and_each_prohibited_merge_refused(self):
        W.check_separation(self.good())
        a = self.good(); a["tracker-verifier-worker"] = (a["tracker-materializer-worker"][0], "tracker-verifier"); self.assertEqual(code(W.check_separation, a), "PROHIBITED_ROLE_MERGE")                   # same OS process
        a = self.good(); a["tracker-verifier-worker"] = (999, "tracker-materializer"); self.assertEqual(code(W.check_separation, a), "PROHIBITED_ROLE_MERGE")                                           # same principal
        a = self.good(); a["health-evidence-worker"] = (a["tracker-acceptance-worker"][0], "health-writer"); self.assertEqual(code(W.check_separation, a), "PROHIBITED_ROLE_MERGE")
        a = self.good(); a["composer-build-worker"] = (555, "tracker-acceptor"); self.assertEqual(code(W.check_separation, a), "COMPOSER_HOLDS_TRACKER_ROLE")
        a = self.good(); a["scheduler-worker"] = (556, "health-writer"); self.assertEqual(code(W.check_separation, a), "WORKER_PRINCIPAL_MISMATCH"); a = self.good(); del a["replay-worker"]; self.assertEqual(code(W.check_separation, a), "WORKER_SET_INCOMPLETE")
        self.assertTrue(W.may_write("tracker-acceptor", "CANONICAL_TRANSITION_AND_STATUS_WRITE")); self.assertFalse(W.may_write("tracker-materializer", "CANONICAL_TRANSITION_AND_STATUS_WRITE")); self.assertEqual(W.PRINCIPAL_MAP, "DOCUMENTARY_NOT_AUTHENTICATION")
    def test_queue_idempotency_and_recovery_from_canonical_history(self):
        q = W.JobQueue(); j = W.Job("j1", "verify", "k1", (("ref", "h"),)); self.assertIs(q.submit(j), j); self.assertIs(q.submit(W.Job("j1", "verify", "k1", (("ref", "h"),))), j)
        self.assertEqual(code(q.submit, W.Job("j2", "verify", "k1", (("ref", "OTHER"),))), "JOB_IDEMPOTENCY_KEY_REUSED_DIFFERENTLY"); self.assertEqual(code(q.submit, W.Job("j", "k", "x", ())), "JOB_MALFORMED")
        q.complete("k1"); self.assertEqual(q.pending(), ()); self.assertEqual(code(q.complete, "nope"), "JOB_UNKNOWN")
        from . import test_r33_composed as TC
        t = TC.AcceptedRecordVerification(); rig, fk, jr, body = t.accepted()
        nxt = lambda kind: "reverify" if kind == "CANONICAL_ACCEPTED" else None
        a = W.recover_pending({fk.namespace(): jr}, nxt); b = W.recover_pending({fk.namespace(): jr}, nxt); self.assertEqual(a, b); self.assertEqual(len(a), 1); self.assertEqual(a[0].kind, "reverify")
        self.assertEqual(W.recover_pending({fk.namespace(): jr}, lambda k: None), ())
class ReadModel(unittest.TestCase):
    def row(self, h="a" * 64): return {"manifest_hash": h, "feature_id": "f", "feature_version": "1", "status_projection": "CURRENT", "canonical_ref": "transition/1", "canonical_hash": h}
    def test_rows_need_provenance_rebuild_is_exclusive_and_fail_closed_and_presence_is_not_authority(self):
        m = RM.ReadModel(); m.upsert("stagea_manifest_index", self.row()); r = m.get("stagea_manifest_index", "a" * 64); self.assertFalse(r.authoritative)
        bad = self.row(); del bad["canonical_hash"]; self.assertEqual(code(m.upsert, "stagea_manifest_index", bad), "READ_MODEL_ROW_MALFORMED"); self.assertEqual(code(m.upsert, "nope", self.row()), "READ_MODEL_TABLE_UNKNOWN")
        c = self.row(); c["canonical_hash"] = "b" * 64; self.assertEqual(code(m.upsert, "stagea_manifest_index", c), "READ_MODEL_ROW_PROVENANCE_CONFLICT")
        self.assertEqual(m.rebuild([("stagea_manifest_index", self.row("c" * 64))]), 1); self.assertIsNone(m.get("stagea_manifest_index", "a" * 64))               # the old projection is dropped, not merged
        self.assertEqual(code(m.rebuild, [("stagea_manifest_index", self.row("d" * 64)), ("stagea_manifest_index", bad)]), "READ_MODEL_ROW_MALFORMED"); self.assertEqual(m.snapshot()["stagea_manifest_index"], {})     # failure leaves it EMPTY
        s1 = RM.ReadModel(); s1.rebuild([("stagea_manifest_index", self.row("e" * 64))]); s2 = RM.ReadModel(); s2.upsert("stagea_manifest_index", self.row("e" * 64)); self.assertEqual(s1.snapshot(), s2.snapshot())
    def test_ddl_names_every_table_and_the_transition_unique_key(self):
        d = RM.ddl(); self.assertTrue(all(("CREATE TABLE %s " % t) in d for t in RM.TABLES)); self.assertIn("UNIQUE INDEX stagea_transition_index_ns_epoch_seq", d); self.assertEqual(len(RM.TABLES), 11)
class Keys(unittest.TestCase):
    def test_builders_validate_and_head_cas_is_epoch_fenced(self):
        h = "ab" * 32; self.assertEqual(K.artifact_key("manifest", h), "stage-a/v1/artifacts/manifest/ab/%s.bin" % h); self.assertEqual(K.transition_key("ns", 2, 7, h), "stage-a/v1/coordination/ns/epochs/2/transitions/%020d-%s.bin" % (7, h))
        for f, a in ((K.artifact_key, ("m", "short")), (K.golden_key, ("../x", h)), (K.transition_key, ("ns", -1, 1, h)), (K.transition_key, ("ns", 1, 0, h)), (K.health_key, ("t", "s", -1, h))): self.assertIsNotNone(code(f, *a), a)
        self.assertTrue(K.head_cas_allowed(3, 3, 5, 6)); self.assertFalse(K.head_cas_allowed(3, 2, 5, 6)); self.assertFalse(K.head_cas_allowed(3, 3, 5, 7)); self.assertFalse(K.head_cas_allowed(3, 3, 5, 5))
class Rehearsal(unittest.TestCase):
    def test_phases_are_ordered_evidenced_and_rollback_never_deletes(self):
        p = RH.MigrationPlan(); self.assertEqual(code(p.record_phase, RH.PHASES[1], "e"), "MIGRATION_PHASE_OUT_OF_ORDER"); self.assertEqual(code(p.record_phase, RH.PHASES[0], ""), "MIGRATION_PHASE_EVIDENCE_MISSING")
        p.record_phase(RH.PHASES[0], "ev1"); self.assertEqual(p.next_phase(), RH.PHASES[1]); self.assertEqual(len(p.completed()), 1); self.assertIn("retain_all_canonical_artifacts_and_transitions_append_only", p.rollback_actions()); self.assertFalse(any("delete" in a for a in p.rollback_actions()))
if __name__ == "__main__": unittest.main()
