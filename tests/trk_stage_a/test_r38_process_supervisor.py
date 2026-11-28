"""R38: REAL worker processes, ref-only IPC, respawn/retry recovery and canonical-ref queue recovery. Test-only generic supervisor; no deployment, principal or credential."""
import os, tempfile, unittest, json
from stage_a.errors import Refusal
from stage_a.ops import workers as W
from stage_a.ops.process_supervisor import ProcessSupervisor
from stage_a.ops.runner import encode_job_ref
from stage_a.storage.object_store import InMemoryObjectStore
from stage_a.coordination.object_store_journal import ObjectStoreJournal
HP = os.path.join(os.path.dirname(os.path.abspath(__file__)), "proc_handlers")
PATHS = (os.path.dirname(HP),)
M = "proc_handlers.handlers:"
def job(d, name, kind="mat", h="h1"): return W.Job("j-" + name, kind, "idem-" + name, ((os.path.join(d, name), h),))
def sup(q, **kw):
    hs = {"mat": ("tracker-materializer-worker", M + "ok"), "ver": ("tracker-verifier-worker", M + "ok"), "die": ("tracker-materializer-worker", M + "die_once"), "fail": ("tracker-acceptance-worker", M + "always_fail"), "hang": ("tracker-verifier-worker", M + "hang_once")}
    return ProcessSupervisor(q, hs, extra_paths=PATHS, **kw)
def code(f, *a, **k):
    try: f(*a, **k)
    except Refusal as e: return e.code
