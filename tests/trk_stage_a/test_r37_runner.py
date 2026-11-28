"""R37: generic worker runner: separation gate, idempotent retry, dead-letter visibility, job-ref-only wire form, queue-loss recovery from canonical history."""
import io, json, unittest
from stage_a.errors import Refusal
from stage_a.ops import workers as W, runner as R
from stage_a.observability import JsonEventSink
from stage_a.coordination.object_store_journal import ObjectStoreJournal
from stage_a.storage.object_store import InMemoryObjectStore
def code(f, *a, **k):
    try: f(*a, **k)
    except Refusal as e: return e.code
SLOTS = {w: (100 + i, W.WORKER_PRINCIPAL[w]) for i, w in enumerate(W.WORKERS)}
def job(k="k1", kind="verify", refs=(("ns", "h1"),)): return W.Job("j-" + k, kind, k, refs)
class Runner(unittest.TestCase):
    def test_requires_a_separation_clean_assignment_before_any_job_runs(self):
        bad = dict(SLOTS); bad["tracker-verifier-worker"] = (SLOTS["tracker-materializer-worker"][0], "tracker-verifier"); ran = []
        self.assertEqual(code(R.WorkerRunner, W.JobQueue(), bad, {"verify": ("tracker-verifier-worker", ran.append)}), "PROHIBITED_ROLE_MERGE"); self.assertEqual(ran, [])
        self.assertEqual(code(R.WorkerRunner, W.JobQueue(), SLOTS, {"verify": ("nope", ran.append)}), "RUNNER_CONFIG_INVALID"); self.assertEqual(code(R.WorkerRunner, W.JobQueue(), SLOTS, {"verify": ("tracker-verifier-worker", ran.append)}, max_attempts=0), "RUNNER_CONFIG_INVALID")
    def test_success_completes_once_a_failing_handler_is_retried_then_dead_lettered_and_never_completed(self):
        q = W.JobQueue(); calls = []; sink = JsonEventSink(stream=io.StringIO())
        def flaky(j): calls.append(j.idempotency_key); (_ for _ in ()).throw(Refusal("x", code="BOOM")) if j.idempotency_key == "bad" else None
        r = R.WorkerRunner(q, SLOTS, {"verify": ("tracker-verifier-worker", flaky)}, sink=sink, max_attempts=2); q.submit(job("ok")); q.submit(job("bad"))
        self.assertEqual(r.run_until_idle(), [("bad", "RETRY"), ("bad", "DEAD"), ("ok", "DONE")]); self.assertEqual([j.idempotency_key for j in q.pending()], ["bad"]); self.assertIn("bad", r.dead); self.assertEqual(r.dead["bad"][1], "BOOM")      # dead-lettered and VISIBLE, not complete
        self.assertEqual(r.run_one(), None); self.assertEqual([e["event_name"] for e in sink.events if e["subject_id"] == "bad"], ["JOB_STARTED", "JOB_RETRY", "JOB_STARTED", "JOB_DEAD_LETTERED"]); self.assertTrue(all(e["authoritative"] is False for e in sink.events))
    def test_a_failing_sink_never_changes_a_job_outcome_and_an_unhandled_kind_is_left_pending(self):
        class Boom:
            def emit(self, *a, **k): raise OSError("x")
        q = W.JobQueue(); r = R.WorkerRunner(q, SLOTS, {"verify": ("tracker-verifier-worker", lambda j: None)}, sink=Boom()); q.submit(job("a")); q.submit(job("z", kind="other")); self.assertEqual(r.run_until_idle(), [("a", "DONE")]); self.assertEqual([j.idempotency_key for j in q.pending()], ["z"])
    def test_wire_form_is_a_job_reference_only_and_extra_or_missing_fields_refuse(self):
        j = job(); self.assertEqual(R.decode_job_ref(R.encode_job_ref(j)), j)
        base = {"job_id": "j", "kind": "verify", "idempotency_key": "k", "governing_refs": [["a", "b"]]}
        for d, c in ((dict(base, status="CURRENT"), "JOB_REF_MALFORMED"), ({k: v for k, v in base.items() if k != "governing_refs"}, "JOB_REF_MALFORMED"), (dict(base, governing_refs=[["a"]]), "JOB_REF_MALFORMED"), (dict(base, governing_refs=[]), "JOB_MALFORMED"), (dict(base, kind=""), "JOB_MALFORMED")):
            self.assertEqual(code(R.decode_job_ref, json.dumps(d).encode()), c, d)
        self.assertEqual(code(R.decode_job_ref, b"\xff"), "JOB_REF_MALFORMED")
    def test_queue_loss_is_recovered_from_canonical_history_and_the_rerun_is_idempotent(self):
        jn = ObjectStoreJournal(InMemoryObjectStore(), "ns", "w"); jn.acquire_epoch(); jn.append(jn.head(), "CANONICAL_ACCEPTED", {"x": 1}); effects = set()
        nxt = lambda kind: "verify" if kind == "CANONICAL_ACCEPTED" else None
        q1 = W.JobQueue(); [q1.submit(j) for j in W.recover_pending({"ns": jn}, nxt)]; r1 = R.WorkerRunner(q1, SLOTS, {"verify": ("tracker-verifier-worker", lambda j: effects.add(j.idempotency_key))})
        def crash(j): raise OSError("process died mid-job")
        rc = R.WorkerRunner(W.JobQueue(), SLOTS, {"verify": ("tracker-verifier-worker", crash)}, max_attempts=1)
        q2 = W.JobQueue(); [q2.submit(j) for j in W.recover_pending({"ns": jn}, nxt)]; rc._q = q2; self.assertEqual(rc.run_until_idle()[0][1], "DEAD")                      # crashed run, queue then LOST
        q3 = W.JobQueue(); [q3.submit(j) for j in W.recover_pending({"ns": jn}, nxt)]; r3 = R.WorkerRunner(q3, SLOTS, {"verify": ("tracker-verifier-worker", lambda j: effects.add(j.idempotency_key))}); self.assertEqual(r3.run_until_idle()[0][1], "DONE"); self.assertEqual(len(effects), 1)
        r3.run_until_idle(); self.assertEqual(len(effects), 1)                                                                                                                   # same recovered key: no second effect
        jn.append(jn.head(), "PUBLISHABLE", {"x": 2}); self.assertEqual(W.recover_pending({"ns": jn}, nxt), ())                                                                  # the advanced journal owes nothing
if __name__ == "__main__": unittest.main()