class Proc(unittest.TestCase):
    def test_real_distinct_pids_run_jobs_in_the_owning_worker_process_not_in_this_one(self):
        with tempfile.TemporaryDirectory() as d, sup(W.JobQueue()) as s:
            pids = s.pids(); self.assertEqual(len(set(pids.values())), 10); self.assertNotIn(os.getpid(), pids.values()); W.check_separation(s.slots())
            s._q.submit(job(d, "a", "mat")); s._q.submit(job(d, "b", "ver")); self.assertEqual(s.run_until_idle(), [("idem-a", "DONE"), ("idem-b", "DONE")])
            self.assertEqual(open(os.path.join(d, "a.done")).read().split(), [str(pids["tracker-materializer-worker"])]); self.assertEqual(open(os.path.join(d, "b.done")).read().split(), [str(pids["tracker-verifier-worker"])])   # ran in the OWNING child, different pids
            self.assertEqual(s._q.pending(), ())
    def test_ipc_is_reference_only_extra_fields_and_foreign_kinds_refuse_in_the_child(self):
        with tempfile.TemporaryDirectory() as d, sup(W.JobQueue()) as s:
            p = s._procs["tracker-materializer-worker"]; j = job(d, "x", "mat"); wire = json.loads(encode_job_ref(j)); wire["payload"] = "stage=CURRENT"
            p.stdin.write(json.dumps(wire) + "\n"); p.stdin.flush(); r = json.loads(p.stdout.readline()); self.assertEqual((r["result"], r["code"], r["pid"]), ("REFUSED", "JOB_REF_MALFORMED", p.pid))
            self.assertEqual(s._ask("tracker-materializer-worker", job(d, "y", "ver")), ("REFUSED", "KIND_NOT_OWNED_BY_WORKER"))        # a worker never runs another role's kind
            self.assertFalse(os.path.exists(os.path.join(d, "x.done")) or os.path.exists(os.path.join(d, "y.done")))
    def test_child_death_leaves_the_job_pending_then_respawn_gets_a_new_pid_and_retry_completes(self):
        with tempfile.TemporaryDirectory() as d, sup(W.JobQueue()) as s:
            old = s.pids()["tracker-materializer-worker"]; s._q.submit(job(d, "d", "die")); self.assertEqual(s.run_one(), ("idem-d", "RETRY")); self.assertEqual(len(s._q.pending()), 1)      # NOT completed
            new = s.pids()["tracker-materializer-worker"]; self.assertNotEqual(old, new); self.assertEqual(s.run_one(), ("idem-d", "DONE")); self.assertEqual(open(os.path.join(d, "d.done")).read().split(), [str(new)]); W.check_separation(s.slots()); self.assertEqual(s.respawns, 1)
    def test_hung_child_is_killed_at_the_bound_and_a_poison_job_is_dead_lettered_never_completed(self):
        with tempfile.TemporaryDirectory() as d, sup(W.JobQueue(), reply_timeout=0.5) as s:
            s._q.submit(job(d, "h", "hang")); self.assertEqual(s.run_one(), ("idem-h", "RETRY")); self.assertEqual(s.run_one(), ("idem-h", "DONE"))
            s._q.submit(job(d, "f", "fail")); self.assertEqual([r for r in s.run_until_idle()], [("idem-f", "RETRY"), ("idem-f", "RETRY"), ("idem-f", "DEAD")]); self.assertIn("idem-f", s.dead); self.assertEqual(s.dead["idem-f"][1], "ValueError"); self.assertEqual([j.idempotency_key for j in s._q.pending()], ["idem-f"])
    def test_respawn_bound_is_enforced(self):
        with tempfile.TemporaryDirectory() as d, sup(W.JobQueue(), max_respawns=0) as s:
            s._q.submit(job(d, "d2", "die")); self.assertEqual(code(s.run_one), "SUPERVISOR_RESPAWN_BOUND_EXCEEDED")
    def test_queue_loss_recovery_from_canonical_refs_runs_in_a_fresh_supervisor_and_is_stable(self):
        with tempfile.TemporaryDirectory() as d:
            j = ObjectStoreJournal(InMemoryObjectStore(), "ns", "w"); j.acquire_epoch(); j.append(j.head(), "CANONICAL_ACCEPTED_TEST", {"x": 1})
            rec = lambda: W.recover_pending({os.path.join(d, "ns"): j}, lambda k: "mat" if k == "CANONICAL_ACCEPTED_TEST" else None)
            a, b = rec(), rec(); self.assertEqual(a, b); self.assertEqual(len(a), 1)
            q = W.JobQueue(); [q.submit(x) for x in a]
            with sup(q) as s: self.assertEqual(s.run_until_idle(), [(a[0].idempotency_key, "DONE")])
            j.append(j.head(), "SOMETHING_ELSE", {}); self.assertEqual(rec(), ())                      # advanced journal: the superseded state owes nothing
    def test_a_reply_from_a_foreign_pid_is_refused_and_an_externally_killed_worker_is_replaced_before_the_job_is_sent(self):
        import subprocess, sys, signal
        with tempfile.TemporaryDirectory() as d, sup(W.JobQueue()) as s:
            w = "tracker-materializer-worker"; old = s._procs[w]; old.kill(); old.wait(); self.assertIsNotNone(old.poll())
            s._q.submit(job(d, "k", "mat")); self.assertEqual(s.run_one(), ("idem-k", "DONE")); self.assertEqual(s.respawns, 1); self.assertEqual(s._tries.get("idem-k", 0), 0)      # replaced BEFORE sending: no attempt burned
            liar = subprocess.Popen([sys.executable, "-c", "import sys, json\nfor l in sys.stdin:\n    j = json.loads(l)\n    print(json.dumps({'job_id': j['job_id'], 'result': 'DONE', 'code': '', 'pid': 1}), flush=True)"], stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True, bufsize=1)
            try:
                s._procs[w].kill(); s._procs[w].wait(); s._procs[w] = liar; self.assertEqual(s._ask(w, job(d, "z", "mat")), ("LOST", "CHILD_REPLY_NOT_FROM_SPAWNED_PID_OR_JOB"))
            finally: liar.kill(); liar.wait()
    def test_config_and_unknown_worker_negatives(self):
        self.assertEqual(code(ProcessSupervisor, W.JobQueue(), {"mat": ("not-a-worker", M + "ok")}), "SUPERVISOR_CONFIG_INVALID"); self.assertEqual(code(ProcessSupervisor, W.JobQueue(), {"mat": ("tracker-materializer-worker", "nocolon")}), "SUPERVISOR_CONFIG_INVALID")
if __name__ == "__main__": unittest.main()
